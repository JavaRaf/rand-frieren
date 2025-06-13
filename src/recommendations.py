import json
from pathlib import Path
from typing import List, Dict
from src.logger import get_logger

logger = get_logger(__name__)

RECOMMENDATIONS_PATH = Path.cwd() / 'logs' / 'recommendations.json'
RECOMMENDATIONS_PATH.parent.mkdir(exist_ok=True)

DEFAULT_STRUCTURE = {
    "execute": False,  # Estado de processamento
    "recommendations": []    # Lista de recomendações
}

if not RECOMMENDATIONS_PATH.exists():
    with open(RECOMMENDATIONS_PATH, 'w', encoding='utf-8') as file:
        json.dump(DEFAULT_STRUCTURE, file, indent=2, ensure_ascii=False)

def load_recommendations() -> Dict:
    """
    Load recommendations from JSON file.
    
    Returns:
        Dict: Dictionary containing processing state and recommendations list.
        Returns default structure if file not found.
    """
    try:
        with open(RECOMMENDATIONS_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        logger.warning(f"Recommendations file not found at {RECOMMENDATIONS_PATH}")
        return DEFAULT_STRUCTURE.copy()
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in recommendations file at{RECOMMENDATIONS_PATH}")
        return DEFAULT_STRUCTURE.copy()

def save_recommendations(data: Dict) -> None:
    """
    Save recommendations to JSON file.
    
    Args:
        data (Dict): Dictionary containing processing state and recommendations list
    """
    try:
        with open(RECOMMENDATIONS_PATH, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving recommendations: {e}")

def add_recommendations(new_recommendations: List[Dict]) -> None:
    """
    Add new recommendations to the JSON file.
    
    Args:
        new_recommendations (List[Dict]): List of new recommendations to add
    """
    if not new_recommendations:
        return
    
    data = load_recommendations()
    for new_recommendation in new_recommendations:
        is_duplicate = any(
            rec["episode"] == new_recommendation["episode"] and 
            rec["frame"] == new_recommendation["frame"] 
            for rec in data["recommendations"]
        )
        if not is_duplicate:
            data["recommendations"].append(new_recommendation)

    save_recommendations(data)

def clear_recommendations(max_recommendations: int = 100) -> None:
    """
    Clear recommendations from the JSON file.
    """
    data = load_recommendations()
    if len(data["recommendations"]) > max_recommendations:
        data["recommendations"] = data["recommendations"][-max_recommendations:]
    save_recommendations(data)

# mudar de true para false para rodar o processamento
def set_execute_state(value: bool) -> None:
    """
    Update the processing state in the JSON file.
    
    Args:
        is_processing (bool): New processing state
    """
    data = load_recommendations()
    data["execute"] = value
    save_recommendations(data)

def get_unseen_recommendations() -> List[Dict]:
    """
    Get all unseen recommendations from the saved recommendations file.
    
    Returns:
        List[Dict]: List of unseen recommendations
    """
    data = load_recommendations()
    return [rec for rec in data["recommendations"] if not rec.get("seen", False)]

def mark_recommendation_as_seen(episode: int, frame: int) -> None:
    """
    Mark a specific recommendation as seen.
    
    Args:
        episode (int): Episode number
        frame (int): Frame number
    """
    data = load_recommendations()
    for rec in data["recommendations"]:
        if rec["episode"] == episode and rec["frame"] == frame:
            rec["seen"] = True
            break
    save_recommendations(data) 