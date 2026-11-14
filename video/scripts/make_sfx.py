"""Efectos de sonido y base musical sintetizados por código (sin descargas): public/sfx/*.wav y public/music/pad.wav.

    ..\\.venv\\Scripts\\python scripts\\make_sfx.py

Son BORRADORES para dar ritmo al montaje; se pueden sustituir por librerías con licencia manteniendo los nombres.
"""

import math
import random
import struct
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SR = 22050
random.seed(2297)


def write(path: Path, samples: list[float], gain: float = 0.9) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    peak = max(1e-9, max(abs(s) for s in samples))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(32767 * gain * s / peak)) for s in samples))


def env(i: int, n: int, attack: float = 0.005, decay: float = 4.0) -> float:
    t = i / SR
    a = min(1.0, t / attack) if attack > 0 else 1.0
    return a * math.exp(-decay * t / (n / SR))


def thump(dur: float = 0.6) -> list[float]:
    n = int(SR * dur)
    return [env(i, n, 0.002, 6) * (math.sin(2 * math.pi * (70 - 30 * i / n) * i / SR) + 0.25 * random.uniform(-1, 1) * math.exp(-i / 300)) for i in range(n)]


def crack(dur: float = 0.7) -> list[float]:
    n = int(SR * dur)
    out, prev = [], 0.0
    for i in range(n):
        x = random.uniform(-1, 1) * (1.0 if random.random() < 0.15 + 0.5 * math.exp(-i / 2000) else 0.2)
        prev = x - 0.6 * prev  # realce de agudos: cristal
        out.append(env(i, n, 0.001, 5) * prev + 0.4 * env(i, n, 0.001, 9) * math.sin(2 * math.pi * 2400 * i / SR))
    return out


def glitch(dur: float = 0.5) -> list[float]:
    n = int(SR * dur)
    out, f = [], 300.0
    for i in range(n):
        if i % 800 == 0:
            f = random.choice([180, 300, 520, 900, 1400])
        out.append(env(i, n, 0.001, 2) * (1 if math.sin(2 * math.pi * f * i / SR) > 0 else -1) * (0.6 if (i // 400) % 3 else 0.1))
    return out


def whoosh(dur: float = 0.55) -> list[float]:
    n = int(SR * dur)
    out, lp = [], 0.0
    for i in range(n):
        t = i / n
        cutoff = 0.02 + 0.5 * math.sin(math.pi * t)
        lp += cutoff * (random.uniform(-1, 1) - lp)
        out.append(lp * math.sin(math.pi * t) ** 1.5)
    return out


def scratch(dur: float = 1.1) -> list[float]:
    n = int(SR * dur)
    out, hp = [], 0.0
    for i in range(n):
        stroke = 0.5 + 0.5 * math.sin(2 * math.pi * 7 * i / SR) ** 2
        x = random.uniform(-1, 1)
        hp = x - 0.85 * hp
        out.append(0.6 * hp * stroke * min(1, i / 400) * min(1, (n - i) / 2000))
    return out


def pop(dur: float = 0.12) -> list[float]:
    n = int(SR * dur)
    return [env(i, n, 0.001, 8) * math.sin(2 * math.pi * (900 + 600 * i / n) * i / SR) for i in range(n)]


def tick(dur: float = 0.05) -> list[float]:
    n = int(SR * dur)
    return [env(i, n, 0.0005, 12) * math.sin(2 * math.pi * 2200 * i / SR) for i in range(n)]


def pad(dur: float = 120.0) -> list[float]:
    """Acordes lentos (Am–F–C–G, 8 s cada uno) con ataque suave y un pulso grave; muy por debajo de la voz."""
    chords = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [196.0, 261.63, 329.63], [196.0, 246.94, 293.66]]
    n = int(SR * dur)
    seg = 8 * SR
    out = []
    for i in range(n):
        k = (i // seg) % 4
        local = (i % seg) / seg
        fade = math.sin(math.pi * local) ** 0.6
        s = sum(math.sin(2 * math.pi * f * i / SR) + 0.3 * math.sin(2 * math.pi * 2 * f * i / SR + 1) for f in chords[k])
        bass = 0.6 * math.sin(2 * math.pi * chords[k][0] / 2 * i / SR) * (0.6 + 0.4 * math.sin(2 * math.pi * 0.5 * i / SR))
        edge = min(1, i / (3 * SR), (n - i) / (3 * SR))
        out.append(edge * (fade * s / 4 + bass / 3))
    return out


def main() -> None:
    sfx = ROOT / "public" / "sfx"
    for name, fn in {"thump": thump, "crack": crack, "glitch": glitch, "whoosh": whoosh, "scratch": scratch, "pop": pop, "tick": tick}.items():
        write(sfx / f"{name}.wav", fn())
    write(ROOT / "public" / "music" / "pad.wav", pad(), gain=0.6)
    print("ok")


if __name__ == "__main__":
    main()
