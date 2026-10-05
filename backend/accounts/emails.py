import logging
from collections.abc import Mapping
from typing import Any

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def send_templated_email(
    *, template_name: str, subject: str, recipient: str, context: Mapping[str, Any]
) -> bool:
    try:
        text_body = render_to_string(f"accounts/email/{template_name}.txt", context)
        html_body = render_to_string(f"accounts/email/{template_name}.html", context)
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        message.attach_alternative(html_body, "text/html")
        message.send(fail_silently=False)
    except Exception:
        logger.exception("Transactional email delivery failed", extra={"email_kind": template_name})
        return False
    return True
