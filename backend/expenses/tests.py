from decimal import Decimal

from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from common.testing import add_expense, client_for, make_group, make_user

from .splitting import SplitError, split_custom, split_equal, split_percentage


class SplittingTests(SimpleTestCase):
    def test_equal_split_exact(self):
        self.assertEqual(split_equal(400000, [1, 2, 3, 4]), [(u, 100000, None) for u in [1, 2, 3, 4]])

    def test_equal_split_distributes_remainder_paisa(self):
        shares = split_equal(10000, [1, 2, 3])  # Rs. 100 / 3
        self.assertEqual([s[1] for s in shares], [3334, 3333, 3333])
        self.assertEqual(sum(s[1] for s in shares), 10000)

    def test_custom_split_must_match_total(self):
        self.assertEqual(len(split_custom(400000, [(1, 150000), (2, 100000), (3, 150000)])), 3)
        with self.assertRaisesMessage(SplitError, "left to assign"):
            split_custom(400000, [(1, 150000), (2, 100000)])
        with self.assertRaisesMessage(SplitError, "too much"):
            split_custom(100, [(1, 150)])

    def test_percentage_split_must_total_100(self):
        shares = split_percentage(400000, [(1, Decimal("50")), (2, Decimal("25")), (3, Decimal("25"))])
        self.assertEqual([s[1] for s in shares], [200000, 100000, 100000])
        with self.assertRaisesMessage(SplitError, "100%"):
            split_percentage(400000, [(1, Decimal("50")), (2, Decimal("40"))])

    def test_percentage_rounding_still_adds_up(self):
        shares = split_percentage(10000, [(1, Decimal("33.33")), (2, Decimal("33.33")), (3, Decimal("33.34"))])
        self.assertEqual(sum(s[1] for s in shares), 10000)

    def test_duplicates_and_empty_rejected(self):
        with self.assertRaises(SplitError):
            split_equal(100, [])
        with self.assertRaises(SplitError):
            split_equal(100, [1, 1])


class ExpenseApiTests(APITestCase):
    def setUp(self):
        self.utsuk = make_user("Utsuk", "9812345678")
        self.ram = make_user("Ram", "9800000001")
        self.sita = make_user("Sita", "9800000002")
        self.outsider = make_user("Outsider", "9800000009")
        self.group = make_group(self.utsuk, [self.ram, self.sita])
        self.client = client_for(self.utsuk)

    def test_equal_expense_creates_splits_and_notifies(self):
        data = add_expense(self.utsuk, self.group, "3000", [self.utsuk, self.ram, self.sita], description="Hotel")
        self.assertEqual([s["amount"] for s in data["splits"]], ["1000.00"] * 3)
        self.assertEqual(Decimal(data["my_share"]), Decimal("1000.00"))
        notes = client_for(self.ram).get("/api/notifications/").data
        self.assertEqual(notes["unread_count"], 2)  # added to group + expense
        self.assertIn("You owe Rs. 1,000", notes["results"][0]["message"])

    def test_custom_and_percentage_via_api(self):
        res = self.client.post("/api/expenses/", {
            "group": self.group, "description": "Taxi", "amount": "4000", "category": "transport",
            "paid_by": self.ram.pk, "split_method": "custom",
            "splits": [{"user": self.utsuk.pk, "amount": "1500"}, {"user": self.ram.pk, "amount": "1000"},
                       {"user": self.sita.pk, "amount": "1500"}],
        }, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        res = self.client.post("/api/expenses/", {
            "group": self.group, "description": "Food", "amount": "4000", "paid_by": self.utsuk.pk,
            "split_method": "percentage",
            "splits": [{"user": self.utsuk.pk, "percentage": "50"}, {"user": self.ram.pk, "percentage": "30"}],
        }, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("100%", str(res.data))

    def test_preview_does_not_save(self):
        res = self.client.post("/api/expenses/preview/", {
            "group": self.group, "description": "Dinner", "amount": "3600", "paid_by": self.utsuk.pk,
            "participants": [self.utsuk.pk, self.ram.pk, self.sita.pk],
        }, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["my_share"], Decimal("1200.00"))
        self.assertEqual(res.data["my_balance_effect"], Decimal("2400.00"))
        self.assertEqual(self.client.get("/api/expenses/", {"group": self.group}).data, [])

    def test_participants_must_be_members(self):
        res = self.client.post("/api/expenses/", {
            "group": self.group, "description": "x", "amount": "100", "paid_by": self.utsuk.pk,
            "participants": [self.utsuk.pk, self.outsider.pk],
        }, format="json")
        self.assertEqual(res.status_code, 400)

    def test_outsider_cannot_see_or_add(self):
        add_expense(self.utsuk, self.group, "300", [self.utsuk, self.ram])
        other = client_for(self.outsider)
        self.assertEqual(other.get("/api/expenses/").data, [])
        res = other.post("/api/expenses/", {
            "group": self.group, "description": "x", "amount": "100", "paid_by": self.outsider.pk,
            "participants": [self.outsider.pk]}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_edit_and_delete_permissions(self):
        exp = add_expense(self.utsuk, self.group, "300", [self.utsuk, self.ram, self.sita])
        sita = client_for(self.sita)
        self.assertEqual(sita.patch(f"/api/expenses/{exp['id']}/", {"description": "Hack"}, format="json").status_code, 403)
        res = self.client.patch(f"/api/expenses/{exp['id']}/", {"amount": "600", "participants": [self.utsuk.pk, self.ram.pk]}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual([s["amount"] for s in res.data["splits"]], ["300.00", "300.00"])
        self.assertEqual(self.client.delete(f"/api/expenses/{exp['id']}/").status_code, 204)

    def test_receipt_upload(self):
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        exp = add_expense(self.utsuk, self.group, "300", [self.utsuk, self.ram])
        buf = io.BytesIO()
        Image.new("RGB", (40, 60), "white").save(buf, "JPEG")
        upload = SimpleUploadedFile("bill.jpg", buf.getvalue(), content_type="image/jpeg")
        res = self.client.post(f"/api/expenses/{exp['id']}/receipt/", {"receipt": upload}, format="multipart")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertIn("/media/receipts/", res.data["receipt"])
        bad = SimpleUploadedFile("x.jpg", b"not an image", content_type="image/jpeg")
        self.assertEqual(self.client.post(f"/api/expenses/{exp['id']}/receipt/", {"receipt": bad}, format="multipart").status_code, 400)
        self.assertEqual(self.client.delete(f"/api/expenses/{exp['id']}/receipt/").data["receipt"], None)
