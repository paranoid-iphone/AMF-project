from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CsrfSessionAuthenticationScheme(OpenApiAuthenticationExtension):  # type: ignore[no-untyped-call]
    target_class = "accounts.authentication.CsrfEnforcedSessionAuthentication"
    name = "cookieAuth"

    def get_security_definition(self, auto_schema):  # type: ignore[no-untyped-def]
        del auto_schema
        return {"type": "apiKey", "in": "cookie", "name": "sessionid"}
