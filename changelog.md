# Changelog

All notable changes to the video watermarker script will be documented in this file.

## [0.1.0] - 2025-01-18

### Added

- Initial release of video watermarking functionality
- Support for multiple video formats (mp4, avi, mov, mkv, webm)
- Batch processing of videos in a directory
- Customizable watermark options:
  - Custom logo support (PNG with transparency)
  - Fallback text watermark when no logo is provided
  - Adjustable scale relative to video size
  - Adjustable transparency
  - Multiple position options (top-left, top-right, bottom-left, bottom-right, center)
- Comprehensive logging system:
  - Process logging to both file and console
  - Individual video processing status
  - Success/failure statistics
  - Timestamp-based log files

### Technical Features

- Maintains original video quality and codecs
- Preserves audio tracks
- Multi-threaded video processing
- Automatic output directory creation
- Error handling and graceful failure recovery
- Support for transparent PNG watermarks
- RGBA color space handling
- Maintains aspect ratio when scaling watermarks

### Dependencies

- moviepy: Video processing
- Pillow (PIL): Image handling
- numpy: Array operations
- Python 3.6+: Required for f-strings and type hints
- imageio-ffmpeg: Video encoding/decoding

### Usage

```bash
python video_watermarker.py --input-dir /path/to/videos \
                          --output-dir /path/to/output \
                          --logo-path /path/to/logo.png \
                          --position top-right \
                          --scale 0.1 \
                          --transparency 0.5
```
