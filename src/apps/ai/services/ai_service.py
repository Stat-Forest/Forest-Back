import time
from .ollama_client import OllamaClient
from .prompt_builder import build_prompt
from .domain_filter import classify_question, detect_language


class AIService:
    def __init__(self):
        self.client = OllamaClient()

    def ask(self, question: str) -> dict:
        return self.handle_ai_request(question)

    def handle_ai_request(self, question: str) -> dict:
        start_time = time.time()

        category = classify_question(question)
        language = detect_language(question)

        # GREETING
        if category == "greeting":
            if language == "ru":
                return {
                    "answer": "Здравствуйте! Я помогаю по системе Stat-Urmon. Задайте вопрос о создании отчетов или итогах."
                }
            return {
                "answer": "Salom! Men Stat-Urmon tizimi bo‘yicha yordam beraman. Hisobot yoki reja haqida savol bersangiz, tushuntirib beraman."
            }

        # META
        if category == "meta":
            if language == "ru":
                return {
                    "answer": "Я помогаю по системе Stat-Urmon: создание отчетов, разница между планом и фактом, региональные и республиканские итоги."
                }
            return {
                "answer": "Men Stat-Urmon tizimi bo‘yicha yordam beraman: hisobot yaratish, reja va amalda farqi, viloyat va respublika jami haqida."
            }

        # OFF-TOPIC
        if category == "off_topic":
            if language == "ru":
                return {
                    "message_response": "Пожалуйста, задавайте вопросы только по системе Stat-Urmon."
                }
            return {
                "message_response": "Iltimos, faqat Stat-Urmon tizimiga oid savol bering."
            }

        # DOMAIN → LLM
        prompt = build_prompt(question)
        answer = self.client.generate(prompt)

        response_time = int((time.time() - start_time) * 1000)

        return {
            "answer": answer.strip(),
            "response_time_ms": response_time,
        }