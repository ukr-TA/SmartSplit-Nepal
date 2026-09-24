"""Shared test helpers."""

from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from users.models import User


def make_user(name, phone, email=None, password="Str0ng!pass"):
    email = email or f"{name.lower().replace(' ', '.')}@example.com"
    return User.objects.create_user(email=email, password=password, full_name=name, phone_number=phone)


def client_for(user):
    client = APIClient()
    token, _ = Token.objects.get_or_create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


def make_group(owner, members, name="Pokhara Trip", **extra):
    client = client_for(owner)
    response = client.post(
        "/api/groups/",
        {"name": name, "group_type": "trip", "member_ids": [m.pk for m in members], **extra},
        format="json",
    )
    assert response.status_code == 201, response.data
    return response.data["id"]


def add_expense(user, group_id, amount, participants, payer=None, **extra):
    data = {
        "group": group_id,
        "description": extra.pop("description", "Expense"),
        "amount": str(amount),
        "category": extra.pop("category", "food"),
        "paid_by": (payer or user).pk,
        "split_method": extra.pop("split_method", "equal"),
        "participants": [p.pk for p in participants],
        **extra,
    }
    response = client_for(user).post("/api/expenses/", data, format="json")
    assert response.status_code == 201, response.data
    return response.data
