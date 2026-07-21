"""Build the local Devpost demo video from verified screenshots.

All generated assets stay under docs/submission. Narration is synthesized by
Windows SAPI; ffmpeg performs the final H.264/AAC encoding.
"""

from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "demo-video-assets"
SHOTS = ROOT / "screenshots"
OUTPUT = ROOT / "incident-commander-demo.mp4"
FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"

SCENES = [
    {
        "slug": "01-title",
        "title": "INCIDENT COMMANDER AI",
        "subtitle": "From production signal to a verified, human-approved resolution package",
        "badge": "OPENAI BUILD WEEK 2026",
        "narration": (
            "Production incidents force small engineering teams to assemble evidence, diagnose risk, "
            "and coordinate a safe fix under pressure. Incident Commander AI turns that fragmented "
            "work into one supervised, auditable workflow."
        ),
    },
    {
        "slug": "02-intake",
        "title": "1  INTAKE",
        "subtitle": "Normalize the alert. Preserve provenance. Redact secrets before analysis.",
        "badge": "SIMULATED GOLDEN INCIDENT",
        "screenshot": "01-dashboard.png",
        "narration": (
            "This verified local demo begins with a checkout API incident: HTTP five hundred errors "
            "jump from zero point two to twelve point four percent. The interface clearly labels the "
            "golden telemetry as simulated. At ingestion, evidence receives stable provenance and "
            "secret-shaped values are redacted before any investigation component can use them."
        ),
    },
    {
        "slug": "03-investigate",
        "title": "2  INVESTIGATE",
        "subtitle": "Rank hypotheses with citations, then stop at the first human gate.",
        "badge": "EVIDENCE-GROUNDED",
        "screenshot": "02-investigation-approval.png",
        "narration": (
            "The investigation correlates the error window with a recent deployment, the stack trace, "
            "and the exact commit diff. Its top hypothesis identifies unsafe access to discount code in "
            "checkout dot T S. Every material claim cites persisted evidence, while uncertainty remains "
            "explicit. The proposed remediation is deliberately bounded to two files and forty lines. "
            "No workspace write is possible until an engineer approves this versioned plan."
        ),
    },
    {
        "slug": "04-verify",
        "title": "3  VERIFY",
        "subtitle": "Isolated patching, deterministic checks, risk review, and a second approval.",
        "badge": "NO MODEL SELF-GRADING",
        "screenshot": "03-review-approval.png",
        "narration": (
            "After approval, deterministic demo mode uses an explicitly simulated fixture code agent "
            "inside an isolated temporary workspace. It restores optional discount handling and adds the "
            "missing regression test. The platform reconstructs the stored diff and runs targeted tests, "
            "the full suite, lint, type checks, regression coverage, and deterministic risk review. The "
            "review package exposes the exact diff, artifact hash, and rollback guidance. A separate, "
            "artifact-bound approval is still required before creating the resolution package."
        ),
    },
    {
        "slug": "05-resolve",
        "title": "4  RESOLVE",
        "subtitle": "Audience-specific updates and one evidence-linked postmortem.",
        "badge": "RESOLUTION_DRAFTED",
        "screenshot": "04-resolution-package.png",
        "narration": (
            "The final local state is resolution drafted. The system records both approvals, a clearly "
            "labeled simulated draft pull request artifact, technical and stakeholder updates, and an "
            "evidence-linked postmortem. Repeated actions are idempotent, stale approvals fail closed, and "
            "high-risk authentication or schema changes are blocked by policy. No production action or "
            "real GitHub write is implied by this offline workflow."
        ),
    },
    {
        "slug": "06-proof",
        "title": "VERIFIED, NOT VAGUE",
        "subtitle": "A safe incident workflow that keeps engineers in control.",
        "badge": "SUBMISSION PROOF",
        "proof": [
            "175+ backend tests",
            "Ruff + strict mypy",
            "Web + contract tests",
            "21 Chromium flows",
            "5 complete demo runs",
            "Clean secret scan",
        ],
        "narration": (
            "The offline product path is backed by more than one hundred seventy-five backend tests, "
            "strict typing, browser automation, five complete demo runs, and a clean secret scan. Codex "
            "was used side by side to architect, implement, test, and verify this project. A separate "
            "credentialed GPT-five-point-six structured-output smoke test also passed. The "
            "screens shown here remain honest fixture evidence. Incident Commander AI: faster diagnosis, "
            "deterministic verification, and human control at every consequential boundary."
        ),
    },
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size)


def wrapped(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], width: int,
            fill: str, size: int, bold: bool = False, spacing: int = 12) -> int:
    chars = max(12, int(width / (size * 0.56)))
    lines = textwrap.wrap(text, width=chars)
    draw.multiline_text(xy, "\n".join(lines), font=font(size, bold), fill=fill, spacing=spacing)
    return len(lines) * (size + spacing)


def base_card() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (1920, 1080), "#0b0f16")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 12, 1080), fill="#26b5e8")
    draw.rectangle((12, 0, 1920, 6), fill="#26b5e8")
    return image, draw


def render_scene(scene: dict[str, object]) -> Path:
    image, draw = base_card()
    screenshot = scene.get("screenshot")
    if screenshot:
        shot = Image.open(SHOTS / str(screenshot)).convert("RGB")
        shot.thumbnail((1500, 1040), Image.Resampling.LANCZOS)
        x = 1920 - shot.width - 22
        y = (1080 - shot.height) // 2
        draw.rounded_rectangle((x - 4, y - 4, x + shot.width + 4, y + shot.height + 4),
                               radius=14, fill="#253044")
        image.paste(shot, (x, y))
        panel_width = x - 48
        draw.text((38, 58), str(scene["badge"]), font=font(18, True), fill="#55d6a8")
        wrapped(draw, str(scene["title"]), (38, 125), panel_width, "#f4f7fb", 46, True)
        draw.rectangle((38, 205, min(panel_width, 250), 211), fill="#26b5e8")
        wrapped(draw, str(scene["subtitle"]), (38, 250), panel_width, "#aab8cc", 25)
        draw.text((38, 945), "LOCAL VERIFIED DEMO", font=font(17, True), fill="#7f91aa")
        draw.text((38, 980), "Human approval required", font=font(17), fill="#7f91aa")
    else:
        draw.text((120, 130), str(scene["badge"]), font=font(24, True), fill="#55d6a8")
        wrapped(draw, str(scene["title"]), (120, 260), 1680, "#f4f7fb", 72, True, 18)
        draw.rectangle((120, 380, 440, 388), fill="#26b5e8")
        wrapped(draw, str(scene["subtitle"]), (120, 440), 1500, "#aab8cc", 34)
        proof = scene.get("proof")
        if proof:
            for index, item in enumerate(proof):
                col, row = index % 3, index // 3
                x, y = 120 + col * 550, 650 + row * 120
                draw.rounded_rectangle((x, y, x + 480, y + 78), 14, fill="#131b28", outline="#26364c")
                draw.text((x + 28, y + 22), str(item), font=font(24, True), fill="#e8edf5")
        else:
            draw.text((120, 760), "EVIDENCE  ->  PLAN  ->  PATCH  ->  VERIFY  ->  APPROVE",
                      font=font(27, True), fill="#26b5e8")
    out = ASSETS / f"{scene['slug']}.png"
    image.save(out, optimize=True)
    return out


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def duration(path: Path) -> float:
    value = subprocess.check_output(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        text=True,
    )
    return float(value.strip())


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    for scene in SCENES:
        render_scene(scene)
    (ASSETS / "narration.json").write_text(json.dumps(SCENES, indent=2), encoding="utf-8")

    sapi = ROOT / "synthesize-demo-narration.ps1"
    run("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(sapi))

    segments: list[Path] = []
    for scene in SCENES:
        slug = str(scene["slug"])
        wav = ASSETS / f"{slug}.wav"
        segment = ASSETS / f"{slug}.mp4"
        seconds = duration(wav) + 1.2
        run(
            FFMPEG, "-y", "-loglevel", "error", "-loop", "1", "-i", str(ASSETS / f"{slug}.png"),
            "-i", str(wav), "-filter_complex", "[1:a]apad=pad_dur=1.2[a]", "-map", "0:v", "-map", "[a]",
            "-t", f"{seconds:.3f}", "-vf", "fps=30,fade=t=in:st=0:d=0.35,fade=t=out:st="
            f"{max(0.1, seconds - 0.35):.3f}:d=0.35", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", str(segment),
        )
        segments.append(segment)

    concat = ASSETS / "concat.txt"
    concat.write_text("".join(f"file '{path.as_posix()}'\n" for path in segments), encoding="utf-8")
    run(
        FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat),
        "-c:v", "copy", "-af", "loudnorm=I=-16:LRA=7:TP=-1.5", "-c:a", "aac", "-b:a", "160k",
        "-ar", "48000",
        "-movflags", "+faststart", str(OUTPUT),
    )
    print(f"Built {OUTPUT} ({duration(OUTPUT):.2f}s)")


if __name__ == "__main__":
    main()
