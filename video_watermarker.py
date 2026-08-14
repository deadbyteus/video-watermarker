# Standard library imports
import os
import argparse
from typing import Tuple, Optional, Any
from datetime import datetime
import logging

# Third-party imports
import numpy as np
from PIL import Image, ImageDraw
from moviepy import VideoFileClip, ImageClip, CompositeVideoClip  # type: ignore

# Local imports
from utils import (
    SUPPORTED_FORMATS,
    calculate_position,
    clean_path,
    get_default_font,
    normalize_transparency,
)

# Type aliases
VideoClip = Any  # For moviepy types that lack proper typing

class VideoWatermarker:
    def __init__(self, input_dir: str, output_dir: str, logo_path: str = None):
        """Initialize the video watermarker with directory paths and settings."""
        self.input_dir = clean_path(input_dir)
        self.output_dir = self._create_output_dir(clean_path(output_dir))
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
        try:
            if self.logo_path:
                watermark = Image.open(self.logo_path)
                watermark = watermark.convert('RGBA')
                logging.info(f"Watermark loaded: {watermark.size}")
            else:
                # Create text-based watermark
                watermark = Image.new('RGBA', (150, 50), (255, 255, 255, 0))
                draw = ImageDraw.Draw(watermark)
                font = get_default_font(24)
                draw.text((10, 10), 'your-logo', font=font, fill=(255, 255, 255, 128))
                
            # Convert to numpy array for MoviePy
            return np.array(watermark)
            
        except Exception as e:
            logging.error(f"Error creating watermark: {e}")
            return None
            
    def process_video(self, filename: str, scale: float = 0.1, position: str = 'top-right',
                     transparency: float = 0.5) -> Optional[str]:
        """Process a single video with watermark."""
        video_path = os.path.join(self.input_dir, filename)
        output_path = os.path.join(self.output_dir, filename)
        
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
            pos = calculate_position(video.size, (new_width, new_height), position)
            
            opacity = normalize_transparency(transparency)
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
            
            # Clean up resources
            video.close()
            watermark_clip.close()
            final_video.close()
            
            logging.info(f"Successfully processed: {filename}")
            return output_path
            
        except Exception as e:
            logging.error(f"Error processing {filename}: {str(e)}")
            return None
            
    def process_directory(self, scale: float = 0.1, position: str = 'top-right',
                         transparency: float = 0.5) -> Tuple[int, int]:
        """Process all compatible videos in the input directory."""
        successful = 0
        failed = 0
        
        for filename in os.listdir(self.input_dir):
            if os.path.splitext(filename)[1].lower() in SUPPORTED_FORMATS:
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
    
    watermarker = VideoWatermarker(args.input_dir, args.output_dir, args.logo_path)
    successful, failed = watermarker.process_directory(args.scale, args.position, args.transparency)
    
    logging.info(f"Processing complete. Successful: {successful}, Failed: {failed}")

if __name__ == "__main__":
    main()