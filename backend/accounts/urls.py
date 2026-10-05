from django.urls import path

from accounts.views import (
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    SessionView,
    VerificationConfirmView,
    VerificationRequestView,
)

urlpatterns = [
    path("session/", SessionView.as_view(), name="auth-session"),
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path(
        "email-verification/request/",
        VerificationRequestView.as_view(),
        name="auth-verification-request",
    ),
    path(
        "email-verification/confirm/",
        VerificationConfirmView.as_view(),
        name="auth-verification-confirm",
    ),
    path(
        "password-reset/request/",
        PasswordResetRequestView.as_view(),
        name="auth-password-reset-request",
    ),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
]
