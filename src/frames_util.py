from pathlib import Path
import random
import time
from typing import Optional

from PIL import Image
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.logger import get_logger
from src.frame_history import FrameHistory

logger = get_logger(__name__)

# Initialize the HTTP client with a timeout and headers
# The timeout is set to 30 seconds for the entire request and 10 seconds for the connection
client = httpx.Client(
    timeout=httpx.Timeout(30, connect=10),
    headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'})

# Initialize frame history
frame_history = FrameHistory()

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError))
)
def download_frame(configs: dict, frame_number: int, episode_number: int) -> Optional[Path]:
    """
    Download a frame from the specified episode and frame number.
    Implements exponential backoff for rate limiting and network errors.
    Returns None if all retry attempts fail.

    Args:
        configs (dict): Configuration dictionary containing episode data.
        frame_number (int): The frame number to download.
        episode_number (int): The episode number to download from.

    Returns:
        Optional[Path]: The path to the downloaded frame, or None if all retry attempts fail.
    """
    try:
        username = configs.get("github", {}).get("username")
        repo = configs.get("github", {}).get("repo")
        branch = configs.get("episodes", {}).get(episode_number, {}).get("branch")
        frames_dir = configs.get("episodes", {}).get(episode_number, {}).get("frames_dir")

        if not all([username, repo, branch, frames_dir]):
            logger.error("Error: Missing required configuration values for download subtitle", exc_info=True)
            return None

        frame_url = f'https://raw.githubusercontent.com/{username}/{repo}/{branch}/{frames_dir:02d}/{frame_number:04d}.jpg'
        
        # Add a small delay before each request to avoid rate limiting
        time.sleep(1)
        
        response = client.get(frame_url)
   
        if response.status_code == 429:
            proxy_url = f'https://images.weserv.nl/?url={frame_url}'
            response = client.get(proxy_url)

        if not response.status_code == 200:
            logger.error(
                f"HTTP error while downloading frame {frame_number} from episode {episode_number}: "
                f"{response.status_code} - {response.text}", exc_info=True
                )
            return None

        images_dir = Path.cwd() / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        frame_path = images_dir / f"{frame_number:04d}.jpg"
        frame_path.write_bytes(response.content)

        return frame_path
    except httpx.RequestError as e:
        logger.error(f"Request error while downloading frame {frame_number} from episode {episode_number}: {e}", exc_info=True)
        if not isinstance(e, httpx.HTTPStatusError) or e.response.status_code != 429:
            return None
        raise  # Re-raise only for rate limiting
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error while downloading frame {frame_number} from episode {episode_number}: "
                     f"{e.response.status_code} - {e.response.text}", exc_info=True)
        if e.response.status_code != 429:
            return None
        raise  # Re-raise only for rate limiting
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return None


def get_random_frame(configs: dict) -> tuple[int, int] | None:
    """
    Select a random frame from the episodes configuration.
    Avoids returning frames that have been used before.

    Args:
        configs (dict): Configuration dictionary containing episode data.
    
    Returns:
        tuple[int, int] | None: A tuple containing the random frame number and episode number.
        Returns None if no valid frame is found or if all frames have been used.
    """
    episodes: dict = configs.get("episodes", {})
    if not episodes:
        logger.error(f"No episodes found in the configuration.")
        return None

    # Try to find an unused frame
    max_attempts = 500  # Prevent infinite loops
    attempts = 0
    
    while attempts < max_attempts:
        random_episode_key = random.choice(list(episodes.keys()))
        episode_data: dict = episodes.get(random_episode_key, {})
        number_of_frames = episode_data.get("number_of_frames", 0)

        if number_of_frames <= 0:
            logger.error(f"No frames available in episode {random_episode_key}.", exc_info=True)
            return None

        frame_number = random.randint(1, number_of_frames)
        episode_number = int(random_episode_key)
        
        if not frame_history.is_frame_used(frame_number, episode_number):
            frame_history.add_frame(frame_number, episode_number)
            return frame_number, episode_number
            
        attempts += 1

    logger.warning(f"Could not find an unused frame after maximum attempts.")
    return None

   
def random_crop(frame_path: Path, configs: dict) -> tuple[Path, str] | None:
    """
    Returns a random crop of the frame.

    Args:
        frame_path: Path to the frame image.

    Returns:
        tuple[Path, str]: Tuple containing the path to the cropped image and the crop coordinates.
    """
    if not isinstance(frame_path, Path):
        logger.error(f"frame_path must be a Path object ", exc_info=True)
        return None, None

    if not frame_path.is_file():
        logger.error(f"frame_path must be a file", exc_info=True)
        return None, None

    try:
        min_x: int = configs.get("posting", {}).get("random_crop", {}).get("min_x", 200)
        min_y: int = configs.get("posting", {}).get("random_crop", {}).get("min_y", 600)

        # Random crop dimensions. perfect square.
        crop_width = crop_height = random.randint(min_x, min_y)

        with Image.open(frame_path) as img:
            image_width, image_height = img.size

            if image_width < crop_width or image_height < crop_height:
                logger.error(f"Image {frame_path} is too small for the crop size.", exc_info=True)
                return None, None

            # Generate random crop coordinates
            crop_x = random.randint(0, image_width - crop_width)
            crop_y = random.randint(0, image_height - crop_height)

            # Crop image
            cropped_img = img.crop(
                (crop_x, crop_y, crop_x + crop_width, crop_y + crop_height)
            )

            # Save the cropped image
            cropped_path = (
                Path.cwd()
                / "temp"
                / f"cropped_frame{frame_path.suffix}"
            )
            cropped_path.parent.mkdir(exist_ok=True)

            cropped_img.save(cropped_path)
            message = (
                f"Random Crop. [{crop_width}x{crop_height} ~ X: {crop_x}, Y: {crop_y}]"
            )

            return cropped_path, message

    except Exception as e:
        logger.error(f"Failed to crop image: {str(e)}", exc_info=True)
        return None, None