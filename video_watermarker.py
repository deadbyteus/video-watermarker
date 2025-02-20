import os
import sys
import argparse
from typing import Tuple, Optional
from datetime import datetime
import logging
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# Import core moviepy modules directly
import moviepy.config as conf
import moviepy.tools as tools
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import ImageClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip

def clean_path(path: str) -> str:
    """Clean path string by removing newlines and extra whitespace."""
    return path.strip().replace('\n', '').replace('\r', '')

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
                try:
                    font = ImageFont.truetype("arial.ttf", 24)
                except OSError:
                    font = ImageFont.load_default()
                draw.text((10, 10), 'unstabledb', font=font, fill=(255, 255, 255, 128))
                
            # Convert to numpy array for MoviePy
            return np.array(watermark)
            
        except Exception as e:
            logging.error(f"Error creating watermark: {e}")
            return None
            
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
            
            # Create clip from resized watermark with position and settings
            watermark_clip = (ImageClip(watermark_array, transparent=True)
                            .with_position(pos)
                            .with_duration(video.duration)
                            .with_opacity(1 - transparency))
            
            logging.info(f"Created watermark clip with size: {watermark_clip.size} at position {pos}")
            
            # Compose final video
            final_video = CompositeVideoClip([video, watermark_clip])
            
            logging.info(f"Writing output file: {output_path}")
            
            # Write output
            final_video.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
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
        supported_formats = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
        successful = 0
        failed = 0
        
        for filename in os.listdir(self.input_dir):
            if os.path.splitext(filename)[1].lower() in supported_formats:
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
                      help='Watermark transparency (0-1, where 1 is fully transparent)')
    
    args = parser.parse_args()
    
    watermarker = VideoWatermarker(args.input_dir, args.output_dir, args.logo_path)
    successful, failed = watermarker.process_directory(args.scale, args.position, args.transparency)
    
    logging.info(f"Processing complete. Successful: {successful}, Failed: {failed}")

if __name__ == "__main__":
    main()