import random
from dataclasses import dataclass
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_fixed
from typing import Optional
from typing import Optional
import httpx
from PIL import Image

# Initialize the HTTP client with a timeout and headers
# The timeout is set to 30 seconds for the entire request and 10 seconds for the connection
client = httpx.Client(
    timeout=httpx.Timeout(30, connect=10),
    headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'})


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def download_frame(configs: dict, frame_number: int, episode_number: int) -> Optional[Path]:
    """
    Download a frame from the specified episode and frame number.

    Args:
        configs (dict): Configuration dictionary containing episode data.
        frame_number (int): The frame number to download.
        episode_number (int): The episode number to download from.

    Returns:
        Optional[Path]: The path to the downloaded frame, or None if an error occurs.
    """
    try:
        username = configs.get("github", {}).get("username")
        repo = configs.get("github", {}).get("repo")
        branch = configs.get("episodes", {}).get(episode_number, {}).get("branch")
        frames_dir = configs.get("episodes", {}).get(episode_number, {}).get("frames_dir")

        if not all([username, repo, branch, frames_dir]):
            print("Error: Missing required configuration values.")
            return None

        frame_url = f'https://raw.githubusercontent.com/{username}/{repo}/{branch}/{frames_dir}/frame_{frame_number}.jpg'
        response = client.get(frame_url)
        response.raise_for_status()

        images_dir = Path.cwd() / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        frame_path = images_dir / f"frame_{frame_number}.jpg"
        frame_path.write_bytes(response.content)

        return frame_path

    except httpx.RequestError as e:
        print(f"Request error while downloading frame {frame_number} from episode {episode_number}: {e}")
    except httpx.HTTPStatusError as e:
        print(f"HTTP error while downloading frame {frame_number} from episode {episode_number}: "
              f"{e.response.status_code} - {e.response.text}")
    except Exception as e:
        print(f"Unexpected error: {e}")

    return None


def get_random_frame(configs: dict) -> tuple[int, int] | None:
    """
    Select a random frame from the episodes configuration.

    args:
        configs (dict): Configuration dictionary containing episode data.
    
    returns:
        tuple[int, int] | None: A tuple containing the random frame number and episode number.
        Returns None if no valid frame is found.
    """
    episodes: dict = configs.get("episodes", {})
    if not episodes:
        print("No episodes found in the configuration.")
        return None

    random_episode_key = random.choice(list(episodes.keys()))
    episode_data: dict = episodes.get(random_episode_key, {})
    number_of_frames = episode_data.get("number_of_frames", 0)

    if number_of_frames <= 0:
        print(f"No frames available in episode {random_episode_key}.")
        return None

    return random.randint(1, number_of_frames), int(random_episode_key)

   
def random_crop(frame_path: Path, configs: dict) -> tuple[Path, str] | None:
    """
    Returns a random crop of the frame.

    Args:
        frame_path: Path to the frame image.

    Returns:
        tuple[Path, str]: Tuple containing the path to the cropped image and the crop coordinates.
    """
    if not isinstance(frame_path, Path):
        print("frame_path must be a Path object")
        return None, None

    if not frame_path.is_file():
        print("frame_path must be a file")
        return None, None

    try:
        min_x: int = configs.get("posting", {}).get("random_crop", {}).get("min_x", 200)
        min_y: int = configs.get("posting", {}).get("random_crop", {}).get("min_y", 600)

        # Random crop dimensions. perfect square.
        crop_width = crop_height = random.randint(min_x, min_y)

        with Image.open(frame_path) as img:
            image_width, image_height = img.size

            if image_width < crop_width or image_height < crop_height:
                print(f"Image {frame_path} is too small for the crop size.")
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
                Path(__file__).parent.parent
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
        print(f"Failed to crop image: {str(e)}", exc_info=True)
        return None, None