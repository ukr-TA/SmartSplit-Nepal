from rest_framework.test import APIClient, APITestCase

from common.testing import client_for, make_user


class AuthTests(APITestCase):
    def register(self, **overrides):
        data = {
            "full_name": "Utsuk Kharel",
            "email": "utsuk@example.com",
            "phone_number": "9812345678",
            "password": "Str0ng!pass",
            **overrides,
        }
        return APIClient().post("/api/auth/register/", data, format="json")

    def test_register_returns_token_and_profile(self):
        res = self.register()
        self.assertEqual(res.status_code, 201)
        self.assertIn("token", res.data)
        self.assertEqual(res.data["user"]["phone_number"], "9812345678")

    def test_register_normalises_phone_with_country_code(self):
        res = self.register(phone_number="+977 981-234-5678")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["user"]["phone_number"], "9812345678")

    def test_register_rejects_invalid_or_duplicate_phone(self):
        self.assertEqual(self.register(phone_number="12345").status_code, 400)
        self.register()
        res = self.register(email="other@example.com")
        self.assertEqual(res.status_code, 400)
        self.assertIn("phone_number", res.data)

    def test_register_rejects_weak_password(self):
        res = self.register(password="password")
        self.assertEqual(res.status_code, 400)
        self.assertIn("password", res.data)

    def test_login_with_email_or_phone(self):
        self.register()
        client = APIClient()
        self.assertEqual(client.post("/api/auth/login/", {"identifier": "UTSUK@example.com", "password": "Str0ng!pass"}).status_code, 200)
        self.assertEqual(client.post("/api/auth/login/", {"identifier": "9812345678", "password": "Str0ng!pass"}).status_code, 200)
        self.assertEqual(client.post("/api/auth/login/", {"identifier": "9812345678", "password": "wrong"}).status_code, 400)

    def test_logout_invalidates_token(self):
        token = self.register().data["token"]
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(client.get("/api/profile/").status_code, 200)
        self.assertEqual(client.post("/api/auth/logout/").status_code, 204)
        self.assertEqual(client.get("/api/profile/").status_code, 401)

    def test_protected_endpoints_require_login(self):
        for url in ["/api/profile/", "/api/groups/", "/api/expenses/", "/api/dashboard/", "/api/settlements/"]:
            self.assertEqual(APIClient().get(url).status_code, 401, url)


class ProfileAndSearchTests(APITestCase):
    def setUp(self):
        self.me = make_user("Utsuk Kharel", "9812345678")
        self.ram = make_user("Ram Sharma", "9800000001")
        self.client = client_for(self.me)

    def test_update_profile(self):
        res = self.client.patch("/api/profile/", {"full_name": "Utsuk  K."}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["full_name"], "Utsuk K.")

    def test_cannot_take_someone_elses_phone(self):
        res = self.client.patch("/api/profile/", {"phone_number": "9800000001"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_profile_picture_upload(self):
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (20, 20), "teal").save(buf, "PNG")
        upload = SimpleUploadedFile("me.png", buf.getvalue(), content_type="image/png")
        res = self.client.patch("/api/profile/", {"profile_picture": upload}, format="multipart")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(res.data["profile_picture"].startswith("http"))
        self.me.refresh_from_db()
        self.me.profile_picture.delete()

    def test_search_by_full_phone_only(self):
        res = self.client.get("/api/users/search/", {"q": "9800000001"})
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["phone_number"], "98XXXX0001")
        self.assertNotIn("email", res.data["results"][0])
        # partial numbers do not list people
        self.assertEqual(len(self.client.get("/api/users/search/", {"q": "98000"}).data["results"]), 0)

    def test_search_by_name_and_email_excludes_self(self):
        self.assertEqual(len(self.client.get("/api/users/search/", {"q": "ram"}).data["results"]), 1)
        self.assertEqual(len(self.client.get("/api/users/search/", {"q": "ram.sharma@example.com"}).data["results"]), 1)
        self.assertEqual(len(self.client.get("/api/users/search/", {"q": "utsuk"}).data["results"]), 0)
