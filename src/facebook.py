import os
from pathlib import Path
import re
from typing import List

import httpx
from src.frames_util import timestamp_to_frame
from tenacity import retry
from tenacity import (
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.logger import get_logger

logger = get_logger(__name__)

# Carrega as variáveis de ambiente do arquivo .env
# O parâmetro override=False garante que as variáveis de ambiente não sejam sobrescritas
#  se já estiverem definidas no ambiente do sistema operacional



# Define a classe FacebookAPI para interagir com a API do Facebook
# A classe é inicializada com a versão da API e o token de acesso


class FacebookAPI:
    def __init__(self, version: str = "v21.0"):
        self.base_url = f"https://graph.facebook.com/{version}/"
        self.access_token = os.getenv("FB_TOKEN", None)
        self.client = httpx.Client(base_url=self.base_url, timeout=httpx.Timeout(30, connect=10))

    # Verifica se o token de acesso foi definido
    # Se não estiver definido, levanta um erro
    if not os.getenv("FB_TOKEN"):
        logger.error("FB_TOKEN not defined")
        raise ValueError("FB_TOKEN not defined")

    @retry(
        stop=stop_after_attempt(3),  # Máximo de 3 tentativas
        wait=wait_exponential(
            multiplier=1, min=2, max=10
        ),  # Tempo de espera exponencial
        retry=retry_if_exception_type(
            httpx.HTTPError
        ),  # Só tenta novamente se for erro HTTP
        reraise=True,  # Lança exceção se todas as tentativas falharem
    )
    def _try_post(self, endpoint: str, params: dict, files: dict = None) -> str | None:
        response = self.client.post(endpoint, params=params, files=files)

        if response.status_code == 200:
            try:
                return response.json().get("id")
            except ValueError:
                logger.error('Error: Response does not contain valid JSON', exc_info=True)
                return None
        
        response.raise_for_status()  # Levanta exceção para ativar retry
        return None

    def post(self, message: str = "", frame_path: Path = None, parent_id: str = None) -> str | None:
        """
        Posts a message to Facebook.
        If all attempts fail, only logs the error and returns None.
        """
        endpoint = (
            f"{self.base_url}/{parent_id}/comments"
            if parent_id
            else f"{self.base_url}/me/photos"
        )
        params = {"access_token": self.access_token, "message": message}
        files = None


        if not frame_path:
            try:
                return self._try_post(endpoint, params)
            except RetryError:
                logger.error("Failed to post after multiple attempts", exc_info=True)
                return None
        
        with open(frame_path, "rb") as file:
            files = {"source": file}
            try:
                return self._try_post(endpoint, params, files)
            except RetryError:
                logger.error("Failed to post after multiple attempts", exc_info=True)
                return None

    # recommendations functions
    def get_posts(self, attempts: int = 6) -> List[dict]:
        """
        Fetch posts from Facebook API with pagination support.
        
        Args:
            attempts: Number of pagination attempts to make
            
        Returns:
            List of post data dictionaries
        """
        params = {
            'fields': 'message,comments.limit(100)',
            'limit': '100',
            'access_token': self.access_token
        }

        data_posts = []
        endpoint = "me/posts"

        for attempt in range(attempts):
            try:
                response = self.client.get(endpoint, params=params)
                data = response.json()
                data_posts.extend(data.get('data', []))

                # update endpoint and reset params after first request
                next_page = data.get('paging', {}).get('next')
                if next_page:
                    endpoint = next_page
                    params = {}  # avoid sending duplicate params
                else:
                    break  # exit loop if no more data
            except Exception as e:
                logger.error(f"Tentativa {attempt + 1} falhou: {str(e)}")
        return data_posts

    def extract_comments(self, data_posts: List[dict]) -> List[str]:
        """
        Extract all comments from posts data.
        
        Args:
            data_posts: List of post data dictionaries
            
        Returns:
            List of comment messages
        """
        comments = []
        for post in data_posts:
            comments_data = post.get('comments', {}).get('data', [])
            comments.extend(comment.get('message', '') for comment in comments_data if comment.get('message'))
        return comments

    def parse_frame_recommendations(self, comments: List[str]) -> List[dict]:
        """
        Parse comments to extract frame recommendations.
        
        Args:
            comments: List of comment messages
            
        Returns:
            List of frame recommendation dictionaries
        """
        frames = []
        for comment in comments:
            try:
                if not comment.startswith('!'):
                    continue

                parts = comment.split(",")
                if len(parts) < 2:
                    logger.warning(f"Comment has insufficient parts: {comment}")
                    continue
                episode = parts[0]
                value = parts[1]

                if len(parts) > 2:
                    user_name = parts[2]
                    if len(user_name) > 150:
                        user_name = user_name[:150].strip()
                else:
                    user_name = 'unknown'

                if not episode or not value:
                    logger.warning(f"Invalid comment format: {comment}")
                    continue

                episode_num = int(re.search(r'\d+', episode).group(0))

                if re.search(r'\d{1,2}:\d{2}:\d{2}\.\d{2}', value):
                    frame = timestamp_to_frame(re.search(r'\d{1,2}:\d{2}:\d{2}\.\d{2}', value).group(0))
                else:
                    frame = int(re.search(r'\d+', value).group(0))

                frames.append({
                    "episode": episode_num,
                    "frame": frame,
                    "user_name": user_name,
                    "seen": False
                })

            except Exception as e:
                logger.error(f"Error parsing comment: {e}", exc_info=True)
                continue

        return frames
    



