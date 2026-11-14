"""Música de fondo compuesta por código (sin descargas ni licencias): public/music/score.wav, 2:00 exactos.

    ..\\.venv\\Scripts\\python scripts\\make_music.py

Sigue el arco del vídeo leyendo los inicios de escena de src/timeline.ts:
  intro            dron grave y aire: la pregunta
  friday/problems  La menor lenta; desde los problemas, pulso grave e inquietud
  command          subida de ruido hasta la regla; golpe al aparecer "No model approves anything"
  triage/crossExam motor: bajo en corcheas, arpegio, bombo suave (96 bpm); se abre una octava en el contrainterrogatorio
  owner            se vacía: solo acordes, la calma de "son doce"
  finding          oscuro (Re menor / Si bemol), golpe grave en el ESCAPE
  sign/close       resuelve a Do mayor y se apaga sobre el título
Queda muy por debajo de la voz: Demo.tsx la baja aún más mientras se habla.
"""

import math
import random
import re
import wave
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SR = 32000
FPS = 30
LENGTH = 120.0
BEAT = 60 / 96

# Frecuencias (Hz)
N = {
    "A1": 55.0, "D2": 73.42, "E2": 82.41, "F2": 87.31, "G2": 98.0, "A2": 110.0, "Bb2": 116.54, "C3": 130.81,
    "D3": 146.83, "E3": 164.81, "F3": 174.61, "G3": 196.0, "G#3": 207.65, "A3": 220.0, "Bb3": 233.08, "B3": 246.94,
    "C4": 261.63, "D4": 293.66, "E4": 329.63, "F4": 349.23, "G4": 392.0, "A4": 440.0, "C5": 523.25, "D5": 587.33,
    "E5": 659.26,
}
CHORDS = {  # (bajo, notas del acorde)
    "Am": ("A2", ["A3", "C4", "E4"]), "F": ("F2", ["F3", "A3", "C4"]), "C": ("C3", ["G3", "C4", "E4"]),
    "G": ("G2", ["G3", "B3", "D4"]), "E": ("E2", ["G#3", "B3", "E4"]), "Dm": ("D2", ["D3", "F3", "A3"]),
    "Bb": ("Bb2", ["Bb3", "D4", "F4"]), "A": ("A2", ["A3", "C4", "E4"]),
}


def scene_starts() -> dict[str, float]:
    src = (ROOT / "src" / "timeline.ts").read_text(encoding="utf-8")
    return {k: int(f) / FPS for k, f in re.findall(r"(\w+): \{ from: (\d+), duration: \d+ \}", src)}


def cue_start(scene: str, line: int) -> float | None:
    cues = ROOT / "src" / "data" / "voice-cues.json"
    if not cues.exists():
        return None
    import json

    data = json.loads(cues.read_text(encoding="utf-8"))
    return data[scene][line]["from"] / FPS if scene in data and len(data[scene]) > line else None


class Mix:
    def __init__(self) -> None:
        self.buf = array("d", [0.0]) * int(SR * LENGTH)

    def tone(self, t0: float, dur: float, freq: float, amp: float, attack: float = 0.01, release: float = 0.1,
             harmonics: tuple[tuple[float, float], ...] = ((1, 1.0),), decay: float = 0.0) -> None:
        """Nota con envolvente: ataque, decaimiento exponencial opcional y salida suave."""
        start, n = int(t0 * SR), int(dur * SR)
        n = min(n, len(self.buf) - start)
        if n <= 0:
            return
        a, r = max(1, int(attack * SR)), max(1, int(release * SR))
        steps = [(2 * math.pi * freq * h / SR, g) for h, g in harmonics]
        buf = self.buf
        for i in range(n):
            env = min(1.0, i / a, (n - i) / r)
            if decay:
                env *= math.exp(-decay * i / SR)
            s = 0.0
            for w, g in steps:
                s += g * math.sin(w * i)
            buf[start + i] += amp * env * s

    def pad(self, t0: float, dur: float, chord: str, amp: float = 0.07) -> None:
        for note in CHORDS[chord][1]:
            for detune in (0.997, 1.003):  # dos voces ligeramente desafinadas: coro cálido
                self.tone(t0, dur, N[note] * detune, amp, attack=1.2, release=1.4, harmonics=((1, 1.0), (2, 0.25), (3, 0.08)))

    def bass(self, t0: float, dur: float, note: str, amp: float = 0.22) -> None:
        self.tone(t0, dur, N[note], amp, attack=0.005, release=0.06, harmonics=((1, 1.0), (2, 0.35)), decay=5.0)

    def pluck(self, t0: float, note: str, amp: float = 0.06, octave: int = 1) -> None:
        self.tone(t0, 0.45, N[note] * octave, amp, attack=0.003, release=0.08, harmonics=((1, 1.0), (2, 0.4), (3, 0.15)), decay=7.0)

    def kick(self, t0: float, amp: float = 0.35) -> None:
        start, n = int(t0 * SR), int(0.28 * SR)
        phase = 0.0
        for i in range(min(n, len(self.buf) - start)):
            freq = 45 + 90 * math.exp(-i / (0.03 * SR))
            phase += 2 * math.pi * freq / SR
            self.buf[start + i] += amp * math.exp(-i / (0.09 * SR)) * math.sin(phase)

    def noise(self, t0: float, dur: float, amp: float, rise: bool = False, bright: float = 0.08, seed: int = 1,
              decay: float = 0.0) -> None:
        """Ruido filtrado (paso bajo de un polo): aire, platillo o subida."""
        rnd = random.Random(seed)
        start, n = int(t0 * SR), int(dur * SR)
        y = 0.0
        for i in range(min(n, len(self.buf) - start)):
            y += bright * (rnd.uniform(-1, 1) - y)
            env = (i / n) ** 2 if rise else min(1.0, i / (0.01 * SR + 1), (n - i) / (0.05 * SR + 1))
            if decay:
                env *= math.exp(-decay * i / SR)
            self.buf[start + i] += amp * env * y

    def hit(self, t0: float, amp: float = 0.5) -> None:
        self.kick(t0, amp)
        self.tone(t0, 2.5, N["A1"], amp * 0.6, attack=0.005, release=1.0, decay=1.5)
        self.noise(t0, 1.2, amp * 0.5, bright=0.3, seed=7, decay=3.0)


def progression(mix: Mix, t0: float, t1: float, chords: list[str], bar: float, *, pad: float = 0.07,
                bass: str = "", arp: str = "", arp_amp: float = 0.06, octave_up: float = -1.0, kick: bool = False,
                hats: bool = False) -> None:
    """Rellena [t0, t1) con una progresión: cada acorde dura `bar` segundos."""
    t, k = t0, 0
    while t < t1 - 0.05:
        dur = min(bar, t1 - t)
        chord = chords[k % len(chords)]
        root, notes = CHORDS[chord]
        if pad:
            mix.pad(t, dur + 0.6, chord, pad)
        step = BEAT / 2 if bass == "8ths" else BEAT
        if bass:
            x = t
            while x < t + dur - 0.01:
                mix.bass(x, step * 0.9, root, 0.2 if bass == "8ths" else 0.16)
                x += step
        if arp:
            pattern = [notes[0], notes[1], notes[2], notes[1]] if arp == "16ths" else [notes[0], notes[2]]
            step_a = BEAT / 4 if arp == "16ths" else BEAT
            x, j = t, 0
            while x < t + dur - 0.01:
                mix.pluck(x, pattern[j % len(pattern)], arp_amp, 2)
                if 0 <= octave_up <= x:
                    mix.pluck(x + step_a / 2, pattern[(j + 2) % len(pattern)], arp_amp * 0.5, 4)
                x += step_a
                j += 1
        if kick or hats:
            x = t
            while x < t + dur - 0.01:
                beat = round((x - t0) / BEAT)
                if kick and beat % 2 == 0:
                    mix.kick(x, 0.3)
                if hats:
                    mix.noise(x + BEAT / 2, 0.06, 0.05, bright=0.9, seed=int(x * 100))
                x += BEAT
        t += bar
        k += 1


def compose() -> Mix:
    s = scene_starts()
    rule = cue_start("command", 1) or s["command"] + 4.5
    escape = cue_start("finding", 3) or s["finding"] + 8.5
    title = cue_start("close", 1) or s["close"] + 2.6
    mix = Mix()
    # Intro: dron y aire que se abre.
    mix.tone(0, s["friday"] + 1.5, N["A1"], 0.22, attack=2.0, release=1.5, harmonics=((1, 1.0), (2, 0.3)))
    mix.noise(0, s["friday"], 0.25, rise=True, bright=0.04, seed=3)
    # Viernes y problemas: La menor lenta; desde los problemas, pulso grave.
    progression(mix, s["friday"], s["problems"], ["Am", "F"], 5.0, pad=0.06)
    progression(mix, s["problems"], s["command"], ["Am", "E"], 5.0, pad=0.065, bass="quarters")
    # Comando: subida hasta la regla y golpe.
    progression(mix, s["command"], rule, ["E"], rule - s["command"], pad=0.06)
    mix.noise(s["command"], rule - s["command"], 0.35, rise=True, bright=0.12, seed=5)
    mix.hit(rule, 0.55)
    # Motor: T1, T2 y T3. En el contrainterrogatorio se abre una octava.
    progression(mix, rule, s["owner"], ["Am", "F", "C", "G"], 4 * BEAT, pad=0.055, bass="8ths", arp="16ths",
                arp_amp=0.05, octave_up=s["crossExam"], kick=True, hats=True)
    # Owner: calma.
    progression(mix, s["owner"], s["finding"], ["F", "C"], 5.0, pad=0.065, arp="quarters", arp_amp=0.04)
    # Hallazgo: oscuro, con golpe grave en el ESCAPE.
    progression(mix, s["finding"], s["product"], ["Dm", "Bb", "Dm", "A"], 4 * BEAT, pad=0.06, bass="quarters")
    mix.hit(escape, 0.45)
    # Producto y firma: resuelve hacia el mayor.
    progression(mix, s["product"], s["sign"], ["F"], s["sign"] - s["product"], pad=0.06)
    progression(mix, s["sign"], s["close"], ["F", "C", "G", "C"], 4 * BEAT, pad=0.065, bass="quarters", arp="16ths", arp_amp=0.04)
    # Cierre: Do mayor largo y un brillo al aparecer el título; se apaga a los 2:00.
    mix.pad(s["close"], LENGTH - s["close"], "C", 0.07)
    mix.tone(s["close"], LENGTH - s["close"], N["C3"], 0.14, attack=0.5, release=3.0)
    for k, note in enumerate(["C5", "E5", "G4"]):
        mix.pluck(title + k * 0.12, note, 0.05, 1)
    return mix


def write(mix: Mix, path: Path) -> None:
    peak = max(abs(v) for v in mix.buf) or 1.0
    gain = 0.89 / peak
    fade = int(1.5 * SR)
    n = len(mix.buf)
    pcm = array("h", (int(max(-1.0, min(1.0, v * gain * min(1.0, (n - i) / fade))) * 32767) for i, v in enumerate(mix.buf)))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    write(compose(), ROOT / "public" / "music" / "score.wav")
    print("ok")
