from datetime import datetime, timedelta
from pathlib import Path
import re

import httpx
from langdetect import detect
from tenacity import retry, stop_after_attempt, wait_fixed

from src.logger import get_logger

logger = get_logger(__name__)

client = httpx.Client(
    timeout=httpx.Timeout(30, connect=10),
    headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'})


# Download subtitles from GitHub if they don't exist locally
# para bots que guardam os subs na pasta fb, do bot tipo (fearocanity / ebtrfio-template)
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def download_subtitles_if_needed(episode: int, configs: dict) -> None:
    """
    Download subtitles from GitHub if they don't exist locally.

    Args:
        episode (int): The episode number to download subtitles for.
        configs (dict): Configuration dictionary containing episode data.

    Returns:
        None: This function does not return anything.
    """
    subtitles_dir = Path.cwd() / "subtitles"
    episode_folder_subtitles = subtitles_dir / f"{episode:02d}"

    if not subtitles_dir.exists():
        subtitles_dir.mkdir(parents=True, exist_ok=True)

    if not episode_folder_subtitles.exists():
        episode_folder_subtitles.mkdir(parents=True, exist_ok=True)

    files = [f for f in episode_folder_subtitles.iterdir() if f.is_file() and f.suffix == ".ass"]

    if not files:
        github_data = configs.get("github", {})
        episode_data = configs.get("episodes", {}).get(episode, {})

        if not all([github_data.get("username"), github_data.get("repo"), episode_data.get("branch")]):
            logger.error("Error: Missing required configuration values.", exc_info=True)
            return None

        subtitle_url = (
            f'https://raw.githubusercontent.com/'
            f'{github_data["username"]}/{github_data["repo"]}/'
            f'{episode_data["branch"]}/fb/subtitle_en.ass'
        )

        try:
            response = client.get(subtitle_url)
            
            if not response.status_code == 200:
                logger.error(f"HTTP error while downloading subtitles for episode {episode}: "
                            f"{response.status_code} - {response.text}", exc_info=True)
                return None

            subtitle_file = episode_folder_subtitles / 'subtitle_en.ass'
            subtitle_file.write_bytes(response.content)
            return subtitle_file
        except httpx.RequestError as e:
            logger.error(f"Request error while downloading subtitles for episode {episode}: {e}", exc_info=True)
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error while downloading subtitles for episode {episode}: "
                  f"{e.response.status_code} - {e.response.text}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return None

    return None




LANGUAGE_CODES = {
    "en": "English",
    "pt": "Português",
    "es": "Español",
    "spa": "Español",
    "ja": "Japanese",
    "ko": "Korean",
    "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",
    "fr": "Français",
    "de": "Deutsch",
    "it": "Italiano",
    "ru": "Русский (Russian)",
    "tr": "Türkçe (Turkish)",
    "vi": "Tiếng Việt (Vietnamese)",
    "nl": "Nederlands (Dutch)",
    "uk": "Українська (Ukrainian)",
    "id": "Bahasa Indonesia (Indonesian)",
    "tl": "Tagalog (Filipino)",
    # add more language codes here
}



def remove_tags(message: str) -> str:
    """Remove ASS/SSA tags and control codes from a subtitle string."""
    # Ajusta a regex para capturar tags e comandos com mais robustez
    pattern = re.compile(r"\{\s*[^}]*\s*\}|\\N|\\[a-zA-Z]+\d*|\\c&H[0-9A-Fa-f]+&")
    # Substitui as tags e comandos por espaços
    message = pattern.sub(" ", message)
    # Remove múltiplos espaços
    return re.sub(r"\s+", " ", message).strip()

def timestamp_to_seconds(time_str: str) -> float:
    """Convert H:MM:SS.MS format to seconds"""
    try:
        h, m, s = time_str.split(":")
        s, ms = s.split(".")
        # Converte para float
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 100
    except ValueError:
        raise ValueError("Invalid time format. Expected HH:MM:SS.mmm.")

def frame_to_timestamp(img_fps: int | float, current_frame: int) -> str:
    """Convert frame number to timestamp.
    
    Args:
        img_fps (int | float): Frames per second of the video.
        current_frame (int): Current frame number.

    Returns:
        str | None: Timestamp in the format "HH:MM:SS.ms" or None if an error occurs.   
    """
    # Verifica se os tipos dos parâmetros são válidos
    if not isinstance(img_fps, (int, float)) or not isinstance(current_frame, int):
        logger.error("Error, img_fps or frame_number must be a number", exc_info=True)
        return None
    
    if img_fps <= 0 or current_frame < 0:
        return None  # FPS zero ou frame negativo não são válidos

    try:
        # Converte o número do frame para o timestamp
        frame_timestamp = datetime(1900, 1, 1) + timedelta(seconds=current_frame / img_fps)
        hr, min, sec, ms = (
            frame_timestamp.hour,
            frame_timestamp.minute,
            frame_timestamp.second,
            frame_timestamp.microsecond // 10000,
        )
        return f"{hr}:{min:02d}:{sec:02d}.{ms:02d}"
    except Exception as e:
        logger.error(f"Error calculating timestamp: {e}", exc_info=True)
        return None

def language_detect(file_path: Path, dialogues: list[str]) -> str:
    """Detects the language based on the dialogue content
      and renames the file with the detected lang code if it's not already in the file name.
    """
    if not file_path.exists():
        logger.error(f"Error: File not found: {file_path}", exc_info=True)
        return "Unknown"

    # Divide the file name into parts
    name_parts = file_path.stem.split(".")
    ext = file_path.suffix.lstrip(".")  # Remove the dot from the extension

    # If there is already a valid language code in the file name, use it
    if len(name_parts) > 1 and name_parts[-1] in LANGUAGE_CODES:
        return LANGUAGE_CODES.get(name_parts[-1], "Unknown")

    # Detects the language of the extracted text
    lang_code = detect(" ".join(dialogues))
    language = LANGUAGE_CODES.get(lang_code, "Unknown")

    if language == "Unknown":
        logger.error(f"Language detection failed. Keeping original filename ({__name__}).", exc_info=True)
        return language

    # Generates a new file path with the detected lang code
    new_file_path = file_path.with_name(
        f"{file_path.stem.split('.')[0]}.{lang_code}.{ext}"
    )

    try:
        if new_file_path.exists():
            return language

        file_path.rename(new_file_path)
        return language
    except Exception as e:
        logger.error(f"Error renaming file subtitle: {e}", exc_info=True)
        return "Unknown"

def subtitle_ass(subtitle_file: str, current_frame: int, current_episode: int, configs: dict) -> str | None:
    """
    Returns the subtitle message for the current frame.
    """

    img_fps = configs.get("episodes", {}).get(current_episode, {}).get("img_fps", 0)

    if not img_fps:
        logger.error("Error, img_fps not set, please define img_fps in the configs.yml file", exc_info=True)
        return None

    frame_in_seconds = timestamp_to_seconds(frame_to_timestamp(img_fps, current_frame))

    with open(subtitle_file, "r", encoding="utf-8_sig") as file:
        content = file.readlines()

    dialogues = [line for line in content if line.startswith("Dialogue:")]
    lang_name = language_detect(Path(subtitle_file), dialogues)
    subtitles = []

    for line in dialogues:
        parts = line.split(",")
        start_time_seconds = timestamp_to_seconds(parts[1])
        end_time_seconds = timestamp_to_seconds(parts[2])
        style = parts[3]  # Estilo (por exemplo, "Lyrics" ou "Signs")
        name = parts[4]  # Nome (opcional, usado em alguns casos)
        text = line.split(",,")[-1]  # O texto da legenda

        if start_time_seconds <= frame_in_seconds <= end_time_seconds:
            # Verifica se o estilo é relacionado a sinais (Signs)
            if re.match(r"(?i)^signs?", style) or re.match(r"(?i)^signs?", name):
                subtitle = f"【 {remove_tags(text)} 】"
                subtitles.append(subtitle + "\n")

            # Verifica se o estilo ou o nome é relacionado a letras de música (Lyrics ou Songs)
            elif re.search(r"(?i)lyrics?|songs?", style) or re.search(r"(?i)lyrics?|songs?", name):
                subtitle = f"♪ {remove_tags(text)} ♪\n"
                subtitles.append(subtitle)

            # Caso contrário, apenas adiciona o texto
            else:
                subtitle = remove_tags(text)
                subtitles.append(subtitle + "\n")
    if not subtitles:
        return None

    return f"[{lang_name}]\n {' '.join(subtitles)}"


def get_subtitle_message(current_frame: int, current_episode: int, configs: dict) -> str | None:
    """
    Returns the subtitle message for the current frame.
    """
    
    if not isinstance(current_frame, int) or not isinstance(current_episode, int):
        logger.error("Error, current_frame and current_episode must be integers", exc_info=True)
        return None

    subtitles_dir = Path.cwd() / "subtitles"
    subtitle_dir = subtitles_dir / f"{current_episode:02d}"

    if not subtitle_dir.exists():
        subtitle_dir.mkdir(parents=True, exist_ok=True)
        return None

    files = [f for f in subtitle_dir.iterdir() if f.is_file() and f.suffix == ".ass"]
    if not configs.get("posting", {}).get("multi_language_subtitles", False):
        files = [files[0]]

    if not files:
        logger.error(f"Subtitles active, but not found in directory {subtitle_dir}", exc_info=True)
        return None

    message = ""

    for file in files:
        subtitle_file = subtitle_dir / file

        result = subtitle_ass(subtitle_file, current_frame, current_episode, configs)
        if result:
            message += result + "\n\n"

    return "𝑺𝒖𝒃𝒕𝒊𝒕𝒍𝒆𝒔:\n" + message if message else None