from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from common.money import format_npr
from groups.models import Group
from notifications.models import Activity, Notification
from notifications.services import log_activity, notify

from . import gateways
from .models import Settlement
from .serializers import SettlementCreateSerializer, SettlementSerializer


def complete_settlement(settlement, reference=""):
    """Mark successful + activity + notification. Balances update automatically
    because the balance engine only counts successful settlements."""
    with transaction.atomic():
        locked = Settlement.objects.select_for_update().get(pk=settlement.pk)
        if locked.status != Settlement.Status.PENDING:
            return locked
        locked.mark_successful(reference)
    s = locked
    via = s.get_method_display()
    log_activity(
        s.group, s.payer, Activity.Action.SETTLEMENT,
        f"{s.payer.full_name} settled {format_npr(s.amount)} with {s.recipient.full_name} via {via}",
        amount=s.amount,
    )
    if s.created_by_id == s.recipient_id:
        notify([s.payer], Notification.Kind.SETTLEMENT, "Settlement recorded",
               f"{s.recipient.full_name} recorded {format_npr(s.amount)} cash from you", group=s.group)
    else:
        notify([s.recipient], Notification.Kind.SETTLEMENT, "Settlement received",
               f"{s.payer.full_name} paid you {format_npr(s.amount)} via {via}", group=s.group)
    Group.objects.filter(pk=s.group_id).update(updated_at=timezone.now())
    return s


class SettlementViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                        mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    GET  /api/settlements/?group=<id>&status=successful
    POST /api/settlements/
    GET  /api/settlements/{id}/
    POST /api/settlements/{id}/confirm/        (simulation)
    POST /api/settlements/{id}/cancel/
    POST /api/settlements/{id}/verify-esewa/   {"data": "<base64 from eSewa>"}
    POST /api/settlements/{id}/verify-khalti/  {"pidx": "..."}
    """

    serializer_class = SettlementSerializer

    def get_queryset(self):
        qs = (
            Settlement.objects.filter(group__memberships__user=self.request.user)
            .select_related("group", "payer", "recipient", "created_by")
            .distinct()
        )
        params = self.request.query_params
        if params.get("group"):
            qs = qs.filter(group_id=params["group"])
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("mine") == "1":
            from django.db.models import Q

            qs = qs.filter(Q(payer=self.request.user) | Q(recipient=self.request.user))
        return qs

    def _payload(self, settlement, next_step=None, code=status.HTTP_200_OK):
        settlement.refresh_from_db()
        data = {"settlement": SettlementSerializer(settlement, context={"request": self.request}).data}
        if next_step:
            data["next"] = next_step
        return Response(data, status=code)

    def create(self, request, *args, **kwargs):
        serializer = SettlementCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        settlement = Settlement.objects.create(
            group=d["group"], payer=d["payer"], recipient=d["recipient"], amount=d["amount"],
            method=d["method"], channel=d["channel"], note=d.get("note", ""), created_by=request.user,
        )

        if settlement.method == Settlement.Method.CASH:
            complete_settlement(settlement)
            return self._payload(settlement, {"type": "done"}, status.HTTP_201_CREATED)

        if settlement.channel == Settlement.Channel.SIMULATION:
            return self._payload(settlement, {"type": "simulation"}, status.HTTP_201_CREATED)

        # Real test gateway
        try:
            if settlement.method == Settlement.Method.ESEWA:
                form = gateways.esewa_form(settlement)
                return self._payload(settlement, {"type": "form_post", **form}, status.HTTP_201_CREATED)
            data = gateways.khalti_initiate(settlement, request.user)
        except gateways.GatewayError as exc:
            settlement.mark_failed()
            raise ValidationError(str(exc))
        settlement.gateway_reference = data["pidx"]
        settlement.save(update_fields=["gateway_reference"])
        return self._payload(settlement, {"type": "redirect", "url": data["payment_url"]}, status.HTTP_201_CREATED)

    def _pending_for_payer(self, pk):
        settlement = self.get_object()
        if settlement.payer_id != self.request.user.pk:
            raise PermissionDenied("Only the payer can complete this payment.")
        return settlement

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        settlement = self._pending_for_payer(pk)
        if settlement.channel != Settlement.Channel.SIMULATION:
            raise ValidationError("This payment must be confirmed by the payment gateway.")
        if settlement.status != Settlement.Status.PENDING:
            return self._payload(settlement)
        pin = str(request.data.get("pin", "")).strip()
        if settlement.method == Settlement.Method.KHALTI and len(pin) != 4:
            raise ValidationError({"pin": "Enter any 4-digit MPIN (simulation)."})
        prefix = "ESW" if settlement.method == Settlement.Method.ESEWA else "KHL"
        reference = f"SIM-{prefix}-{timezone.now():%H%M%S}{settlement.pk}"
        complete_settlement(settlement, reference)
        return self._payload(settlement)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        settlement = self._pending_for_payer(pk)
        if settlement.status == Settlement.Status.PENDING:
            settlement.mark_failed()
        return self._payload(settlement)

    @action(detail=True, methods=["post"], url_path="verify-esewa")
    def verify_esewa(self, request, pk=None):
        settlement = self._pending_for_payer(pk)
        if settlement.method != Settlement.Method.ESEWA:
            raise ValidationError("Not an eSewa payment.")
        if settlement.status != Settlement.Status.PENDING:
            return self._payload(settlement)
        if request.data.get("failed"):
            settlement.mark_failed()
            return self._payload(settlement)
        try:
            payload = gateways.esewa_decode_response(str(request.data.get("data", "")))
        except gateways.GatewayError as exc:
            raise ValidationError(str(exc))
        if payload.get("transaction_uuid") != settlement.transaction_id:
            raise ValidationError("This eSewa response belongs to a different transaction.")
        if not gateways.esewa_amount_matches(payload.get("total_amount"), settlement):
            raise ValidationError("The amount paid does not match the settlement.")
        if payload.get("status") != "COMPLETE":
            settlement.mark_failed(payload.get("transaction_code", ""))
            return self._payload(settlement)
        # Double-check with eSewa's server when reachable (signature already verified)
        remote = gateways.esewa_status_check(settlement)
        if remote not in (None, "COMPLETE"):
            raise ValidationError(f"eSewa reports this payment as {remote}.")
        complete_settlement(settlement, payload.get("transaction_code", ""))
        return self._payload(settlement)

    @action(detail=True, methods=["post"], url_path="verify-khalti")
    def verify_khalti(self, request, pk=None):
        settlement = self._pending_for_payer(pk)
        if settlement.method != Settlement.Method.KHALTI:
            raise ValidationError("Not a Khalti payment.")
        if settlement.status != Settlement.Status.PENDING:
            return self._payload(settlement)
        pidx = str(request.data.get("pidx", ""))
        if not pidx or pidx != settlement.gateway_reference:
            raise ValidationError("This Khalti response belongs to a different transaction.")
        try:
            data = gateways.khalti_lookup(pidx)
        except gateways.GatewayError as exc:
            raise ValidationError(str(exc))
        state = data.get("status")
        if state == "Completed" and int(data.get("total_amount", 0)) == int(settlement.amount * 100):
            complete_settlement(settlement, data.get("transaction_id") or pidx)
        elif state in ("User canceled", "Expired", "Refunded", "Failed"):
            settlement.mark_failed()
        return self._payload(settlement, {"gateway_status": state})


class PaymentConfigView(APIView):
    def get(self, request):
        return Response(gateways.payment_config())
