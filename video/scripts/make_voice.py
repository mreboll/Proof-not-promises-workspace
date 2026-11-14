"""Voz en off y tiempos reales de cada frase.

    ..\\.venv\\Scripts\\python scripts\\make_voice.py            # voz definitiva con ElevenLabs (ELEVENLABS_API_KEY en ../.env)
    ..\\.venv\\Scripts\\python scripts\\make_voice.py --draft    # borrador gratis con Windows SAPI, solo para cuadrar tiempos

Lee SCENES y VOICE de src/timeline.ts, sintetiza cada frase, la coloca en orden dentro de su escena (si una escena no
cabe, acelera solo esa escena) y escribe:
  - public/voice/vo.wav (o vo-draft.wav)   pista de 2:00 con todas las frases en su sitio
  - src/data/voice-cues.json               {escena: [{from, to, text}]} en frames absolutos (subtítulos y sincronía)
Las frases de ElevenLabs se guardan en .voice-cache/ por (voz, ajustes, texto, velocidad): repetir no vuelve a gastar.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import wave
from array import array
from pathlib import Path

import requests
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FPS = 30
TOTAL = 3600
LEAD_IN = 10  # frames de silencio al empezar cada escena
GAP = 8  # frames entre frases
TAIL = 8  # frames libres al final de cada escena
# Silencio inicial distinto por escena (la intro arranca solo con el fondo) y pausas antes de frases concretas para
# dejar ver la imagen: el embudo antes de la regla, el mutante antes de la cola y el panel de Modal.
LEAD_BY_SCENE = {"intro": 20, "close": 4}
PAUSE_BEFORE = {("command", 1): 110, ("crossExam", 2): 30, ("crossExam", 4): 75}

# ElevenLabs: "Brian", narrador grave y sereno (tono de explicación técnica, creíble, sin sonar a anuncio).
ELEVEN_VOICE = "nPczCjzI2devNBz1zQrb"
ELEVEN_MODEL = "eleven_multilingual_v2"
ELEVEN_SETTINGS = {"stability": 0.55, "similarity_boost": 0.75, "style": 0.15, "use_speaker_boost": True}
ELEVEN_HZ = 24000  # pcm_24000: PCM 16 bits mono, disponible en todos los planes
ELEVEN_SPEEDS = [1.0, 1.05, 1.1, 1.15, 1.2]  # 1.2 es el máximo que admite la API
CACHE = ROOT / ".voice-cache"

SAPI_HZ = 22050
SAPI_RATES = [1, 2, 3, 4, 5]


def parse_timeline() -> tuple[dict[str, tuple[int, int]], dict[str, list[str]]]:
    src = (ROOT / "src" / "timeline.ts").read_text(encoding="utf-8").replace("\r\n", "\n")
    scenes = {k: (int(f), int(d)) for k, f, d in re.findall(r"(\w+): \{ from: (\d+), duration: (\d+) \}", src)}
    voice_src = src.split("export const VOICE", 1)[1]
    voice = {}
    for key in scenes:
        block = re.search(rf"\b{key}: \[(.*?)\],\n", voice_src, re.S)
        voice[key] = re.findall(r'"((?:[^"\\]|\\.)*)"', block.group(1)) if block else []
    return scenes, voice


def sapi(text: str, rate: int, tmp: Path) -> bytes:
    out = tmp / f"{hashlib.sha1(f'{rate}|{text}'.encode()).hexdigest()}.wav"
    script = (
        "Add-Type -AssemblyName System.Speech;"
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        "$s.SelectVoice('Microsoft Zira Desktop');"
        f"$s.Rate = {rate};"
        f"$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo({SAPI_HZ}, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono);"
        f"$s.SetOutputToWaveFile('{out}', $fmt);"
        f"$s.Speak([System.IO.File]::ReadAllText('{out}.txt'));"
        "$s.Dispose()"
    )
    Path(f"{out}.txt").write_text(text, encoding="utf-8")
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True, capture_output=True)
    with wave.open(str(out)) as w:
        return w.readframes(w.getnframes())


TAIL_KEEP = 0.25  # segundos de cola que se conservan tras el último sonido (las consonantes finales son suaves)


def trim_silence(pcm: bytes, hz: int, threshold: int = 150) -> tuple[bytes, int]:
    """Quita el silencio de cabeza y deja una cola corta con fundido. Devuelve (audio, muestras hasta el último sonido).

    La duración que ocupa la frase en el vídeo se mide hasta el último sonido; la cola puede caer en el hueco GAP.
    """
    samples = memoryview(pcm).cast("h")
    loud = [i for i in range(0, len(samples), 32) if abs(samples[i]) > threshold]
    if not loud:
        return pcm, len(samples)
    start = max(0, loud[0] - 64)
    end = min(len(samples), loud[-1] + int(TAIL_KEEP * hz))
    body = array("h", samples[start:end])
    fade = min(len(body), int(0.03 * hz))
    for k in range(fade):
        body[len(body) - fade + k] = int(body[len(body) - fade + k] * (1 - k / fade))
    return body.tobytes(), loud[-1] - start + int(0.05 * hz)


def eleven(text: str, speed: float, previous: str, key: str) -> bytes:
    """Audio en bruto de ElevenLabs (cacheado sin recortar)."""
    settings = {**ELEVEN_SETTINGS, "speed": speed}
    tag = hashlib.sha256(json.dumps([ELEVEN_VOICE, ELEVEN_MODEL, settings, text, previous]).encode()).hexdigest()[:24]
    cached = CACHE / f"{tag}.raw.pcm"
    if cached.exists():
        return cached.read_bytes()
    resp = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE}",
        params={"output_format": f"pcm_{ELEVEN_HZ}"},
        headers={"xi-api-key": key, "Content-Type": "application/json"},
        json={"text": text, "model_id": ELEVEN_MODEL, "voice_settings": settings, "previous_text": previous or None},
        timeout=120,
    )
    if resp.status_code != 200:
        sys.exit(f"ElevenLabs {resp.status_code}: {resp.text[:300]}")
    CACHE.mkdir(exist_ok=True)
    cached.write_bytes(resp.content)
    return resp.content


def main() -> None:
    draft = "--draft" in sys.argv
    load_dotenv(ROOT.parent / ".env")
    key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not draft and not key:
        sys.exit("Falta ELEVENLABS_API_KEY en ../.env (o usa --draft para el borrador con SAPI).")
    hz = SAPI_HZ if draft else ELEVEN_HZ
    steps = SAPI_RATES if draft else ELEVEN_SPEEDS
    tmp = Path(tempfile.mkdtemp(prefix="vo-"))
    track = bytearray(TOTAL * hz // FPS * 2)
    cues: dict[str, list[dict]] = {}
    scenes, voice = parse_timeline()
    for scene, (start, duration) in scenes.items():
        lines = voice[scene]
        for n, step in enumerate(steps):
            clips = []
            for i, text in enumerate(lines):
                raw = sapi(text, step, tmp) if draft else eleven(text, step, lines[i - 1] if i else "", key)
                pcm, spoken = trim_silence(raw, hz)
                clips.append((text, int(spoken / hz * FPS + 0.999), pcm))
            lead = LEAD_BY_SCENE.get(scene, LEAD_IN)
            pauses = sum(PAUSE_BEFORE.get((scene, i), 0) for i in range(len(clips)))
            needed = lead + sum(c[1] for c in clips) + GAP * (len(clips) - 1) + TAIL + pauses
            if needed <= duration or n == len(steps) - 1:
                break
        cursor = start + LEAD_BY_SCENE.get(scene, LEAD_IN)
        cues[scene] = []
        for i, (text, length, pcm) in enumerate(clips):
            cursor += PAUSE_BEFORE.get((scene, i), 0)
            offset = cursor * hz // FPS * 2
            track[offset:offset + len(pcm)] = pcm[: max(0, len(track) - offset)]
            cues[scene].append({"from": cursor, "to": cursor + length, "text": text})
            cursor += length + GAP
        flag = "" if needed <= duration else "  ** NO CABE: alarga la escena o acorta el texto **"
        print(f"{scene:10s} {'rate' if draft else 'speed'} {step}  {needed:4d}/{duration} frames{flag}")
    out_dir = ROOT / "public" / "voice"
    out_dir.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_dir / ("vo-draft.wav" if draft else "vo.wav")), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(hz)
        w.writeframes(bytes(track))
    (ROOT / "src" / "data" / "voice-cues.json").write_text(json.dumps(cues, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
