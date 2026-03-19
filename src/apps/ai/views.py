from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.ai.services.ai_service import AIService
from apps.ai.serializers.ai_serializer import AIRequestSerializer
from apps.ai.services.throttle import AIDailyThrottle


class AIChatView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AIDailyThrottle]

    def post(self, request):
        serializer = AIRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question = serializer.validated_data["question"]
        service = AIService()

        answer = service.ask(question)

        return Response({"answer": answer})