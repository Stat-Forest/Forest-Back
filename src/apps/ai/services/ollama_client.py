import requests
from django.conf import settings


class OllamaClient:
    def __init__(self):
        self.base_url = settings.AI_BASE_URL
        self.model = settings.AI_MODEL
        self.timeout = settings.AI_TIMEOUT

    def generate(self, prompt: str) -> str:
        try:
            response = requests.post(
                f"{self.base_url}/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": settings.AI_TEMPERATURE,
                        "num_predict": settings.AI_MAX_TOKENS,
                        "num_ctx": settings.AI_NUM_CTX,
                        "top_p": settings.AI_TOP_P,
                    },
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()

        except requests.exceptions.RequestException as e:
            return "AI vaqtinchalik ishlamayapti. Keyinroq urinib ko‘ring."