# Standard library imports
from pathlib import Path
from time import sleep
from typing import Optional

# Local imports
from src.filters import select_filter, apply_filter
from src.facebook import FacebookAPI
from src.logger import get_logger
from src.frames_util import (
    download_frame,
    get_random_frame
)
from src.load_configs import load_configs
from src.poster import post_frame, post_random_crop, post_subtitles
from src.subtitle import (
    download_subtitles_if_needed,
    frame_to_timestamp,
    get_subtitle_message
)
from src.request_by import main_request_by_process

fb = FacebookAPI()
logger = get_logger(__name__)




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
                "total_frames_in_this_episode1": configs.get("episodes").get(frame_data[0].get("episode")).get("number_of_frames"),
                "episode2": frame_data[1].get("episode"),
                "total_frames_in_this_episode2": configs.get("episodes").get(frame_data[1].get("episode")).get("number_of_frames"),
                "frame1": frame_data[0].get("frame"),
                "frame2": frame_data[1].get("frame"),
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
            f'( {frame_data[0].get("episode")}, {frame_data[1].get("episode")} )',
            "Frames:",
            f'( {frame_data[0].get("frame")}, {frame_data[1].get("frame")} )',
            "out of",
            f'( {configs.get("episodes").get(frame_data[0].get("episode")).get("number_of_frames")}, {configs.get("episodes").get(frame_data[1].get("episode")).get("number_of_frames")} )',
            flush=True
        )

        post_id = post_frame(message, frame_data[0].get('output_path'))
        if not post_id:
            logger.error("✖ Failed to post frame data (main)")
            return None
        
        post_subtitles(post_id, frame_data[0].get('frame'), frame_data[0].get('episode'), frame_data[0].get('subtitle'), configs)
        post_subtitles(post_id, frame_data[1].get('frame'), frame_data[1].get('episode'), frame_data[1].get('subtitle'), configs)
        post_random_crop(post_id, frame_data[0].get('output_path'), configs)
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
                "total_frames_in_this_episode": configs.get("episodes").get(frame_data.get("episode")).get("number_of_frames"),
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
            f"├── Posting {frame_data.get('filter_func')}, Episode:",
            f'{frame_data.get("episode")}',
            "Frame:",
            f'{frame_data.get("frame")}',
            "out of",
            f'{configs.get("episodes").get(frame_data.get("episode")).get("number_of_frames")}',
            flush=True
        )

        post_id = post_frame(message, frame_data.get('output_path'))
        if not post_id:
            logger.error("✖ Failed to post frame data")
            return None
        
        post_subtitles(post_id, frame_data.get('frame'), frame_data.get('episode'), frame_data.get('subtitle'), configs)
        post_random_crop(post_id, frame_data.get('output_path'), configs)
        return post_id

def process_frame(CONFIGS, filter_func) -> Optional[dict]:
    """
    Process a random frame and apply the selected filter.
    Returns a dictionary with frame data.
    """

    frame_number, episode_number = get_random_frame(CONFIGS)
    if not episode_number or not frame_number:
        logger.error("Error: No valid frame found.")
        return None

    frame_path = download_frame(CONFIGS, frame_number, episode_number)
    if not frame_path:
        logger.error(f"Error: Frame {frame_number} from episode {episode_number} not found.")
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

    main_request_by_process() # request by process (post frames by recommendations of users)

    print('\n' + '-' * 50 + '\n' + '-' * 50,  flush=True) # makes visualization better in CI/CD environments

    configs = load_configs()
    season = int(configs.get("season", 0))
    posting_interval = configs.get("posting", {}).get("posting_interval", 2)
    fph = configs.get("posting", {}).get("fph", 15)

    for _ in range(1, fph + 1):
        filter_func = select_filter(configs)
        if not filter_func:
            logger.error(f"✖ No filter selected or filter is not callable")
            continue

        try:
            if filter_func.__name__ == 'two_panels':
                framedata = process_two_panels(configs, filter_func)
                if not framedata:
                    logger.error(f"✖ Error processing frames for two_panels")
                    sleep(10)
                    continue
                
                output_path = apply_filter(filter_func, framedata)
                if not output_path:
                    logger.error(f"✖ Error generating output_path for two_panels") 
                    sleep(10)
                    continue

                framedata[0]['output_path'] = output_path
                post_frame_data(season, framedata, configs)

            else:
                data = process_frame(configs, filter_func)
                if not data:
                    logger.error(f"✖ Error processing frame")
                    sleep(10)
                    continue

                output_path = apply_filter(filter_func, [data])
                if not output_path:
                    logger.error(f"✖ Error generating output_path for single frame")
                    sleep(10)
                    continue
                    
                data['output_path'] = output_path
                post_frame_data(season, data, configs)

        

        except (IndexError, KeyError, Exception) as e:
            logger.error(f"✖ Error processing frame: {str(e)}")
            sleep(10)
            continue
        
        

        print('\n' + '-' * 50 + '\n' + '-' * 50,  flush=True) # makes visualization better in CI/CD environments
        sleep(posting_interval * 60) # 2 minutes

        


if __name__ == "__main__":
    main()
    # Run the main function