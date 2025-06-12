"""
poster module handles the coordination of posting operations to Facebook.

This module contains functions for posting frames, subtitles and random crops
to Facebook pages in an organized way.
"""

# Standard library imports
from pathlib import Path
from time import sleep
from typing import Optional

# Third party imports
from src.facebook import FacebookAPI
from src.logger import get_logger
from src.frames_util import random_crop

# Initialize services
fb = FacebookAPI()
logger = get_logger(__name__)

# post frame
def post_frame(message: str, frame_path: Path) -> Optional[str]:
    """Post a frame and return the post ID."""
    try:
        post_id = fb.post(message, frame_path)
        if post_id:
            print("├── Frame has been posted", flush=True)
            sleep(2)
        else:
            logger.error("✖ Failed to post frame (main, post_frame)")
        return post_id
    except Exception as e:
        logger.error(f"✖ Error posting frame: {e}")
        return None
    
def post_subtitles(post_id: str, frame_number: int, episode: int, subtitle: str, configs: dict) -> Optional[str]:
    """Post the subtitles associated with the frame."""
    if not configs.get("posting", {}).get("posting_subtitles", False):
        return None

    if not subtitle:
        return None

    if configs.get("filters", {}).get("two_panels", {}).get("enabled", False):
        message = f"Episode {episode} Frame {frame_number}\n\n{subtitle}"
    else:
        message = subtitle

    try:
        subtitle_post_id = fb.post(message, None, post_id)
        if subtitle_post_id:
            print("└── Subtitle has been posted", flush=True)
            sleep(2)
        else:
            logger.error("✖ Failed to post subtitle (main, post_subtitles)")
        return subtitle_post_id
    except Exception as e:
        logger.error(f"✖ Error posting subtitle: {e}")
        return None


def post_random_crop(post_id: str, frame_path: Path, configs: dict) -> Optional[str]:
    """Post a random cropped frame."""
    if not configs.get("posting", {}).get("random_crop", {}).get("enabled", False):
        return None

    try:
        crop_path, crop_message = random_crop(frame_path, configs)
        if crop_path and crop_message:
            crop_post_id = fb.post(crop_message, crop_path, post_id)
            if crop_post_id:
                print("└── Random Crop has been posted", flush=True)
                sleep(2)
            else:
                logger.error("✖ Failed to post random crop (main, post_random_crop)")
            return crop_post_id
    except Exception as e:
        logger.error(f"✖ Error posting random crop: {e}")

    return None 


