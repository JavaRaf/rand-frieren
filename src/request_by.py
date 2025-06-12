from src.frames_util import download_frame, frame_to_timestamp
from src.poster import post_frame, post_random_crop, post_subtitles
from src.facebook import FacebookAPI
from src.logger import get_logger
from src.recommendations import (
    add_recommendations,
    load_recommendations,
    set_execute_state,
    get_unseen_recommendations,
    mark_recommendation_as_seen
)
from src.load_configs import load_configs
from pathlib import Path
from typing import Optional
from src.subtitle import get_subtitle_message


fb = FacebookAPI()
CONFIGS = load_configs()

logger = get_logger(__name__)



def process_new_recommendations():
    """
    Process new recommendations from Facebook and add them to the JSON file.
    """
    try:
        # Busca e processa as recomendações
        posts = fb.get_posts()
        comments = fb.extract_comments(posts)
        new_recommendations = fb.parse_frame_recommendations(comments)
        
        # Adiciona as novas recomendações ao JSON
        add_recommendations(new_recommendations)
        
    except Exception as e:
        logger.error(f"Error processing recommendations: {e}")

def get_next_recommendation() -> list[dict]:
    """
    Get the next unseen recommendation.
    
    Returns:
        list[dict]: List of unseen recommendations
    """
    return get_unseen_recommendations()


def process_recommendation(recommendation: dict):
    """
    Process a recommendation.
    """
    frame_number, episode_number = recommendation.get("frame"), recommendation.get("episode")
    frame_path = download_frame(CONFIGS, frame_number, episode_number)
    if not frame_path:
        logger.error(f"Error: Frame {frame_number} from episode {episode_number} not found.")
        return None
    
    subtitle = get_subtitle_message(frame_number, episode_number, CONFIGS)
    timestamp = frame_to_timestamp(CONFIGS.get("episodes").get(episode_number).get("img_fps"), frame_number)

    return {
        "frame_path": frame_path,
        "episode": episode_number,
        "frame": frame_number,
        "user_name": recommendation.get("user_name"),
        "subtitle": subtitle,
        "timestamp": timestamp,
    }



def post_frame_by_recommendation(season: int, frame_data: dict, configs: dict) -> Optional[str]:
    """
    Post a frame by recommendation.
    """
    message: str = configs.get("msg_recommendation")
    if not message:
        logger.error("✖ Failed to get message template from configs")
        return None
    
    try:
        format_dict = {
            "season": season,
            "episode": frame_data.get("episode"),
            "frame": frame_data.get("frame"),
            "timestamp": frame_data.get("timestamp"),
            "filter_func": frame_data.get("filter_func"),
            "user_name": frame_data.get("user_name")
        }
        required_keys = [key for key in format_dict.keys() if "{" + key + "}" in message]
        present_keys = {k: format_dict[k] for k in required_keys}
        message = message.format(**present_keys)


        print(
            "\n\n"
            "├── Posting frame by recommendation, Episode:",
            f'( {frame_data.get("episode")} )',
            "Frame:",
            f'( {frame_data.get("frame")} )',
            "User:",
            f'( {frame_data.get("user_name")} )',
            flush=True
        )

        post_id = post_frame(message, frame_data.get("frame_path"))
        if not post_id:
            logger.error("Failed to post frame")
            return None
        
        mark_recommendation_as_seen(frame_data.get("episode"), frame_data.get("frame"))

        frame_path = frame_data.get("frame_path")
        frame_number = frame_data.get("frame")
        episode_number = frame_data.get("episode")
        subtitle = frame_data.get("subtitle")

        post_subtitles(post_id, frame_number, episode_number, subtitle, configs)
        post_random_crop(post_id, frame_path, configs)

        return post_id
    
    except Exception as e:
        logger.error(f"Error posting frame by recommendation: {e}")
        return None

def main_request_by_process():
    process_new_recommendations()
    unseen_recommendations = get_next_recommendation()

    if not unseen_recommendations:
        logger.info("No unseen recommendations found")
        return

    execute = load_recommendations()["execute"]
    logger.info(f"Recommendations are{' not' if not execute else ''} being processed")
    set_execute_state(not execute)
    if not execute:
        return
    

    for recommendation in unseen_recommendations:
        season = int(CONFIGS.get("season", 0))
        frame_data = process_recommendation(recommendation)
        post_id = post_frame_by_recommendation(season, frame_data, CONFIGS)
        if not post_id:
            logger.error("Failed to post frame by recommendation")
            continue
        
        mark_recommendation_as_seen(recommendation.get("episode"), recommendation.get("frame"))

    








