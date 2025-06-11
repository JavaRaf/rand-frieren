"""
Filters module contains functions for applying filters to frames.
"""

# Standard library imports
from pathlib import Path
import random
from PIL import Image, ImageEnhance
from typing import Optional

# Third party imports
from src.logger import get_logger

# Define output directory for processed images
OUTPUT_DIR = Path.cwd() / "images"

# Initialize logger
logger = get_logger(__name__)


def none_filter(frame_path: Path) -> Path:
    """Returns the original frame without applying any filter."""
    return frame_path


def two_panels(frame_path1: Path, frame_path2: Path) -> Path:
    try:
        with Image.open(frame_path1) as img1, Image.open(frame_path2) as img2:
            image_width, image_height = img1.size
            img3 = Image.new("RGB", (image_width, image_height * 2))
            img3.paste(img1, (0, 0))
            img3.paste(img2, (0, image_height))

            output_path = OUTPUT_DIR / "_two_panels.jpg"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img3.save(output_path)
            logger.info(f"Saved two-panels image to {output_path}")
            return output_path
    except IOError as e:
        logger.error(f"IOError while processing two-panels image: {e}")
        return None


def mirror(frame_path) -> Path:
    """Mirrors the left or right side of the image randomly."""
    try:
        with Image.open(frame_path) as img:
            width, height = img.size
            output_img = Image.new("RGB", (width, height))

            if random.choice([True, False]):
                half = img.crop((0, 0, width // 2, height))
                mirrored_half = half.transpose(Image.FLIP_LEFT_RIGHT)
                output_img.paste(half, (0, 0))
                output_img.paste(mirrored_half, (width // 2, 0))
            else:
                half = img.crop((width // 2, 0, width, height))
                mirrored_half = half.transpose(Image.FLIP_LEFT_RIGHT)
                output_img.paste(mirrored_half, (0, 0))
                output_img.paste(half, (width // 2, 0))

        output_path = OUTPUT_DIR / "_mirror.jpg"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_img.save(output_path)
        logger.info(f"Saved mirrored image to {output_path}")
        return output_path
    except IOError as e:
        logger.error(f"IOError while processing mirror image: {e}")
        return None


def brightness_contrast(frame_path: Path, brightness: float = 0.8, contrast: float = 1.5) -> Path:
    """Applies a brightness and contrast filter to an image."""
    input_path = Path(frame_path)

    if not input_path.exists():
        return None
    
    output_path = OUTPUT_DIR / "_brightness_contrast.jpg"

    try:
        with Image.open(input_path) as img:
            img = ImageEnhance.Brightness(img).enhance(brightness)
            img = ImageEnhance.Contrast(img).enhance(contrast)
            img.save(output_path)
            logger.info(f"Saved brightness/contrast image to {output_path}")
        return output_path
    except IOError as e:
        logger.error(f"IOError while processing brightness/contrast image: {e}")
        return None


def negative(frame_path) -> Path:
    """Applies a negative filter."""
    try:
        with Image.open(frame_path) as img:
            output_img = img.convert("RGB").point(lambda x: 255 - x)

        output_path = OUTPUT_DIR / "_negative.jpg"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_img.save(output_path)
        logger.info(f"Saved negative image to {output_path}")
        return output_path
    except IOError as e:
        logger.error(f"IOError while processing negative image: {e}")
        return None


filter_registry = {
    'none_filter': none_filter,
    'two_panels': two_panels,
    'mirror': mirror,
    'negative': negative,
    'brightness_contrast': brightness_contrast
}


def apply_filter(filter_func, Framedata: list[dict]) -> Optional[Path]:
    """Apply a filter to the frame and return the path of the filtered frame."""

    if not isinstance(Framedata, list) or not all(isinstance(item, dict) for item in Framedata):
        logger.error("✖ Invalid Framedata format")
        return None

    if len(Framedata) == 2 and all('frame_path' in item for item in Framedata):
        try:
            output_path = filter_func(Framedata[0]['frame_path'], Framedata[1]['frame_path'])
            if output_path:
                return output_path
            else:
                logger.error("✖ Failed to apply filter")
        except Exception as e:
            logger.error(f"✖ Error applying filter: {e}")
            return None

    if len(Framedata) == 1 and 'frame_path' in Framedata[0]:
        try:
            output_path = filter_func(Framedata[0]['frame_path'])
            if output_path:
                return output_path
            else:
                logger.error("✖ Failed to apply filter")
        except Exception as e:
            logger.error(f"✖ Error applying filter: {e}")
            return None

    logger.error("✖ Invalid Framedata structure or missing keys")
    return None

def select_filter(configs: dict) -> callable:
    """
    Select an enabled filter based on the configuration and their respective weights.
    """
    active_filters = {}
    filters_config = configs.get("filters", {})
    
    for filter_name, filter_settings in filters_config.items():
        if isinstance(filter_settings, dict) and filter_settings.get("enabled", False):
            active_filters[filter_name] = filter_settings.get("percent", 0)

    if not active_filters:
        return filter_registry['none_filter']

    selected_filter = random.choices(
        list(active_filters.keys()), 
        weights=list(active_filters.values()), 
        k=1
    )[0]

    return filter_registry[selected_filter]
