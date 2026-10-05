from collections.abc import Callable
from typing import cast
from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.api_exceptions import StableAPIError
from accounts.models import User
from accounts.serializers import ErrorEnvelopeSerializer
from projects.exceptions import ProjectNotFoundError, ProjectValidationError
from projects.models import Project
from projects.serializers import (
    ProjectListEnvelopeSerializer,
    ProjectSerializer,
    ProjectWriteSerializer,
)
from projects.services import (
    ProjectCreateData,
    ProjectPatch,
    activate_project,
    create_project,
    deactivate_project,
    update_project,
)

CSRF_HEADER = OpenApiParameter(
    name="X-CSRFToken",
    type=str,
    location=OpenApiParameter.HEADER,
    required=True,
    description="Current csrftoken cookie value for every unsafe request.",
)


def _not_found() -> StableAPIError:
    return StableAPIError(
        code="not_found",
        message="Project not found.",
        status_code=status.HTTP_404_NOT_FOUND,
    )


def _parse_project_id(raw_id: str) -> UUID:
    try:
        return UUID(raw_id)
    except (ValueError, AttributeError) as exc:
        raise _not_found() from exc


def _service_result(call: Callable[[], Project]) -> Project:
    try:
        return call()
    except ProjectNotFoundError as exc:
        raise _not_found() from exc
    except ProjectValidationError as exc:
        raise StableAPIError(fields=exc.field_errors) from exc


def _owned_project(*, request: Request, project_id: UUID) -> Project:
    project = Project.objects.filter(id=project_id, owner=cast(User, request.user)).first()
    if project is None:
        raise _not_found()
    return project


class ProjectAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def handle_exception(self, exc: Exception) -> Response:
        if isinstance(exc, MethodNotAllowed):
            stable = StableAPIError(
                code="method_not_allowed",
                message="Method not allowed.",
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            )
            return super().handle_exception(stable)
        return super().handle_exception(exc)


class ProjectCollectionView(ProjectAPIView):
    @extend_schema(
        operation_id="projects_list",
        responses={200: ProjectListEnvelopeSerializer, 401: ErrorEnvelopeSerializer},
    )
    def get(self, request: Request) -> Response:
        projects = Project.objects.filter(owner=cast(User, request.user))
        return Response(ProjectListEnvelopeSerializer({"projects": projects}).data)

    @extend_schema(
        operation_id="projects_create",
        request=ProjectWriteSerializer,
        parameters=[CSRF_HEADER],
        responses={
            201: ProjectSerializer,
            400: ErrorEnvelopeSerializer,
            401: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        serializer = ProjectWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = _service_result(
            lambda: create_project(
                actor=cast(User, request.user),
                data=cast(ProjectCreateData, serializer.validated_data),
            )
        )
        return Response(ProjectSerializer(project).data, status=status.HTTP_201_CREATED)


class ProjectDetailView(ProjectAPIView):
    @extend_schema(
        operation_id="projects_retrieve",
        parameters=[OpenApiParameter("id", type=str, location=OpenApiParameter.PATH)],
        responses={
            200: ProjectSerializer,
            401: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
        },
    )
    def get(self, request: Request, id: str) -> Response:  # noqa: A002
        project = _owned_project(request=request, project_id=_parse_project_id(id))
        return Response(ProjectSerializer(project).data)

    @extend_schema(
        operation_id="projects_update",
        parameters=[
            OpenApiParameter("id", type=str, location=OpenApiParameter.PATH),
            CSRF_HEADER,
        ],
        request=ProjectWriteSerializer,
        responses={
            200: ProjectSerializer,
            400: ErrorEnvelopeSerializer,
            401: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
        },
    )
    def patch(self, request: Request, id: str) -> Response:  # noqa: A002
        project_id = _parse_project_id(id)
        _owned_project(request=request, project_id=project_id)
        serializer = ProjectWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        project = _service_result(
            lambda: update_project(
                actor=cast(User, request.user),
                project_id=project_id,
                patch=cast(ProjectPatch, serializer.validated_data),
            )
        )
        return Response(ProjectSerializer(project).data)


class ProjectLifecycleView(ProjectAPIView):
    action: str

    def post(self, request: Request, id: str) -> Response:  # noqa: A002
        project_id = _parse_project_id(id)
        service = activate_project if self.action == "activate" else deactivate_project
        project = _service_result(
            lambda: service(actor=cast(User, request.user), project_id=project_id)
        )
        return Response(ProjectSerializer(project).data)


class ProjectActivateView(ProjectLifecycleView):
    action = "activate"

    @extend_schema(
        operation_id="projects_activate",
        description="Activate the saved project.",
        parameters=[
            OpenApiParameter("id", type=str, location=OpenApiParameter.PATH),
            CSRF_HEADER,
        ],
        request=None,
        responses={
            200: ProjectSerializer,
            400: ErrorEnvelopeSerializer,
            401: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request: Request, id: str) -> Response:  # noqa: A002
        return super().post(request, id)


class ProjectDeactivateView(ProjectLifecycleView):
    action = "deactivate"

    @extend_schema(
        operation_id="projects_deactivate",
        description="Return the saved project to draft.",
        parameters=[
            OpenApiParameter("id", type=str, location=OpenApiParameter.PATH),
            CSRF_HEADER,
        ],
        request=None,
        responses={
            200: ProjectSerializer,
            400: ErrorEnvelopeSerializer,
            401: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            404: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request: Request, id: str) -> Response:  # noqa: A002
        return super().post(request, id)
