# Standard library imports
import os
import logging
from typing import Tuple

# Third-party imports
from PIL import ImageFont

# Video formats supported for watermarking
SUPPORTED_FORMATS = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}


def clean_path(path: str) -> str:
    """Clean path string by removing newlines and extra whitespace."""
    return path.strip().replace('\n', '').replace('\r', '')


def get_default_font(size: int = 24) -> ImageFont.FreeTypeFont:
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


def calculate_position(video_size: Tuple[int, int], watermark_size: Tuple[int, int],
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


def normalize_transparency(transparency: float) -> float:
    """Convert a transparency value on the 0-1 or 0-255 scale to an opacity in [0, 1].

    On both scales a HIGHER value means more transparent (weaker):
    0-1: 0=solid, 1=invisible. 0-255: 0=solid, 255=invisible.
    """
    if transparency > 1:
        return max(0, min(1, 1 - (transparency / 255)))
    return max(0, min(1, 1 - transparency))
