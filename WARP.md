# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is a Python-based video watermarking tool that processes videos in bulk, applying either custom logo watermarks or text-based watermarks. The tool is designed as a single-file command-line application with comprehensive logging and error handling.

## Development Commands

### Environment Setup
```bash
# Install dependencies
pip install moviepy Pillow numpy

# For development, also install FFmpeg if not already available:
# Windows: Automatically downloaded by moviepy
# Linux: sudo apt-get install ffmpeg  
# macOS: brew install ffmpeg
```

### Running the Application
```bash
# Basic usage with text watermark
python video_watermarker.py --input-dir "path/to/videos" --output-dir "path/to/output"

# With custom logo
python video_watermarker.py --input-dir "path/to/videos" --output-dir "path/to/output" --logo-path "your-logo.png"

# Full configuration example
python video_watermarker.py --input-dir "path/to/videos" --output-dir "path/to/output" --logo-path "your-logo.png" --scale 0.15 --position bottom-right --transparency 0.3
```

### Testing
```bash
# Test with sample video files (create test directory first)
mkdir test_videos test_output
python video_watermarker.py --input-dir test_videos --output-dir test_output --logo-path your-logo.png

# Validate output by checking log files in the output directory
```

## Architecture

### Single-File Application Structure
The entire application is contained in `video_watermarker.py` with the following key components:

**VideoWatermarker Class**: Main processing class that handles:
- Directory management and validation
- Watermark creation (both image and text-based)
- Video processing pipeline
- Logging configuration

**Key Methods**:
- `_create_watermark()`: Handles both custom logo loading and fallback text watermark generation
- `calculate_position()`: Computes watermark positioning based on video dimensions
- `process_video()`: Core video processing logic using MoviePy
- `process_directory()`: Batch processing coordinator

### Dependencies and Integration Points
- **MoviePy**: Primary video processing library (handles video I/O, compositing)
- **Pillow (PIL)**: Image processing and watermark creation
- **NumPy**: Array operations for image data conversion between PIL and MoviePy

### Watermark Processing Pipeline
1. Load/create watermark image (PNG with RGBA support)
2. Scale watermark relative to video dimensions
3. Calculate positioning coordinates
4. Create MoviePy ImageClip with transparency
5. Composite with original video
6. Export with original codec preservation

## Configuration

### Supported Parameters
- `--input-dir`: Source directory with video files (required)
- `--output-dir`: Destination directory (defaults to `input-dir/watermarked`)
- `--logo-path`: Custom watermark image (PNG recommended for transparency)
- `--scale`: Watermark size relative to video (default: 0.1)
- `--position`: Placement options (top-left, top-right, bottom-left, bottom-right, center)
- `--transparency`: Opacity level (0-1, where 1 is fully transparent)

### Supported Video Formats
- `.mp4` (primary format)
- `.avi` 
- `.mov`
- `.mkv`
- `.webm`

## Development Notes

### Error Handling Strategy
The application uses comprehensive logging and graceful failure handling:
- Individual video failures don't stop batch processing
- Detailed logs are created in the output directory with timestamps
- Both file and console logging are active during processing

### Resource Management
- Video clips are explicitly closed after processing to prevent memory leaks
- Font loading includes cross-platform fallbacks (Windows/Linux/macOS)
- FFmpeg integration is handled automatically by MoviePy

### Extending the Application
When adding new features, consider:
- **New watermark types**: Extend `_create_watermark()` method
- **Additional positioning**: Update `calculate_position()` method
- **New video formats**: Add to `supported_formats` set in `process_directory()`
- **Enhanced logging**: Modify logging configuration in `setup_logging()`

## Common Issues

### FFmpeg Not Found
If FFmpeg errors occur, ensure it's installed:
- Windows: Usually auto-installed by MoviePy
- Linux: `sudo apt-get install ffmpeg`
- macOS: `brew install ffmpeg`

### Memory Issues with Large Videos
For processing large video files:
- Process videos individually rather than in large batches
- Monitor system memory usage during processing
- Consider reducing video resolution if memory constraints exist

### Font Loading Issues
The application includes cross-platform font fallbacks, but if text rendering fails:
- Ensure system fonts are accessible
- Custom font paths can be added to `_get_default_font()` method