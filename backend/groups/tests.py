from rest_framework.test import APITestCase

from common.testing import add_expense, client_for, make_group, make_user


class GroupTests(APITestCase):
    def setUp(self):
        self.owner = make_user("Utsuk", "9812345678")
        self.ram = make_user("Ram", "9800000001")
        self.sita = make_user("Sita", "9800000002")
        self.stranger = make_user("Stranger", "9800000009")
        self.group = make_group(self.owner, [self.ram])
        self.client = client_for(self.owner)

    def test_create_sets_owner_and_trip_mode(self):
        data = self.client.get(f"/api/groups/{self.group}/").data
        self.assertEqual(data["my_role"], "owner")
        self.assertTrue(data["is_trip"])
        self.assertEqual(data["member_count"], 2)

    def test_dates_validated(self):
        res = self.client.post("/api/groups/", {"name": "Bad", "start_date": "2026-09-10",
                                                "end_date": "2026-09-01"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_non_members_cannot_see_group(self):
        other = client_for(self.stranger)
        self.assertEqual(other.get("/api/groups/").data, [])
        self.assertEqual(other.get(f"/api/groups/{self.group}/").status_code, 404)
        self.assertEqual(other.get(f"/api/groups/{self.group}/balances/").status_code, 404)

    def test_only_owner_can_edit_or_remove(self):
        ram = client_for(self.ram)
        self.assertEqual(ram.patch(f"/api/groups/{self.group}/", {"name": "X"}, format="json").status_code, 403)
        self.client.post(f"/api/groups/{self.group}/members/", {"user_id": self.sita.pk}, format="json")
        self.assertEqual(ram.delete(f"/api/groups/{self.group}/members/{self.sita.pk}/").status_code, 403)
        self.assertEqual(self.client.delete(f"/api/groups/{self.group}/members/{self.owner.pk}/").status_code, 400)
        self.assertEqual(self.client.delete(f"/api/groups/{self.group}/members/{self.sita.pk}/").status_code, 204)

    def test_add_member_twice_rejected(self):
        res = self.client.post(f"/api/groups/{self.group}/members/", {"user_id": self.ram.pk}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_cannot_remove_member_with_balance_or_delete_unsettled_group(self):
        add_expense(self.owner, self.group, "1000", [self.owner, self.ram])
        res = self.client.delete(f"/api/groups/{self.group}/members/{self.ram.pk}/")
        self.assertEqual(res.status_code, 400)
        self.assertIn("Rs. 500", str(res.data))
        self.assertEqual(self.client.delete(f"/api/groups/{self.group}/").status_code, 400)

    def test_member_can_leave_when_settled(self):
        self.assertEqual(client_for(self.ram).delete(f"/api/groups/{self.group}/members/{self.ram.pk}/").status_code, 204)

    def test_invite_and_join(self):
        invite = self.client.post(f"/api/groups/{self.group}/invite/").data
        self.assertEqual(len(invite["token"]), 10)
        # same active invite is reused
        self.assertEqual(self.client.post(f"/api/groups/{self.group}/invite/").data["token"], invite["token"])

        joiner = client_for(self.sita)
        preview = joiner.get(f"/api/groups/join/{invite['token'].lower()}/").data
        self.assertEqual(preview["group"]["name"], "Pokhara Trip")
        self.assertFalse(preview["already_member"])
        res = joiner.post(f"/api/groups/join/{invite['token']}/")
        self.assertEqual(res.status_code, 201)
        self.assertFalse(joiner.post(f"/api/groups/join/{invite['token']}/").data["joined"])
        activity = self.client.get(f"/api/groups/{self.group}/activity/").data
        self.assertEqual(activity[0]["action"], "member_joined")

        # regenerating invalidates the old link
        new = self.client.post(f"/api/groups/{self.group}/invite/", {"regenerate": True}, format="json").data
        self.assertNotEqual(new["token"], invite["token"])
        self.assertEqual(client_for(self.stranger).post(f"/api/groups/join/{invite['token']}/").status_code, 400)

    def test_activity_feed(self):
        add_expense(self.owner, self.group, "1000", [self.owner, self.ram], description="Momo")
        feed = client_for(self.ram).get("/api/activity/").data
        self.assertEqual(feed[0]["description"], "Utsuk added Momo")
        self.assertEqual(client_for(self.stranger).get("/api/activity/").data, [])
