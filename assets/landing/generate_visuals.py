"""Generate the landing page visuals with Google's latest models.

Images: Nano Banana 2.1 (gemini-nano-banana-2.1) via generateContent.
Motion: Gemini Omni 1.2 Flash (gemini-omni-1.2-flash) via the Interactions API, image -> video.

Usage (from the repo root, GEMINI_API_KEY in .env):
    .venv/Scripts/python.exe assets/landing/generate_visuals.py images [name ...]
    .venv/Scripts/python.exe assets/landing/generate_visuals.py videos [name ...]

Raw outputs go to assets/landing/v2/raw/; the page uses the compressed files in assets/landing/v2/.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

IMAGE_MODEL = "gemini-nano-banana-2.1"
VIDEO_MODEL = "gemini-omni-1.2-flash"
API = "https://generativelanguage.googleapis.com/v1beta"
OUT = Path(__file__).resolve().parent / "v2"
RAW = OUT / "raw"
TIMEOUT_S = 600

STYLE = (
    "Cinematic 3D render in a dark blueprint world: deep teal-black background (#051a22), a faint fine grid, "
    "soft volumetric haze. The only light comes from glowing mint (#22d3b4) and cyan (#2a93c9) sources, with "
    "amber (#e7a72a) and red (#ef5b4c) used sparingly and only as warning accents. Precise, calm, premium "
    "editorial tech mood, shallow depth of field, subtle film grain, wide 16:9 composition. "
    "Absolutely no text, letters, numbers, logos, watermarks or readable UI anywhere in the image. "
)

# name -> (where to leave empty space for the headline, scene, motion prompt or None)
SCENES: dict[str, tuple[str, str, str | None]] = {
    "hero": (
        "Keep the left 40% of the frame dark and empty for a headline.",
        "Seen from behind, a single engineer sits at a small desk at the bottom of an immense dark atrium. "
        "High above, thousands of translucent glowing code panels drift slowly down like a waterfall; most are dim, "
        "a few glow mint. One soft beam of light falls on the desk, where a fountain pen rests beside a single sheet.",
        "Very slow cinematic push-in towards the desk. The translucent code panels keep drifting gently downward, "
        "a few of them brighten to mint and fade. Dust particles float in the light beam. The engineer stays still. "
        "Smooth, continuous, calm motion, no cuts, quiet ambient room tone only, no music, no voices.",
    ),
    "friday": (
        "Keep the left 45% of the frame darker and calm for text.",
        "A small desk in a dim office at dusk, warm low sunlight mixing with teal shadows. From the desk rises an "
        "impossibly tall, slightly leaning tower of hundreds of translucent glass document sheets, each faintly etched "
        "with abstract unreadable lines of code, disappearing into the darkness above. Next to the tower floats a small "
        "glowing green holographic check-mark badge, overconfident and reassuring. The office chair is empty.",
        "Slow upward tilt following the tall tower of glass sheets. The sheets shiver and sway very slightly as if "
        "about to topple. The small green check-mark badge pulses softly. Dusk light shifts subtly. "
        "Continuous single shot, no cuts, faint office ambience only, no music, no voices.",
    ),
    "t1": (
        "Keep the left third calm and dark.",
        "Isometric view: a river of small glowing square file tiles flows from the left into a thin vertical gate of "
        "light. The gate splits them into three lanes: most tiles flow calmly into a wide mint lane, a handful into a "
        "narrower amber lane, and a single tile into a narrow red lane.",
        "The file tiles keep flowing steadily through the vertical light gate and split into the three lanes; "
        "most go to the wide mint lane, a few to amber, one to red. Camera holds almost still with a faint drift. "
        "Seamless loopable motion, no cuts, soft electronic hum only, no music, no voices.",
    ),
    "t2": (
        "Keep the left third calm and dark.",
        "Macro shot of a sealed glass test chamber on a dark laboratory bench. Inside, a floating crystal block made of "
        "abstract code fragments is pierced by a thin precise probe beam. The left half of the chamber glows red, the "
        "right half glows mint, as a before-and-after comparison. Scientific, precise, clinical.",
        "The thin probe beam scans slowly across the floating crystal block. The red glow on the left fades as the "
        "mint glow on the right brightens, then holds. Tiny particles drift inside the sealed chamber. "
        "Static camera with a very slow dolly, no cuts, faint lab hum only, no music, no voices.",
    ),
    "t3": (
        "Keep the left third calm and dark.",
        "A courtroom-like dark void. Two tall faceless abstract monolith figures face each other across a long dark "
        "table: the left one glows amber-red like a prosecutor, the right one glows mint like a defender. Between them, "
        "above the table, hovers a fractured glass cube with one cracked fragment pulled slightly out, lit from both sides.",
        "The fractured glass cube rotates slowly between the two monolith figures; the cracked fragment drifts out "
        "and back. The amber-red and mint lights pulse alternately as if arguing. Slow orbiting camera, no cuts, "
        "low tense ambient drone only, no music, no voices.",
    ),
    "trust": (
        "Keep the right 40% of the frame dark and empty for text.",
        "A long row of round glowing medallion seals resting on dark glass shelves. Most glow steady mint. One in the "
        "middle is cracked and its light has dimmed to amber. Behind it, a thin vertical crack in a dark glass wall "
        "leaks a sliver of red light.",
        "Slow lateral tracking shot along the row of glowing mint seals. The cracked seal in the middle flickers and "
        "dims to amber; the thin red crack in the wall behind it glows a little brighter. No cuts, "
        "quiet ambience only, no music, no voices.",
    ),
    "escape": (
        "Keep the right 40% of the frame dark and empty for text.",
        "A tall wall made of rows of glowing mint glass panels, orderly and calm. Through one narrow gap between two "
        "panels, a single small glowing red fragment is slipping out into the darkness. A soft amber searchlight beam "
        "has just started to sweep towards the gap.",
        "The small red fragment slowly slips through the narrow gap in the mint glass wall and drifts out. The amber "
        "searchlight beam sweeps towards it and finds it; the nearby mint panels dim to amber. Slow push-in, no cuts, "
        "low tense ambience only, no music, no voices.",
    ),
    "sign": (
        "Keep the left 40% darker for text.",
        "Top-down view of a dark desk. Hundreds of faint translucent pages fade into the darkness around the edges of "
        "the frame. In the center, twelve crisp glowing pages are laid out neatly in front of a human hand holding a "
        "fountain pen, about to sign a single document whose three sections are blank.",
        "The hundreds of faint pages around the edges slowly fade further into darkness while the twelve central pages "
        "brighten. The hand lowers the fountain pen towards the document. Very slow top-down push-in, no cuts, "
        "soft paper and room ambience only, no music, no voices.",
    ),
    "modal": (
        "Keep the left third calm and dark.",
        "A vast dark space filled with a precise floating grid of about sixty small sealed glass cubes, each holding a "
        "tiny glowing mint light. No cables, no connections between them: each one is isolated. Some cubes at the edge "
        "are dissolving into fine particles. Cyan rim light.",
        "The sealed glass cubes light up one after another across the grid in a fast wave, glow mint, then several "
        "dissolve into fine drifting particles. Slow forward drift of the camera through the grid, no cuts, "
        "soft electronic ambience only, no music, no voices.",
    ),
    "archive": (
        "Keep the center calm for text overlay.",
        "A long dark archive corridor of open drawers and shelves receding into the distance, each drawer softly lit "
        "from inside with mint light, neat and orderly, inviting inspection.",
        None,
    ),
}


def api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        env = Path(__file__).resolve().parents[2] / ".env"
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("GEMINI_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"')
    if not key:
        sys.exit("GEMINI_API_KEY not found in the environment or .env")
    return key


def post(url: str, body: dict) -> dict:
    resp = requests.post(url, json=body, headers={"x-goog-api-key": api_key()}, timeout=TIMEOUT_S)
    if resp.status_code != 200:
        raise RuntimeError(f"{resp.status_code}: {resp.text[:800]}")
    return resp.json()


def generate_image(name: str) -> Path:
    space, scene, _ = SCENES[name]
    body = {
        "contents": [{"parts": [{"text": STYLE + space + " Scene: " + scene}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {"aspectRatio": "16:9", "imageSize": "2K"},
        },
    }
    data = post(f"{API}/models/{IMAGE_MODEL}:generateContent", body)
    for part in data["candidates"][0]["content"]["parts"]:
        inline = part.get("inlineData") or part.get("inline_data")
        if inline:
            ext = ".png" if "png" in inline.get("mimeType", inline.get("mime_type", "")) else ".jpg"
            path = RAW / f"{name}{ext}"
            path.write_bytes(base64.b64decode(inline["data"]))
            return path
    raise RuntimeError(f"{name}: no image in response: {json.dumps(data)[:600]}")


def find_raw_image(name: str) -> Path:
    for ext in (".png", ".jpg"):
        if (RAW / f"{name}{ext}").exists():
            return RAW / f"{name}{ext}"
    raise FileNotFoundError(f"generate the image for {name} first")


def generate_video(name: str) -> Path:
    _, _, motion = SCENES[name]
    if motion is None:
        raise ValueError(f"{name} has no motion prompt")
    img = find_raw_image(name)
    mime = "image/png" if img.suffix == ".png" else "image/jpeg"
    resolution = "1080p" if name == "hero" else "720p"
    body = {
        "model": VIDEO_MODEL,
        "input": [
            {"type": "image", "data": base64.b64encode(img.read_bytes()).decode(), "mime_type": mime},
            {"type": "text", "text": "Animate this exact image as the first frame, keeping its composition, palette "
                                     "and style. Do not add any text. " + motion},
        ],
        "response_format": {"type": "video", "aspect_ratio": "16:9", "resolution": resolution, "duration": "8s"},
        "background": False, "store": False, "stream": False,
    }
    data = post(f"{API}/interactions", body)
    for step in data.get("steps", []):
        for item in step.get("content", []) or []:
            if item.get("type") == "video":
                path = RAW / f"{name}.mp4"
                if item.get("data"):
                    path.write_bytes(base64.b64decode(item["data"]))
                elif item.get("uri"):
                    path.write_bytes(download_uri(item["uri"]))
                else:
                    break
                return path
    raise RuntimeError(f"{name}: no video in response: {json.dumps(data)[:800]}")


def download_uri(uri: str) -> bytes:
    for _ in range(60):
        resp = requests.get(uri, headers={"x-goog-api-key": api_key()}, timeout=TIMEOUT_S, allow_redirects=True)
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("video"):
            return resp.content
        time.sleep(5)
    raise RuntimeError(f"video at {uri} never became available")


def run(kind: str, names: list[str]) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    fn = generate_image if kind == "images" else generate_video
    todo = names or [n for n, s in SCENES.items() if kind == "images" or s[2]]

    def one(name: str) -> str:
        t0 = time.time()
        try:
            return f"OK   {name:8s} {fn(name).name}  ({time.time() - t0:.0f}s)"
        except Exception as exc:  # report every failure, keep the other generations going
            return f"FAIL {name:8s} {exc}"

    with ThreadPoolExecutor(max_workers=4) as pool:
        for line in pool.map(one, todo):
            print(line, flush=True)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("images", "videos"):
        sys.exit(__doc__)
    run(sys.argv[1], sys.argv[2:])
