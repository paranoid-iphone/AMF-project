from rest_framework import serializers

from accounts.models import User


class UserSerializer(serializers.ModelSerializer[User]):
    email_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "email_verified")
        read_only_fields = fields


class SessionSerializer(serializers.Serializer[dict[str, object]]):
    authenticated = serializers.BooleanField()
    user = UserSerializer(allow_null=True)


class UserEnvelopeSerializer(serializers.Serializer[dict[str, object]]):
    user = UserSerializer()


class RegisterSerializer(serializers.Serializer[dict[str, str]]):
    invitation_token = serializers.CharField(trim_whitespace=False)
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False, write_only=True)


class LoginSerializer(serializers.Serializer[dict[str, str]]):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False, write_only=True)


class TokenSerializer(serializers.Serializer[dict[str, str]]):
    token = serializers.CharField(trim_whitespace=False)


class PasswordResetRequestSerializer(serializers.Serializer[dict[str, str]]):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer[dict[str, str]]):
    uid = serializers.CharField(trim_whitespace=False)
    token = serializers.CharField(trim_whitespace=False)
    new_password = serializers.CharField(trim_whitespace=False, write_only=True)


class AcceptedSerializer(serializers.Serializer[dict[str, str]]):
    status = serializers.ChoiceField(choices=("accepted",))


class VerifiedSerializer(serializers.Serializer[dict[str, str]]):
    status = serializers.ChoiceField(choices=("verified",))


class ErrorItemSerializer(serializers.Serializer[dict[str, str]]):
    code = serializers.CharField()
    message = serializers.CharField()


class ErrorDetailSerializer(serializers.Serializer[dict[str, object]]):
    code = serializers.ChoiceField(
        choices=(
            "validation_error",
            "invalid_credentials",
            "invalid_invitation",
            "invalid_or_expired_token",
            "not_authenticated",
            "csrf_failed",
            "email_verification_required",
            "not_found",
            "method_not_allowed",
            "rate_limited",
        )
    )
    message = serializers.CharField()
    fields = serializers.DictField(  # type: ignore[assignment]
        child=serializers.ListField(child=ErrorItemSerializer()), required=False
    )


class ErrorEnvelopeSerializer(serializers.Serializer[dict[str, object]]):
    error = ErrorDetailSerializer()
