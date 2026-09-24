import base64
import json
from decimal import Decimal
from unittest import mock

from django.test import SimpleTestCase, override_settings
from rest_framework.test import APITestCase

from common.testing import add_expense, client_for, make_group, make_user

from . import gateways
from .algorithm import minimize_transactions
from .models import Settlement


class AlgorithmTests(SimpleTestCase):
    def test_example_from_project_brief(self):
        # Ram +200, Sita +700, Utsuk -500, Hari -400
        balances = {"ram": 20000, "sita": 70000, "utsuk": -50000, "hari": -40000}
        plan = minimize_transactions(balances, order={k: k for k in balances})
        self.assertIn(("utsuk", "sita", 50000), plan)
        self.assertEqual(len(plan), 3)
        self._assert_settles(balances, plan)

    def test_exact_match_is_preferred(self):
        balances = {"a": -300, "b": -500, "c": 500, "d": 300}
        plan = minimize_transactions(balances)
        self.assertEqual(sorted(plan), [("a", "d", 300), ("b", "c", 500)])

    def test_at_most_n_minus_one_payments(self):
        import random

        rng = random.Random(7)
        for _ in range(200):
            n = rng.randint(2, 9)
            values = [rng.randint(-50000, 50000) for _ in range(n - 1)]
            values.append(-sum(values))
            balances = dict(enumerate(values))
            plan = minimize_transactions(balances)
            nonzero = sum(1 for v in values if v)
            self.assertLessEqual(len(plan), max(nonzero - 1, 0))
            self._assert_settles(balances, plan)

    def test_rejects_unbalanced_input(self):
        with self.assertRaises(ValueError):
            minimize_transactions({"a": 100, "b": -50})

    def _assert_settles(self, balances, plan):
        result = dict(balances)
        for debtor, creditor, amount in plan:
            self.assertGreater(amount, 0)
            result[debtor] += amount
            result[creditor] -= amount
        self.assertTrue(all(v == 0 for v in result.values()), result)


class PokharaScenarioTests(APITestCase):
    """The final demonstration scenario from the project brief."""

    def setUp(self):
        self.u = make_user("Utsuk", "9812345678")
        self.ram = make_user("Ram", "9800000001")
        self.sita = make_user("Sita", "9800000002")
        self.hari = make_user("Hari", "9800000003")
        self.mina = make_user("Mina", "9800000004")
        self.everyone = [self.u, self.ram, self.sita, self.hari, self.mina]
        self.group = make_group(self.u, self.everyone[1:])
        add_expense(self.u, self.group, "12000", self.everyone, description="Hotel", category="hotel")
        add_expense(self.u, self.group, "6500", self.everyone, payer=self.ram, description="Food")
        add_expense(self.u, self.group, "8000", self.everyone, payer=self.sita, description="Bus", category="transport")
        add_expense(self.u, self.group, "4000", self.everyone, payer=self.hari, description="Paragliding",
                    category="entertainment")

    def balances(self, user=None):
        return client_for(user or self.u).get(f"/api/groups/{self.group}/balances/").data

    def test_net_balances(self):
        data = self.balances()
        nets = {m["user"]["full_name"]: m["net"] for m in data["members"]}
        # total 30,500 / 5 = 6,100 each
        self.assertEqual(nets, {
            "Utsuk": Decimal("5900.00"), "Ram": Decimal("400.00"), "Sita": Decimal("1900.00"),
            "Hari": Decimal("-2100.00"), "Mina": Decimal("-6100.00"),
        })
        self.assertEqual(sum(nets.values()), 0)
        self.assertEqual(data["total_spent"], Decimal("30500.00"))
        self.assertLessEqual(data["stats"]["smart_transactions"], 4)
        self.assertGreater(data["stats"]["direct_transactions"], data["stats"]["smart_transactions"])

    def test_settlement_flow_updates_balances(self):
        mina = client_for(self.mina)
        plan = self.balances(self.mina)["you_give"]
        self.assertTrue(plan)
        target = plan[0]
        # overpaying is rejected
        res = mina.post("/api/settlements/", {
            "group": self.group, "recipient": target["user"]["id"], "amount": "999999",
            "method": "khalti"}, format="json")
        self.assertEqual(res.status_code, 400)

        res = mina.post("/api/settlements/", {
            "group": self.group, "recipient": target["user"]["id"], "amount": str(target["amount"]),
            "method": "khalti", "channel": "simulation"}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["next"]["type"], "simulation")
        s = res.data["settlement"]
        self.assertTrue(s["transaction_id"].startswith("SMRT-KHL-"))
        self.assertEqual(s["status"], "pending")
        # pending does not change balances
        self.assertEqual(self.balances(self.mina)["my_net"], Decimal("-6100.00"))

        self.assertEqual(mina.post(f"/api/settlements/{s['id']}/confirm/", {"pin": "12"}, format="json").status_code, 400)
        # someone else cannot confirm Mina's payment
        self.assertEqual(client_for(self.ram).post(f"/api/settlements/{s['id']}/confirm/").status_code, 403)
        res = mina.post(f"/api/settlements/{s['id']}/confirm/", {"pin": "1111"}, format="json")
        self.assertEqual(res.data["settlement"]["status"], "successful")
        self.assertEqual(self.balances(self.mina)["my_net"], Decimal("-6100.00") + Decimal(target["amount"]))

        # recipient is notified; activity recorded
        notes = client_for(Settlement.objects.get(pk=s["id"]).recipient).get("/api/notifications/").data
        self.assertEqual(notes["results"][0]["title"], "Settlement received")
        activity = client_for(self.u).get(f"/api/groups/{self.group}/activity/").data
        self.assertEqual(activity[0]["action"], "settlement")

    def test_settle_everything_with_cash_and_esewa(self):
        # Follow the smart plan until the group is settled
        for _ in range(10):
            suggestions = self.balances()["suggestions"]
            if not suggestions:
                break
            sug = suggestions[0]
            payer = next(x for x in self.everyone if x.pk == sug["from_user"]["id"])
            res = client_for(payer).post("/api/settlements/", {
                "group": self.group, "recipient": sug["to_user"]["id"], "amount": str(sug["amount"]),
                "method": "cash"}, format="json")
            self.assertEqual(res.status_code, 201, res.data)
            self.assertEqual(res.data["settlement"]["status"], "successful")
        data = self.balances()
        self.assertTrue(data["stats"]["is_settled"])
        self.assertTrue(all(m["net"] == 0 for m in data["members"]))
        # dashboard is consistent
        dash = client_for(self.mina).get("/api/dashboard/").data
        self.assertEqual(dash["summary"]["you_owe"], Decimal("0.00"))
        # and now the owner may delete the group
        self.assertEqual(client_for(self.u).delete(f"/api/groups/{self.group}/").status_code, 204)

    def test_recipient_can_record_cash_received(self):
        res = client_for(self.u).post("/api/settlements/", {
            "group": self.group, "payer": self.mina.pk, "recipient": self.u.pk,
            "amount": "1000", "method": "cash"}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        # but a third person can't record it
        res = client_for(self.ram).post("/api/settlements/", {
            "group": self.group, "payer": self.mina.pk, "recipient": self.u.pk,
            "amount": "1000", "method": "cash"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_creditor_cannot_pay(self):
        res = client_for(self.u).post("/api/settlements/", {
            "group": self.group, "recipient": self.ram.pk, "amount": "100", "method": "cash"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_dashboard_summary(self):
        dash = client_for(self.u).get("/api/dashboard/").data
        self.assertEqual(dash["summary"]["you_are_owed"], Decimal("5900.00"))
        self.assertEqual(dash["summary"]["net_balance"], Decimal("5900.00"))
        self.assertEqual(dash["summary"]["active_groups"], 1)
        self.assertEqual(len(dash["recent_expenses"]), 4)

    def test_analytics(self):
        data = client_for(self.u).get(f"/api/groups/{self.group}/analytics/").data
        self.assertEqual(data["total_spent"], Decimal("30500.00"))
        self.assertEqual(data["by_category"][0]["category"], "hotel")
        self.assertEqual(data["average_per_person"], Decimal("6100.00"))
        self.assertEqual(len(data["daily"]), 1)

    def test_esewa_sandbox_flow_with_signed_response(self):
        mina = client_for(self.mina)
        target = self.balances(self.mina)["you_give"][0]
        res = mina.post("/api/settlements/", {
            "group": self.group, "recipient": target["user"]["id"], "amount": str(target["amount"]),
            "method": "esewa", "channel": "sandbox"}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        nxt = res.data["next"]
        self.assertEqual(nxt["type"], "form_post")
        fields = nxt["fields"]
        expected = gateways.esewa_signature(
            f"total_amount={fields['total_amount']},transaction_uuid={fields['transaction_uuid']},product_code=EPAYTEST")
        self.assertEqual(fields["signature"], expected)
        sid = res.data["settlement"]["id"]

        def encoded(status_value, amount):
            payload = {
                "transaction_code": "000AE01", "status": status_value, "total_amount": amount,
                "transaction_uuid": fields["transaction_uuid"], "product_code": "EPAYTEST",
                "signed_field_names": "transaction_code,status,total_amount,transaction_uuid,product_code,signed_field_names",
            }
            msg = ",".join(f"{k}={payload[k]}" for k in payload["signed_field_names"].split(","))
            payload["signature"] = gateways.esewa_signature(msg)
            return base64.b64encode(json.dumps(payload).encode()).decode()

        # tampered signature is rejected
        bad = json.loads(base64.b64decode(encoded("COMPLETE", fields["total_amount"])))
        bad["total_amount"] = "1"
        res = mina.post(f"/api/settlements/{sid}/verify-esewa/",
                        {"data": base64.b64encode(json.dumps(bad).encode()).decode()}, format="json")
        self.assertEqual(res.status_code, 400)

        with mock.patch.object(gateways, "esewa_status_check", return_value="COMPLETE"):
            res = mina.post(f"/api/settlements/{sid}/verify-esewa/",
                            {"data": encoded("COMPLETE", f"{Decimal(fields['total_amount']):,.1f}")}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["settlement"]["status"], "successful")
        self.assertEqual(res.data["settlement"]["gateway_reference"], "000AE01")

    def test_khalti_sandbox_requires_key(self):
        target = self.balances(self.mina)["you_give"][0]
        res = client_for(self.mina).post("/api/settlements/", {
            "group": self.group, "recipient": target["user"]["id"], "amount": str(target["amount"]),
            "method": "khalti", "channel": "sandbox"}, format="json")
        self.assertEqual(res.status_code, 400)

    @override_settings(KHALTI_SECRET_KEY="test-key")
    def test_khalti_sandbox_flow_mocked(self):
        mina = client_for(self.mina)
        target = self.balances(self.mina)["you_give"][0]
        with mock.patch.object(gateways, "_khalti_post", return_value={
                "pidx": "PIDX123", "payment_url": "https://test-pay.khalti.com/?pidx=PIDX123"}):
            res = mina.post("/api/settlements/", {
                "group": self.group, "recipient": target["user"]["id"], "amount": str(target["amount"]),
                "method": "khalti", "channel": "sandbox"}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["next"]["type"], "redirect")
        sid = res.data["settlement"]["id"]
        paisa = int(Decimal(target["amount"]) * 100)
        with mock.patch.object(gateways, "_khalti_post", return_value={
                "pidx": "PIDX123", "status": "Completed", "total_amount": paisa, "transaction_id": "KT1"}):
            self.assertEqual(mina.post(f"/api/settlements/{sid}/verify-khalti/", {"pidx": "WRONG"}).status_code, 400)
            res = mina.post(f"/api/settlements/{sid}/verify-khalti/", {"pidx": "PIDX123"})
        self.assertEqual(res.data["settlement"]["status"], "successful")
        self.assertEqual(res.data["settlement"]["gateway_reference"], "KT1")
