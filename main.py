# Standard library imports
from pathlib import Path
from time import sleep
from typing import Optional

# Local imports
from src.filters import select_filter
from src.facebook import FacebookAPI
from src.logger import get_logger
from src.frames_util import (
    download_frame,
    get_random_frame,
    random_crop
)
from src.load_configs import load_configs
from src.subtitle import (
    download_subtitles_if_needed,
    frame_to_timestamp,
    get_subtitle_message
)

fb = FacebookAPI()
logger = get_logger(__name__)


def post_frame(message: str, frame_path: Path) -> Optional[str]:
    """Posta um frame e retorna o ID do post."""
    try:
        post_id = fb.post(message, frame_path)
        if post_id:
            print("├── Frame has been posted", flush=True)
            sleep(2)
        else:
            print("✖ Failed to post frame (main, post_frame)")
        return post_id
    except Exception as e:
        print(f"✖ Error posting frame: {e}")
        return None


def post_subtitles(post_id: str, frame_number: int, episode: int, subtitle: str, configs: dict) -> Optional[str]:
    """Posta as legendas associadas ao frame."""
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
            print("✖ Failed to post subtitle (main, post_subtitles)")
        return subtitle_post_id
    except Exception as e:
        print(f"✖ Error posting subtitle: {e}")
        return None


def post_random_crop(post_id: str, frame_path: Path, configs: dict) -> Optional[str]:
    """Posta uma versão recortada do frame aleatório."""
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
                print("✖ Failed to post random crop (main, post_random_crop)")
            return crop_post_id
    except Exception as e:
        print(f"✖ Error posting random crop: {e}")

    return None


# agrupa as funcoes de postagem
def post_frame_data(season, frame_data: dict, configs: dict) -> Optional[str]:
    """
    Posta um frame com base em seus dados.

    Args:
        season (str): A temporada do anime em que o frame se encontra.
        frame_data (dict or list): Um dicionário contendo as informações do frame que será postado.
            Caso seja um dicionário, as chaves devem ser "episode", "path" e "timestamp".
            Caso seja uma lista, é esperado que contenha dois dicionários com as mesmas chaves,
            representando dois frames que serão postados lado a lado.
        configs (dict): O dicionário de configurações.

    Returns:
        str: O ID do post criado, ou None se falhar.
    """


    if isinstance(frame_data, list) and len(frame_data) == 2: # frame pode ser um uma lista ou um dicionário por isso essa checagem
        message: str = configs.get("msg_two_panels")
        if not message:
            logger.error("✖ Failed to get message template from configs")
            return None
            
        try:
            # Create a dictionary with all possible values
            format_dict = {
                "season": season,
                "episode1": frame_data[0].get("episode"),
                "episode2": frame_data[1].get("episode"),
                "timestamp1": frame_data[0].get("timestamp"),
                "timestamp2": frame_data[1].get("timestamp"),
                "filter_func": frame_data[0].get("filter_func")
            }
            
            # Get only the keys that exist in the message template
            required_keys = [key for key in format_dict.keys() if "{" + key + "}" in message]
            present_keys = {k: format_dict[k] for k in required_keys}
            
            message = message.format(**present_keys)
        except KeyError as e:
            logger.error(f"✖ Missing required field in frame_data: {e}")
            return None
        except Exception as e:
            logger.error(f"✖ Error formatting message: {e}")
            return None

        print(
            "\n\n"
            "├── Posting two panels, Episodes:",
            f'( {frame_data[0]["episode"]}, {frame_data[1]["episode"]} )',
            "Frames:",
            f'( {frame_data[0]["frame"]}, {frame_data[1]["frame"]} )',
            flush=True
        )

        post_id = post_frame(message, frame_data[0]['output_path'])
        if not post_id:
            logger.error("✖ Failed to post frame data (main)")
            return None
        
        post_subtitles(post_id, frame_data[0]['frame'], frame_data[0]['episode'], frame_data[0]['subtitle'], configs)
        post_subtitles(post_id, frame_data[1]['frame'], frame_data[1]['episode'], frame_data[1]['subtitle'], configs)
        post_random_crop(post_id, frame_data[0]['output_path'], configs)
        return post_id

    else:
        message: str = configs.get("msg_single_frame")
        if not message:
            logger.error("✖ Failed to get message template from configs")
            return None
            
        try:
            # Create a dictionary with all possible values
            format_dict = {
                "season": season,
                "episode": frame_data.get("episode"),
                "frame": frame_data.get("frame"),
                "timestamp": frame_data.get("timestamp"),
                "filter_func": frame_data.get("filter_func")
            }
            
            # Get only the keys that exist in the message template
            required_keys = [key for key in format_dict.keys() if "{" + key + "}" in message]
            present_keys = {k: format_dict[k] for k in required_keys}
            
            message = message.format(**present_keys)
        except KeyError as e:
            logger.error(f"✖ Missing required field in frame_data: {e}")
            return None
        except Exception as e:
            logger.error(f"✖ Error formatting message: {e}")
            return None

        print(
            "\n\n"
            f"├── Posting {frame_data['filter_func']}, Episode:",
            f'{frame_data["episode"]}',
            "Frame:",
            f'{frame_data["frame"]}',
            flush=True
        )

        post_id = post_frame(message, frame_data['output_path'])
        if not post_id:
            logger.error("✖ Failed to post frame data")
            return None
        
        post_subtitles(post_id, frame_data['frame'], frame_data['episode'], frame_data['subtitle'], configs)
        post_random_crop(post_id, frame_data['output_path'], configs)
        return post_id

def aplie_filter(filter_func, Framedata: list[dict]) -> Optional[Path]:
    """Aplica um filtro ao frame e retorna o caminho do frame filtrado."""

    if not isinstance(Framedata, list) or not all(isinstance(item, dict) for item in Framedata):
        print("✖ Invalid Framedata format")
        return None

    if len(Framedata) == 2 and all('frame_path' in item for item in Framedata):
        try:
            output_path = filter_func(Framedata[0]['frame_path'], Framedata[1]['frame_path'])
            if output_path:
                return output_path
            else:
                print("✖ Failed to apply filter")
        except Exception as e:
            print(f"✖ Error applying filter: {e}")
            return None

    if len(Framedata) == 1 and 'frame_path' in Framedata[0]:
        try:
            output_path = filter_func(Framedata[0]['frame_path'])
            if output_path:
                return output_path
            else:
                print("✖ Failed to apply filter")
        except Exception as e:
            print(f"✖ Error applying filter: {e}")
            return None

    print("✖ Invalid Framedata structure or missing keys")
    return None

def process_frame(CONFIGS, filter_func) -> Optional[dict]:
    """
    Process a random frame and apply the selected filter.
    Returns a dictionary with frame data.
    """

    frame_number, episode_number = get_random_frame(CONFIGS)
    if not episode_number or not frame_number:
        print("Error: No valid frame found.")
        return None

    frame_path = download_frame(CONFIGS, frame_number, episode_number)
    if not frame_path:
        print(f"Error: Frame {frame_number} from episode {episode_number} not found.")
        return None

    download_subtitles_if_needed(episode_number, CONFIGS)
    subtitle = get_subtitle_message(frame_number, episode_number, CONFIGS)
    timestamp = frame_to_timestamp(CONFIGS.get("episodes").get(episode_number).get("img_fps"), frame_number)

    return {
        "frame_path": frame_path,
        "episode": episode_number,
        "frame": frame_number,
        "subtitle": subtitle,
        "timestamp": timestamp,
        "filter_func": filter_func.__name__
    }

def process_two_panels(CONFIGS, filter_func) -> list[dict]:
    framedata = []
    for _ in range(2):
        data = process_frame(CONFIGS, filter_func)
        if data:
            framedata.append(data)
    return framedata


def main():
    """
    Main function of the program. It posts frames from anime to Facebook pages.
    
    The function reads the configuration file, selects a random frame from the episodes,
    applies a random filter to the frame, and posts the frame to the specified Facebook
    pages. The function also handles posting subtitles and random crops of the frame.

    The function repeats the process indefinitely, with a configurable posting interval.
    """

    print('\n' + '-' * 50 + '\n' + '-' * 50,  flush=True) # makes visualization better in CI/CD environments

    configs = load_configs()
    season = int(configs.get("season", 0))
    posting_interval = configs.get("posting", {}).get("posting_interval", 2)
    fph = configs.get("posting", {}).get("fph", 15)

    for _ in range(1, fph + 1):
        filter_func = select_filter(configs)
        if not filter_func:
            print(f"✖ No filter selected or filter is not callable ({__name__})")
            continue

        try:
            if filter_func.__name__ == 'two_panels':
                framedata = process_two_panels(configs, filter_func)
                if not framedata:
                    print(f"✖ Error processing frames for two_panels ({__name__})")
                    sleep(10)
                    continue
                
                output_path = aplie_filter(filter_func, framedata)
                if not output_path:
                    print(f"✖ Error generating output_path for two_panels ({__name__})") 
                    sleep(10)
                    continue

                framedata[0]['output_path'] = output_path
                post_frame_data(season, framedata, configs)

            else:
                data = process_frame(configs, filter_func)
                if not data:
                    print(f"✖ Error processing frame ({__name__})")
                    sleep(10)
                    continue

                output_path = aplie_filter(filter_func, [data])
                if not output_path:
                    print(f"✖ Error generating output_path for single frame ({__name__})")
                    sleep(10)
                    continue
                    
                data['output_path'] = output_path
                post_frame_data(season, data, configs)

        except (IndexError, KeyError, Exception) as e:
            print(f"✖ Error processing frame ({__name__}): {str(e)}")
            sleep(10)
            continue

        print('\n' + '-' * 50 + '\n' + '-' * 50,  flush=True) # makes visualization better in CI/CD environments
        sleep(posting_interval * 60) # 2 minutes

        


if __name__ == "__main__":
    main()
    # Run the main function