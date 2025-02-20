# Video Watermarker

A Python tool for bulk watermarking videos with either custom logos or text watermarks.

## Features

- Bulk process multiple videos in a directory
- Support for custom logo watermarks or text-based watermarks
- Adjustable watermark positioning (top-left, top-right, bottom-left, bottom-right, center)
- Configurable watermark size and transparency
- Detailed logging of the watermarking process
- Supports multiple video formats (mp4, avi, mov, mkv, webm)

## Installation

1. Clone the repository:
```
git clone https://github.com/yourusername/video-watermarker.git
cd video-watermarker
```

2. Install required dependencies:
```
pip install moviepy Pillow numpy
```

## Usage

### Basic Usage
```
python video_watermarker.py --input-dir /path/to/videos --output-dir /path/to/output
```

### With Custom Logo
```
python video_watermarker.py --input-dir /path/to/videos --output-dir /path/to/output --logo-path your-logo.png
```

### Additional Options

- `--scale`: Watermark size relative to video size (default: 0.1)
- `--position`: Watermark position (choices: top-left, top-right, bottom-left, bottom-right, center)
- `--transparency`: Watermark transparency (0-1, where 1 is fully transparent)

Example with all options:
```
python video_watermarker.py \
    --input-dir /path/to/videos \
    --output-dir /path/to/output \
    --logo-path your-logo.png \
    --scale 0.15 \
    --position bottom-right \
    --transparency 0.3
```

## Requirements

- Python 3.6+
- moviepy>=1.0.3
- Pillow>=9.0.0
- numpy>=1.21.0

## Example Output Structure

```
output_directory/
├── watermarked_video1.mp4
├── watermarked_video2.mp4
└── video_watermark_log_20240318_143022.log
```

## Error Handling

- The script creates detailed logs in the output directory
- Failed videos are logged but don't stop the batch process
- Invalid input directories or files are reported with clear error messages

## License

MIT License - See LICENSE file for details