# Demo Video Production and Verification

Produced locally from the four verified browser screenshots. Nothing was
uploaded or published externally.

## Deliverables

- `incident-commander-demo.mp4` — final narrated submission video.
- `incident-commander-demo-captions.srt` — accessible sidecar captions.
- `demo-video-contact-sheet.png` — six-frame visual-QA contact sheet.
- `incident-commander-demo.ffprobe.json` — retained playback metadata.
- `build-demo-video.py` and `synthesize-demo-narration.ps1` — reproducible local build.

## Truthful evidence boundary

The video labels the end-to-end golden workflow as a local, simulated-fixture
demo. It does not claim live telemetry, a live Codex patch turn, a GitHub write,
deployment, or production action. The closing slide separately states that the
credentialed GPT-5.6 structured-output smoke test passed; it does not represent
the fixture screenshots as proof of that call.

## Playback metadata

- Duration: `132.410667` seconds (`2:12.411`), inside the requested 2:00–2:30 range.
- Resolution: `1920x1080` at `30 fps`.
- Video: H.264, `yuv420p`.
- Audio: AAC, stereo, `48 kHz`, loudness-normalized for web playback.
- File size: `4,732,658` bytes.
- SHA-256: `81C580B8F30555C8CE763076DE93600E5CAA718A5D69CD7351578BCE5DA8BB72`.

The retained `ffprobe` output is in `incident-commander-demo.ffprobe.json`.
An independent full decode completed with zero ffmpeg errors. Audio QA reported
a healthy speech peak below clipping after loudness normalization.

## Visual QA

The contact sheet samples all six scenes: title, intake, investigation,
verification, resolution, and final proof. Manual inspection confirmed:

- title and scene caption rails remain readable at 1080p;
- each screenshot is contained without stretching or clipped edges;
- simulated-data and human-approval disclosures are visible;
- SHA values remain inside the captured UI layout;
- the final proof slide is legible and makes no external-action claim;
- fade-in/fade-out frames render without corruption.

Rebuild from the repository root with:

```powershell
python docs/submission/build-demo-video.py
```

