---
name: testing-video-watermarker
description: How to end-to-end test the video_watermarker CLI (sample video generation, watermark verification, known pitfalls)
---

# Testing video-watermarker

## Unit tests
Run from repo root (root `conftest.py` puts repo root on sys.path):
```
pytest tests/ --cov=video_watermarker --cov-report=term-missing
```

## End-to-end CLI test
1. Generate a small input video with ffmpeg (no real footage needed):
   `ffmpeg -f lavfi -i testsrc=duration=3:size=640x360:rate=24 /tmp/in/sample.mp4`
2. Run the tool:
   `python3 video_watermarker.py --input-dir /tmp/in --output-dir /tmp/out --logo-path your-logo.png --position bottom-right --scale 0.15 --transparency 0.3`
3. Validate output with `ffprobe` (codec h264, same resolution/duration) and extract a frame:
   `ffmpeg -ss 1 -i /tmp/out/sample.mp4 -frames:v 1 frame.png`
4. Verify the watermark both visually and programmatically: pixel-diff the watermarked frame vs a frame from the input video — the diff should be large only in the watermark region (the log line "Created watermark clip with size ... at position (x, y)" gives the exact region).

## Pitfalls
- The text-watermark fallback (no `--logo-path`) draws WHITE semi-transparent text. `testsrc`'s top-right area is pure white, so the default top-right text watermark is invisible there. Use a dark background input (e.g. `-f lavfi -i color=c=0x203040:duration=3:size=640x360:rate=24`) or a non-top-right `--position` when testing the text fallback.
- `--transparency` accepts 0-1 or 0-255; in both scales HIGHER = more transparent. Expected opacity is logged (e.g. 150 → "opacity=41.2%").
- moviepy 2.2.1's `__version__` string incorrectly reports 2.1.2 — don't trust it for version checks.
- Drop a non-video file (e.g. `notes.txt`) into the input dir to confirm `process_directory` skips it (it must not appear in the output dir, and counts should only include videos).
