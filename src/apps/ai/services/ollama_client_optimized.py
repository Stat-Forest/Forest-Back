import logging
from typing import Any, Dict, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """
    Stable synchronous Ollama client.

    Notes:
    - requests.Session() reuses TCP connections
    - timeout and model options are driven from Django settings
    - generate() returns plain text for compatibility with current service layer
    """

    def __init__(self) -> None:
        self.base_url: str = settings.AI_BASE_URL.rstrip("/")
        self.model: str = settings.AI_MODEL
        self.timeout: int = getattr(settings, "AI_TIMEOUT", 30)
        self.session = requests.Session()

        self.default_options: Dict[str, Any] = {
            "temperature": getattr(settings, "AI_TEMPERATURE", 0.05),
            "num_predict": getattr(settings, "AI_MAX_TOKENS", 160),
            "num_ctx": getattr(settings, "AI_NUM_CTX", 1024),
            "top_p": getattr(settings, "AI_TOP_P", 0.8),
            "repeat_penalty": getattr(settings, "AI_REPEAT_PENALTY", 1.1),
            "use_mmap": True,
            "use_mlock": False,
            "keep_alive": getattr(settings, "AI_KEEP_ALIVE", "10m"),
        }

    def _build_payload(self, prompt: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": self.default_options.copy(),
        }
        if options:
            payload["options"].update(options)
        return payload

    def generate(self, prompt: str, options: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate response text from Ollama.
        Returns user-safe fallback text when upstream fails.
        """
        try:
            response = self.session.post(
                f"{self.base_url}/generate",
                json=self._build_payload(prompt, options=options),
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()
            text = (data.get("response") or "").strip()

            if not text:
                logger.warning("Ollama returned empty response. payload_model=%s", self.model)
                return "Kechirasiz, AI javob qaytara olmadi."

            return text

        except requests.exceptions.Timeout:
            logger.exception("Ollama request timed out after %ss", self.timeout)
            return "AI javob berishda sekinlik kuzatildi. Iltimos, qaytadan urinib ko'ring."

        except requests.exceptions.ConnectionError:
            logger.exception("Ollama connection error")
            return "AI xizmatiga ulanib bo'lmadi. Iltimos, keyinroq urinib ko'ring."

        except requests.exceptions.RequestException:
            logger.exception("Ollama request failed")
            return "AI xizmatida vaqtinchalik xatolik yuz berdi."

        except Exception:
            logger.exception("Unexpected Ollama client error")
            return "AI xizmatida kutilmagan xatolik yuz berdi."