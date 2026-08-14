# Standard library imports
import os
import sys
import argparse
from typing import Tuple, Optional, Any
from datetime import datetime
import logging

# Third-party imports
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoFileClip, ImageClip, CompositeVideoClip  # type: ignore

# Type aliases
VideoClip = Any  # For moviepy types that lack proper typing

def clean_path(path: str) -> str:
    """Clean path string by removing newlines and extra whitespace."""
    return path.strip().replace('\n', '').replace('\r', '')

class VideoWatermarker:
    def __init__(self, input_dir: str, output_dir: str, logo_path: str = None):
        """Initialize the video watermarker with directory paths and settings."""
        self.input_dir = clean_path(input_dir)
        if not os.path.isdir(self.input_dir):
            raise NotADirectoryError(f"Input directory does not exist: {self.input_dir}")
        self.output_dir = self._create_output_dir(clean_path(output_dir) if output_dir else '')
        self.logo_path = clean_path(logo_path) if logo_path else None
        self.setup_logging()
        self.watermark_img = self._create_watermark()
        
    def setup_logging(self):
        """Set up logging configuration."""
        log_file = os.path.join(self.output_dir, f'video_watermark_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
    def _create_output_dir(self, output_dir: str) -> str:
        """Create output directory if it doesn't exist."""
        if not output_dir:
            output_dir = os.path.join(self.input_dir, 'watermarked')
        os.makedirs(output_dir, exist_ok=True)
        return output_dir
        
    def _create_watermark(self) -> np.ndarray:
        """Create or load watermark image."""
        if self.logo_path:
            try:
                watermark = Image.open(self.logo_path)
                watermark = watermark.convert('RGBA')
            except (OSError, ValueError) as e:
                raise ValueError(f"Could not load watermark image '{self.logo_path}': {e}") from e
            logging.info(f"Watermark loaded: {watermark.size}")
        else:
            # Create text-based watermark
            watermark = Image.new('RGBA', (150, 50), (255, 255, 255, 0))
            draw = ImageDraw.Draw(watermark)
            font = self._get_default_font(24)
            draw.text((10, 10), 'your-logo', font=font, fill=(255, 255, 255, 128))

        # Convert to numpy array for MoviePy
        return np.array(watermark)
            
    def _get_default_font(self, size: int = 24) -> ImageFont.FreeTypeFont:
        """Get a default font that works across different operating systems."""
        try:
            # Try common system fonts based on OS
            if os.name == 'nt':  # Windows
                font_path = "arial.ttf"
            elif os.name == 'posix':  # Linux/Mac
                font_paths = [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
                    "/System/Library/Fonts/Helvetica.ttc",  # MacOS
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"  # Some Linux
                ]
                font_path = next((path for path in font_paths if os.path.exists(path)), None)
            else:
                font_path = None

            if font_path and os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
        except Exception as e:
            logging.warning(f"Could not load system font: {e}")
        
        return ImageFont.load_default()
            
    def calculate_position(self, video_size: Tuple[int, int], watermark_size: Tuple[int, int],
                         position: str = 'top-right', padding: int = 10) -> Tuple[int, int]:
        """Calculate watermark position based on specified location."""
        video_width, video_height = video_size
        watermark_width, watermark_height = watermark_size
        
        positions = {
            'top-left': (padding, padding),
            'top-right': (video_width - watermark_width - padding, padding),
            'bottom-left': (padding, video_height - watermark_height - padding),
            'bottom-right': (video_width - watermark_width - padding, video_height - watermark_height - padding),
            'center': ((video_width - watermark_width) // 2, (video_height - watermark_height) // 2)
        }
        return positions.get(position, positions['top-right'])
        
    def process_video(self, filename: str, scale: float = 0.1, position: str = 'top-right',
                     transparency: float = 0.5) -> Optional[str]:
        """Process a single video with watermark."""
        video_path = os.path.join(self.input_dir, filename)
        output_path = os.path.join(self.output_dir, filename)
        
        video = None
        watermark_clip = None
        final_video = None
        try:
            logging.info(f"Starting to process {filename}")
            
            # Load video
            video = VideoFileClip(video_path)
            logging.info(f"Loaded video: {video.size}")
            
            # Load the watermark and convert to array at the start
            watermark_array = np.array(self.watermark_img).astype('uint8')
            watermark_pil = Image.fromarray(watermark_array)
            
            # Calculate new size
            new_width = int(video.w * scale)
            new_height = int(new_width * watermark_pil.height / watermark_pil.width)
            
            # Resize watermark image
            watermark_pil = watermark_pil.resize((new_width, new_height), Image.LANCZOS)
            
            # Convert back to numpy array for MoviePy
            watermark_array = np.array(watermark_pil)
            
            # Get position
            pos = self.calculate_position(video.size, (new_width, new_height), position)
            
            # Normalize transparency: support 0-1 (where 1=fully transparent) or 0-255
            # For 0-255: HIGHER = more transparent (weaker). 255=invisible, 0=solid.
            if transparency > 1:
                opacity = max(0, min(1, 1 - (transparency / 255)))
            else:
                opacity = max(0, min(1, 1 - transparency))
            if opacity < 0.05:
                logging.warning(
                    f"Watermark opacity is very low ({opacity:.1%}). "
                    f"With 0-255 scale, use a SMALL number for a visible logo (e.g. 0-80); "
                    f"250 means almost fully transparent."
                )
            
            # Create clip from resized watermark with position and settings
            # CRITICAL: Match video FPS to avoid blur/shake from frame rate mismatch
            watermark_clip = (ImageClip(watermark_array, transparent=True)
                            .with_duration(video.duration)
                            .with_fps(video.fps)
                            .with_position(pos)
                            .with_opacity(opacity))
            
            logging.info(
                f"Created watermark clip with size: {watermark_clip.size} at position {pos}, "
                f"opacity={opacity:.1%}"
            )
            
            # Compose final video - set explicit FPS to avoid timing/quality issues
            final_video = CompositeVideoClip([video, watermark_clip]).with_fps(video.fps)
            
            logging.info(f"Writing output file: {output_path}")
            
            # Write output - use CRF for quality, preset for encoding stability
            final_video.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                ffmpeg_params=['-crf', '18', '-preset', 'medium'],
                threads=4,
                logger=None  # Disable MoviePy's built-in logger
            )
            
            logging.info(f"Successfully processed: {filename}")
            return output_path
            
        except Exception:
            logging.exception(f"Error processing {filename}")
            return None
        finally:
            # Clean up resources even if processing failed
            for clip in (final_video, watermark_clip, video):
                if clip is not None:
                    try:
                        clip.close()
                    except Exception as e:
                        logging.warning(f"Error closing clip for {filename}: {e}")
            
    def process_directory(self, scale: float = 0.1, position: str = 'top-right',
                         transparency: float = 0.5) -> Tuple[int, int]:
        """Process all compatible videos in the input directory."""
        supported_formats = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
        successful = 0
        failed = 0
        
        video_files = [
            filename for filename in os.listdir(self.input_dir)
            if os.path.splitext(filename)[1].lower() in supported_formats
        ]
        if not video_files:
            logging.warning(f"No supported video files found in {self.input_dir}")
            
        for filename in video_files:
            result = self.process_video(filename, scale, position, transparency)
            if result:
                successful += 1
            else:
                failed += 1
                    
        return successful, failed

def main():
    parser = argparse.ArgumentParser(description='Bulk Video Watermarking Tool')
    parser.add_argument('--input-dir', required=True, help='Input directory containing videos')
    parser.add_argument('--output-dir', help='Output directory for watermarked videos')
    parser.add_argument('--logo-path', help='Path to watermark image')
    parser.add_argument('--scale', type=float, default=0.1, help='Watermark scale relative to video size')
    parser.add_argument('--position', default='top-right',
                      choices=['top-left', 'top-right', 'bottom-left', 'bottom-right', 'center'],
                      help='Watermark position')
    parser.add_argument('--transparency', type=float, default=0.5,
                      help='How transparent the watermark is (weaker = higher number). '
                           '0-1: 0=solid, 1=invisible. '
                           '0-255: 0=solid, 255=invisible (e.g. 200≈22%% visible, 250≈2%% visible).')
    
    args = parser.parse_args()
    
    try:
        watermarker = VideoWatermarker(args.input_dir, args.output_dir, args.logo_path)
    except (NotADirectoryError, ValueError, OSError) as e:
        logging.error(str(e))
        sys.exit(1)
        
    successful, failed = watermarker.process_directory(args.scale, args.position, args.transparency)
    
    logging.info(f"Processing complete. Successful: {successful}, Failed: {failed}")
    if failed:
        sys.exit(1)

if __name__ == "__main__":
    main()