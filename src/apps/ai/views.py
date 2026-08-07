from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema

from apps.ai.serializers.ai_serializer import AIRequestSerializer
from apps.ai.services.ai_service_optimized import AIService
from apps.ai.services.throttle import AIDailyThrottle


class AIChatView(APIView):
    permission_classes = [IsAuthenticated]
    # throttle_classes = [AIDailyThrottle]

    @extend_schema(
        tags=["AI"],
        summary="Stat-Urmon AI yordamchiga savol yuborish",
        description="""
Bu endpoint Stat-Urmon ERP tizimidagi AI yordamchiga savol yuborish uchun ishlatiladi.

### Frontend uchun juda oddiy tushuntirish:
Frontend bu endpointga foydalanuvchi yozgan savolni `question` maydoni ichida yuboradi.  
AI shu savolga javob beradi va natijani JSON ko‘rinishida qaytaradi.

### Qanday ishlaydi:
1. Foydalanuvchi savol yozadi.
2. Frontend savolni backendga yuboradi.
3. Backend AI knowledge bazadan kerakli ma'lumotlarni topadi.
4. AI javobni qaytaradi.

### Muhim:
- `question` maydoni majburiy.
- Savol oddiy user tilida bo'lishi mumkin.
- Savol o'zbekcha yoki ruscha bo'lishi mumkin.
- Javobda faqat `answer` emas, qo'shimcha texnik maydonlar ham qaytadi:
  - `response_time_ms`
  - `llm_time_ms`
  - `rag_time_ms`
  - `routing_type`
  - `context_used`
  - `quality_score`

### Frontchi uchun tavsiya:
UI'da faqat `answer` ni asosiy matn sifatida ko'rsatish mumkin.
Qolgan maydonlar debugging yoki monitoring uchun ishlatiladi.

### Misol savollar:
- `Muddatni kim yaratadi?`
- `Hisobot qabul qilinsa keyin nima bo'ladi?`
- `Viloyat jamini kim yaratadi?`
- `E-IMZO qaysi jarayonlarda ishlatiladi?`
""",
        request=AIRequestSerializer,
        responses={
            200: OpenApiResponse(
                description="AI javobi muvaffaqiyatli qaytdi.",
                response={
                    "type": "object",
                    "properties": {
                        "answer": {"type": "string", "example": "Muddatni odatda Super Admin yaratadi."},
                        "response_time_ms": {"type": "integer", "example": 145},
                        "llm_time_ms": {"type": "integer", "example": 0},
                        "rag_time_ms": {"type": "integer", "example": 141},
                        "cache_hit": {"type": "boolean", "example": False},
                        "routing_type": {"type": "string", "example": "direct_from_context"},
                        "context_used": {"type": "integer", "example": 1},
                        "quality_score": {"type": "number", "format": "float", "example": 1.0},
                        "quality_issues": {
                            "type": "array",
                            "items": {"type": "string"},
                            "example": [],
                        },
                    },
                },
            ),
            503: OpenApiResponse(description="AI xizmati vaqtincha o‘chirilgan."),
        },
        examples=[
            OpenApiExample(
                "Oddiy savol",
                summary="Muddat haqida savol",
                value={"question": "Muddatni kim yaratadi?"},
                request_only=True,
            ),
            OpenApiExample(
                "Hisobot bo‘yicha savol",
                summary="Accepted bo‘lgandan keyingi jarayon",
                value={"question": "Hisobot qabul qilinsa keyin nima bo'ladi?"},
                request_only=True,
            ),
            OpenApiExample(
                "Muvaffaqiyatli javob",
                summary="Response misoli",
                value={
                    "answer": "Muddatni odatda Super Admin yoki yuqori darajadagi mas'ul shaxs yaratadi.",
                    "response_time_ms": 126,
                    "llm_time_ms": 0,
                    "rag_time_ms": 120,
                    "cache_hit": False,
                    "routing_type": "direct_from_context",
                    "context_used": 1,
                    "quality_score": 1.0,
                    "quality_issues": [],
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        if not getattr(settings, "AI_ENABLED", False):
            return Response(
                {"detail": "AI xizmati hozircha o'chirilgan."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        serializer = AIRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question = serializer.validated_data["question"]
        service = AIService()
        result = service.ask(question)

        return Response(result, status=status.HTTP_200_OK)