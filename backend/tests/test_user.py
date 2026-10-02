import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from accounts.models import User


@pytest.mark.django_db
def test_user_uses_canonical_email_as_login_identifier() -> None:
    user_model = get_user_model()
    user = user_model.objects.create_user(
        email="  Applicant@Example.COM  ", password="test-password"
    )

    assert isinstance(user, User)
    assert user.email == "applicant@example.com"
    assert user.USERNAME_FIELD == "email"
    assert not hasattr(user, "username")
    assert user.check_password("test-password")
    assert User.objects.get_by_natural_key("APPLICANT@EXAMPLE.COM") == user


@pytest.mark.django_db
def test_regular_save_canonicalizes_email() -> None:
    user = User(email="First@Example.COM")
    user.set_unusable_password()
    user.save()

    assert user.email == "first@example.com"
    assert User.objects.get(pk=user.pk).email == "first@example.com"


@pytest.mark.django_db
def test_mixed_case_email_identity_must_be_unique() -> None:
    User.objects.create_user(email="Applicant@Example.com", password="test-password")

    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(email="applicant@example.COM", password="test-password")


@pytest.mark.django_db
def test_database_rejects_mixed_case_email_that_bypasses_model_save() -> None:
    user = User(email="Bypass@Example.COM")
    user.set_unusable_password()

    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.bulk_create([user])
