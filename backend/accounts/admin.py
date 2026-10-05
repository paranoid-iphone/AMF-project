from typing import cast

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path

from accounts.models import Invitation, User
from accounts.security import request_correlation_id
from accounts.services import issue_invitation, revoke_invitation


@admin.register(User)
class UserAdmin(DjangoUserAdmin):  # type: ignore[type-arg]
    ordering = ("email",)
    list_display = ("email", "email_verified_at", "is_staff", "is_active")
    search_fields = ("email",)
    readonly_fields = ("email_verified_at",)
    fieldsets = (
        (None, {"fields": ("email", "password", "email_verified_at")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_staff", "is_active"),
            },
        ),
    )


class InvitationIssueForm(forms.Form):
    email = forms.EmailField()


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("id", "email", "state", "created_at", "expires_at", "sent_at")
    search_fields = ("email", "id")
    readonly_fields = (
        "id",
        "email",
        "created_by",
        "created_at",
        "sent_at",
        "expires_at",
        "revoked_at",
        "accepted_at",
        "accepted_by",
    )
    actions = ("revoke_selected",)

    def has_module_permission(self, request: HttpRequest) -> bool:
        return bool(request.user.is_active and request.user.is_superuser)

    def has_view_permission(self, request: HttpRequest, obj: Invitation | None = None) -> bool:
        del obj
        return self.has_module_permission(request)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return self.has_module_permission(request)

    def has_change_permission(self, request: HttpRequest, obj: Invitation | None = None) -> bool:
        del obj
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Invitation | None = None) -> bool:
        del request, obj
        return False

    def get_urls(self):  # type: ignore[no-untyped-def]
        return [
            path("invite/", self.admin_site.admin_view(self.invite_view), name="accounts_invite")
        ] + super().get_urls()

    def add_view(
        self,
        request: HttpRequest,
        form_url: str = "",
        extra_context: dict[str, object] | None = None,
    ) -> HttpResponse:
        del form_url, extra_context
        return self.invite_view(request)

    def invite_view(self, request: HttpRequest) -> HttpResponse:
        if not self.has_add_permission(request):
            raise PermissionDenied
        form = InvitationIssueForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            issued = issue_invitation(
                email=form.cleaned_data["email"],
                actor=cast(User, request.user),
                request_id=request_correlation_id(request.headers.get("X-Request-ID")),
                ip_address=request.META.get("REMOTE_ADDR"),
            )
            self.message_user(
                request,
                f"Invitation {issued.invitation.id} issued and delivery queued.",
                messages.SUCCESS,
            )
            return redirect("admin:accounts_invitation_changelist")
        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "form": form,
            "title": "Invite applicant",
        }
        return TemplateResponse(request, "admin/accounts/invitation/invite_form.html", context)

    @admin.action(description="Revoke selected pending invitations")
    def revoke_selected(self, request: HttpRequest, queryset):  # type: ignore[no-untyped-def]
        revoked = 0
        for selector in queryset.values_list("pk", flat=True):
            if revoke_invitation(
                selector=selector,
                actor=cast(User, request.user),
                request_id=request_correlation_id(request.headers.get("X-Request-ID")),
                ip_address=request.META.get("REMOTE_ADDR"),
            ):
                revoked += 1
        self.message_user(request, f"Revoked {revoked} invitation(s).", messages.SUCCESS)
