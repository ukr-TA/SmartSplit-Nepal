"""
eSewa and Khalti payment gateway helpers (sandbox / test environments).

SmartSplit supports two ways of paying with eSewa or Khalti:

* simulation — an in-app screen that looks like the wallet and generates a
  mock transaction ID. Works offline; used for the classroom demo.
* sandbox    — a real redirect to the wallet's official *test* environment
  using test credentials. No real money moves.

Note: eSewa ePay and Khalti KPG pay a *merchant* account. Real peer-to-peer
wallet transfers between friends are not offered through public APIs, so in
SmartSplit the gateway step demonstrates the integration and confirms the
payment, and the app then records the settlement between the two members.
"""

import base64
import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal

from django.conf import settings

logger = logging.getLogger(__name__)


class GatewayError(Exception):
    """Something went wrong talking to a payment gateway (message is user-safe)."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def esewa_available():
    return bool(settings.ESEWA_ENABLED and settings.ESEWA_SECRET_KEY and settings.ESEWA_PRODUCT_CODE)


def khalti_available():
    return bool(settings.KHALTI_SECRET_KEY)


def payment_config():
    return {
        "esewa": {"simulation": True, "sandbox": esewa_available()},
        "khalti": {"simulation": True, "sandbox": khalti_available()},
        "khalti_minimum": "10.00",
    }


def _amount_str(amount):
    """eSewa expects plain numbers like 1250 or 1250.5 — no commas."""
    amount = Decimal(amount).quantize(Decimal("0.01"))
    return format(amount.normalize(), "f") if amount == amount.to_integral() else str(amount)


# ---------------------------------------------------------------------------
# eSewa ePay v2
# ---------------------------------------------------------------------------

def esewa_signature(message):
    digest = hmac.new(settings.ESEWA_SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def esewa_form(settlement):
    """Fields for the auto-submitted HTML form that sends the user to eSewa."""
    total = _amount_str(settlement.amount)
    fields = {
        "amount": total,
        "tax_amount": "0",
        "product_service_charge": "0",
        "product_delivery_charge": "0",
        "total_amount": total,
        "transaction_uuid": settlement.transaction_id,
        "product_code": settings.ESEWA_PRODUCT_CODE,
        # eSewa appends ?data=<base64> to these URLs
        "success_url": f"{settings.FRONTEND_URL}/payments/esewa/success/{settlement.pk}",
        "failure_url": f"{settings.FRONTEND_URL}/payments/esewa/failure/{settlement.pk}",
        "signed_field_names": "total_amount,transaction_uuid,product_code",
    }
    message = f"total_amount={total},transaction_uuid={settlement.transaction_id},product_code={settings.ESEWA_PRODUCT_CODE}"
    fields["signature"] = esewa_signature(message)
    return {"url": settings.ESEWA_FORM_URL, "fields": fields}


def esewa_decode_response(data):
    """Decode + verify the base64 JSON eSewa sends back to success_url."""
    try:
        padded = data + "=" * (-len(data) % 4)
        payload = json.loads(base64.b64decode(padded).decode())
    except (ValueError, UnicodeDecodeError) as exc:
        raise GatewayError("Could not read the response from eSewa.") from exc

    names = payload.get("signed_field_names", "")
    if not names or "signature" not in payload:
        raise GatewayError("The eSewa response is missing its signature.")
    message = ",".join(f"{name}={payload.get(name, '')}" for name in names.split(","))
    if not hmac.compare_digest(esewa_signature(message), payload["signature"]):
        raise GatewayError("The eSewa response signature is invalid.")
    return payload


def esewa_status_check(settlement):
    """Ask eSewa directly for the transaction status. Returns status string or None if unreachable."""
    query = urllib.parse.urlencode({
        "product_code": settings.ESEWA_PRODUCT_CODE,
        "total_amount": _amount_str(settlement.amount),
        "transaction_uuid": settlement.transaction_id,
    })
    try:
        with urllib.request.urlopen(f"{settings.ESEWA_STATUS_URL}?{query}", timeout=10) as resp:
            return json.loads(resp.read().decode()).get("status")
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        logger.warning("eSewa status check failed: %s", exc)
        return None


def esewa_amount_matches(payload_amount, settlement):
    try:
        return Decimal(str(payload_amount).replace(",", "")) == Decimal(settlement.amount)
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# Khalti KPG-2 (ePayment)
# ---------------------------------------------------------------------------

def _khalti_post(path, body):
    request = urllib.request.Request(
        f"{settings.KHALTI_BASE_URL.rstrip('/')}/{path.lstrip('/')}",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Key {settings.KHALTI_SECRET_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode())
        except ValueError:
            detail = {}
        logger.warning("Khalti error %s: %s", exc.code, detail)
        if exc.code == 401:
            raise GatewayError("Khalti rejected the secret key. Check KHALTI_SECRET_KEY in backend/.env.") from exc
        if exc.code in (400, 404) and path.startswith("epayment/lookup"):
            return detail  # lookup returns 400 for expired / canceled with a status field
        message = detail.get("detail") or next(iter(detail.values()), None) if detail else None
        if isinstance(message, list):
            message = message[0]
        raise GatewayError(f"Khalti error: {message or exc.reason}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise GatewayError("Could not reach Khalti. Check your internet connection.") from exc


def khalti_initiate(settlement, customer):
    body = {
        "return_url": f"{settings.FRONTEND_URL}/payments/khalti/return/{settlement.pk}",
        "website_url": settings.FRONTEND_URL,
        "amount": int(Decimal(settlement.amount) * 100),
        "purchase_order_id": settlement.transaction_id,
        "purchase_order_name": f"SmartSplit settlement - {settlement.group.name}"[:100],
        "customer_info": {
            "name": customer.full_name,
            "email": customer.email,
            "phone": customer.phone_number,
        },
    }
    data = _khalti_post("epayment/initiate/", body)
    if "payment_url" not in data:
        raise GatewayError("Khalti did not return a payment link.")
    return data


def khalti_lookup(pidx):
    return _khalti_post("epayment/lookup/", {"pidx": pidx})
