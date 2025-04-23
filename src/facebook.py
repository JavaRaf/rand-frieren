import os
from pathlib import Path

import httpx
from tenacity import retry
from tenacity import (
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

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
                raise ValueError(
                    "The access token was not found \n"
                    "in the environment variables. Please set FB_TOKEN correctly in the GitHub secrets."
                )


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
                print("Resposta não contém JSON válido")
                return None

        print(f"Falha ao postar: {response.status_code} {response.text}")
        response.raise_for_status()  # Levanta exceção para ativar retry
        return None

    def post(
        self, message: str = "", frame_path: Path = None, parent_id: str = None
    ) -> str | None:
        """
        Posta uma mensagem no Facebook.
        Se todas as tentativas falharem, apenas loga o erro e retorna None.
        """
        endpoint = (
            f"{self.base_url}/{parent_id}/comments"
            if parent_id
            else f"{self.base_url}/me/photos"
        )
        params = {"access_token": self.access_token, "message": message}
        files = None

        if frame_path:
            with open(frame_path, "rb") as file:
                files = {"source": file}
                try:
                    return self._try_post(endpoint, params, files)
                except RetryError:
                   print("Falha ao postar após múltiplas tentativas.")
                   return None
        else:
            try:
                return self._try_post(endpoint, params)
            except RetryError:
                print("Falha ao postar após múltiplas tentativas.")
                return None


        
        
        