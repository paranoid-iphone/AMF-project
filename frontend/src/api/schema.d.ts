export interface paths {
    "/api/auth/email-verification/confirm/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["auth_email_verification_confirm_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/email-verification/request/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["auth_email_verification_request_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/login/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["auth_login_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/logout/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["auth_logout_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/password-reset/confirm/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["auth_password_reset_confirm_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/password-reset/request/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["auth_password_reset_request_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/register/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["auth_register_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/session/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["auth_session_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/health/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["health_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        Accepted: {
            status: components["schemas"]["AcceptedStatusEnum"];
        };
        /**
         * @description * `accepted` - accepted
         * @enum {string}
         */
        AcceptedStatusEnum: "accepted";
        /**
         * @description * `validation_error` - validation_error
         *     * `invalid_credentials` - invalid_credentials
         *     * `invalid_invitation` - invalid_invitation
         *     * `invalid_or_expired_token` - invalid_or_expired_token
         *     * `not_authenticated` - not_authenticated
         *     * `csrf_failed` - csrf_failed
         *     * `email_verification_required` - email_verification_required
         *     * `rate_limited` - rate_limited
         * @enum {string}
         */
        CodeEnum: "validation_error" | "invalid_credentials" | "invalid_invitation" | "invalid_or_expired_token" | "not_authenticated" | "csrf_failed" | "email_verification_required" | "rate_limited";
        ErrorDetail: {
            code: components["schemas"]["CodeEnum"];
            fields?: {
                [key: string]: components["schemas"]["ErrorItem"][];
            };
            message: string;
        };
        ErrorEnvelope: {
            error: components["schemas"]["ErrorDetail"];
        };
        ErrorItem: {
            code: string;
            message: string;
        };
        Health: {
            readonly database: string;
            readonly status: string;
        };
        LoginRequest: {
            /** Format: email */
            email: string;
            password: string;
        };
        PasswordResetConfirmRequest: {
            new_password: string;
            token: string;
            uid: string;
        };
        PasswordResetRequestRequest: {
            /** Format: email */
            email: string;
        };
        RegisterRequest: {
            /** Format: email */
            email: string;
            invitation_token: string;
            password: string;
        };
        Session: {
            authenticated: boolean;
            user: components["schemas"]["User"] | null;
        };
        TokenRequest: {
            token: string;
        };
        UnavailableHealth: {
            readonly database: string;
            readonly status: string;
        };
        User: {
            /** Format: email */
            readonly email: string;
            readonly email_verified: boolean;
            readonly id: number;
        };
        UserEnvelope: {
            user: components["schemas"]["User"];
        };
        Verified: {
            status: components["schemas"]["VerifiedStatusEnum"];
        };
        /**
         * @description * `verified` - verified
         * @enum {string}
         */
        VerifiedStatusEnum: "verified";
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    auth_email_verification_confirm_create: {
        parameters: {
            query?: never;
            header: {
                /** @description Current csrftoken cookie value for every unsafe request. */
                "X-CSRFToken": string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TokenRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["TokenRequest"];
                "multipart/form-data": components["schemas"]["TokenRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Verified"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    auth_email_verification_request_create: {
        parameters: {
            query?: never;
            header: {
                /** @description Current csrftoken cookie value for every unsafe request. */
                "X-CSRFToken": string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Accepted"];
                };
            };
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    auth_login_create: {
        parameters: {
            query?: never;
            header: {
                /** @description Current csrftoken cookie value for every unsafe request. */
                "X-CSRFToken": string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LoginRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["LoginRequest"];
                "multipart/form-data": components["schemas"]["LoginRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserEnvelope"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    auth_logout_create: {
        parameters: {
            query?: never;
            header: {
                /** @description Current csrftoken cookie value for every unsafe request. */
                "X-CSRFToken": string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description No response body */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    auth_password_reset_confirm_create: {
        parameters: {
            query?: never;
            header: {
                /** @description Current csrftoken cookie value for every unsafe request. */
                "X-CSRFToken": string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PasswordResetConfirmRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["PasswordResetConfirmRequest"];
                "multipart/form-data": components["schemas"]["PasswordResetConfirmRequest"];
            };
        };
        responses: {
            /** @description No response body */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    auth_password_reset_request_create: {
        parameters: {
            query?: never;
            header: {
                /** @description Current csrftoken cookie value for every unsafe request. */
                "X-CSRFToken": string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PasswordResetRequestRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["PasswordResetRequestRequest"];
                "multipart/form-data": components["schemas"]["PasswordResetRequestRequest"];
            };
        };
        responses: {
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Accepted"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    auth_register_create: {
        parameters: {
            query?: never;
            header: {
                /** @description Current csrftoken cookie value for every unsafe request. */
                "X-CSRFToken": string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RegisterRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["RegisterRequest"];
                "multipart/form-data": components["schemas"]["RegisterRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserEnvelope"];
                };
            };
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    auth_session_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Session"];
                };
            };
        };
    };
    health_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Health"];
                };
            };
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UnavailableHealth"];
                };
            };
        };
    };
}
