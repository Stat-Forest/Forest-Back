import logging
from typing import List

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class OllamaEmbeddingClient:
    def __init__(self) -> None:
        self.base_url = settings.AI_BASE_URL.rstrip("/")
        self.model = settings.AI_EMBED_MODEL
        self.timeout = getattr(settings, "AI_TIMEOUT", 30)
        self.session = requests.Session()

    def embed(self, text: str) -> List[float]:
        cleaned_text = (text or "").strip()
        if not cleaned_text:
            return []

        try:
            response = self.session.post(
                f"{self.base_url}/embed",
                json={
                    "model": self.model,
                    "input": cleaned_text,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()
            embeddings = data.get("embeddings") or []

            if not embeddings:
                logger.warning("Ollama embed returned empty embeddings.")
                return []

            first = embeddings[0]
            if not isinstance(first, list):
                logger.warning("Ollama embed returned invalid embedding format.")
                return []

            return first

        except requests.exceptions.Timeout:
            logger.exception("Ollama embedding timeout after %ss", self.timeout)
            return []
        except requests.exceptions.ConnectionError:
            logger.exception("Ollama embedding connection error")
            return []
        except requests.exceptions.RequestException:
            logger.exception("Ollama embedding request failed")
            return []
        except Exception:
            logger.exception("Unexpected embedding error")
            return []