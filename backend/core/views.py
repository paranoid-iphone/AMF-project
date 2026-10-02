from django.db import DatabaseError, connection
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_503_SERVICE_UNAVAILABLE
from rest_framework.views import APIView

from core.serializers import HealthSerializer, UnavailableHealthSerializer


class HealthView(APIView):
    authentication_classes: list[type] = []
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="health_retrieve",
        responses={
            HTTP_200_OK: HealthSerializer,
            HTTP_503_SERVICE_UNAVAILABLE: UnavailableHealthSerializer,
        },
        auth=[],
    )
    def get(self, request: Request) -> Response:
        del request
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except DatabaseError:
            return Response(
                {"status": "unavailable", "database": "unavailable"},
                status=HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"status": "ok", "database": "ok"}, status=HTTP_200_OK)
