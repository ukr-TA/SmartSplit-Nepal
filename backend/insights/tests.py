"""Tests for the machine-learning endpoints.

They cover both paths on purpose: with the trained artefacts present (the normal case) and
with them missing (a fresh clone where the notebook has not been run). The API must behave
sensibly either way.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from common.testing import add_expense, client_for, make_group, make_user

from . import predictor


class CategorySuggestionTests(TestCase):
    def setUp(self):
        self.user = make_user("Utsuk Kharel", "9812345678")
        self.client = client_for(self.user)
        predictor.reset_cache()

    def tearDown(self):
        predictor.reset_cache()

    def post(self, **payload):
        return self.client.post("/api/ml/suggest-category/", payload, format="json")

    def test_requires_authentication(self):
        response = APIClient().post(
            "/api/ml/suggest-category/", {"description": "Momo"}, format="json"
        )
        self.assertEqual(response.status_code, 401)

    def test_suggests_a_valid_category_with_confidence(self):
        response = self.post(description="Momo at Everest Momo Center", amount="450")
        self.assertEqual(response.status_code, 200)
        body = response.data
        self.assertIn(body["category"], predictor.CATEGORIES)
        self.assertGreaterEqual(body["confidence"], 0.0)
        self.assertLessEqual(body["confidence"], 1.0)
        self.assertIn(body["source"], {"model", "keyword"})

    def test_alternatives_are_ranked_below_the_top_choice(self):
        response = self.post(description="Tourist bus ticket to Pokhara", amount="1400")
        body = response.data
        for alternative in body["alternatives"]:
            self.assertIn(alternative["category"], predictor.CATEGORIES)
            self.assertLessEqual(alternative["confidence"], body["confidence"])

    def test_blank_description_is_handled(self):
        response = self.post(description="", amount="100")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["source"], "empty")
        self.assertEqual(response.data["category"], "other")

    def test_amount_is_optional(self):
        self.assertEqual(self.post(description="NEA bijuli bill").status_code, 200)

    def test_rejects_a_negative_amount(self):
        self.assertEqual(self.post(description="Momo", amount="-50").status_code, 400)

    @override_settings(ML_MODELS_DIR="/nonexistent/models")
    def test_falls_back_to_keywords_when_the_model_is_missing(self):
        predictor.reset_cache()
        response = self.post(description="NEA bijuli bill Bhadra", amount="1800")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["source"], "keyword")
        self.assertEqual(response.data["category"], "utilities")

    @override_settings(ML_MODELS_DIR="/nonexistent/models")
    def test_keyword_fallback_recognises_common_nepali_wording(self):
        predictor.reset_cache()
        cases = {
            "Momo and chiya": "food",
            "Sajha bus fare": "transport",
            "Room rent Poush": "rent",
            "Semester fee": "education",
            "Movie at QFX": "entertainment",
        }
        for description, expected in cases.items():
            with self.subTest(description=description):
                self.assertEqual(
                    predictor.suggest_category(description)["category"], expected
                )


class ModelInfoTests(TestCase):
    def setUp(self):
        self.client = client_for(make_user("Info User", "9812345670"))
        predictor.reset_cache()

    def test_reports_availability_and_categories(self):
        response = self.client.get("/api/ml/info/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["categories"], predictor.CATEGORIES)
        self.assertIn("classifier_available", response.data)
        self.assertIn("forecaster_available", response.data)


class MonthlyHistoryTests(TestCase):
    def test_groups_by_month_and_fills_gaps(self):
        rows = [
            (date(2026, 1, 5), Decimal("1000")),
            (date(2026, 1, 20), Decimal("500")),
            (date(2026, 3, 2), Decimal("700")),
        ]
        history = predictor.monthly_history(rows)
        self.assertEqual([row["month"] for row in history], ["2026-01", "2026-02", "2026-03"])
        self.assertEqual(history[0]["total"], 1500.0)
        self.assertEqual(history[0]["count"], 2)
        self.assertEqual(history[1]["total"], 0.0)  # February had no expenses

    def test_empty_input(self):
        self.assertEqual(predictor.monthly_history([]), [])


class ForecastTests(TestCase):
    def setUp(self):
        self.owner = make_user("Utsuk Kharel", "9812345678")
        self.friend = make_user("Ram Sharma", "9800000001")
        self.client = client_for(self.owner)
        self.group_id = make_group(self.owner, [self.friend])
        predictor.reset_cache()

    def url(self):
        return f"/api/groups/{self.group_id}/forecast/"

    def test_not_ready_until_there_is_enough_history(self):
        add_expense(self.owner, self.group_id, "500.00", [self.owner, self.friend])
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["ready"])
        self.assertIn("months", response.data["reason"])

    def test_predicts_once_enough_months_exist(self):
        today = date.today().replace(day=1)
        for months_ago in range(6, 0, -1):
            when = today - timedelta(days=30 * months_ago)
            add_expense(
                self.owner, self.group_id, "2000.00", [self.owner, self.friend],
                description=f"Expense {months_ago}", date=when.isoformat(),
            )
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["ready"])
        self.assertGreater(response.data["predicted_total"], 0)
        self.assertLessEqual(response.data["lower"], response.data["predicted_total"])
        self.assertGreaterEqual(response.data["upper"], response.data["predicted_total"])
        self.assertIn(response.data["source"], {"model", "fallback"})
        self.assertGreaterEqual(len(response.data["history"]), 4)

    def test_non_members_cannot_see_the_forecast(self):
        outsider = make_user("Outsider", "9800000099")
        response = client_for(outsider).get(self.url())
        self.assertIn(response.status_code, (403, 404))

    @override_settings(ML_MODELS_DIR="/nonexistent/models")
    def test_falls_back_to_a_three_month_average(self):
        predictor.reset_cache()
        history = [
            {"month": "2026-01", "total": 10000.0, "count": 5},
            {"month": "2026-02", "total": 12000.0, "count": 6},
            {"month": "2026-03", "total": 14000.0, "count": 7},
            {"month": "2026-04", "total": 16000.0, "count": 8},
        ]
        result = predictor.forecast_group_spending(history, "roommates")
        self.assertTrue(result["ready"])
        self.assertEqual(result["source"], "fallback")
        self.assertAlmostEqual(result["predicted_total"], 14000.0, places=2)
        self.assertEqual(result["month"], "2026-05")


class ForecastExplanationTests(TestCase):
    """The forecast card explains itself; these check the explanation is right, not just present."""

    def setUp(self):
        predictor.reset_cache()

    def history(self, last_month="2026-09", months=13, total=40000.0):
        year, month = (int(p) for p in last_month.split("-"))
        rows = []
        for back in range(months - 1, -1, -1):
            y, m = year, month - back
            while m <= 0:
                m += 12
                y -= 1
            rows.append({"month": f"{y:04d}-{m:02d}", "total": total, "count": 10,
                         "categories": {"rent": total * 0.6, "food": total * 0.3, "utilities": total * 0.1}})
        return rows

    def test_explanation_names_the_festival_coming_next_month(self):
        result = predictor.forecast_group_spending(self.history("2026-09"), "roommates")
        explanation = result["explanation"]
        names = [event["name"] for event in explanation["events_next_month"]]
        self.assertEqual(result["month"], "2026-10")
        self.assertIn("Dashain", names)  # 11 to 25 October 2026
        self.assertTrue(any("Dashain" in reason for reason in explanation["reasons"]))

    def test_card_summary_is_one_or_two_short_sentences(self):
        summary = predictor.forecast_group_spending(self.history("2026-09"), "roommates")["explanation"]["summary"]
        sentences = [part for part in summary.replace("Rs.", "Rs").split(". ") if part.strip()]
        self.assertLessEqual(len(sentences), 2)
        self.assertIn("mostly on rent", summary)
        self.assertIn("might", summary)
        self.assertIn("Dashain", summary)
        self.assertNotIn(" will ", f" {summary} ")

    def test_explanation_describes_this_months_spending(self):
        explanation = predictor.forecast_group_spending(self.history(), "roommates")["explanation"]
        top = explanation["this_month"]["top_categories"]
        self.assertEqual(top[0]["category"], "rent")
        self.assertAlmostEqual(top[0]["share"], 0.6, places=2)
        self.assertIn("mostly on rent", explanation["reasons"][0])
        self.assertIn(explanation["direction"], {"up", "down", "same"})
        self.assertTrue(explanation["headline"].startswith("October might cost around Rs."))
        # Forecasts are always worded as possibilities, never as certainties.
        for text in [explanation["headline"], *explanation["reasons"]]:
            self.assertNotIn(" will ", f" {text} ")

    def test_explanation_mentions_the_same_month_last_year(self):
        explanation = predictor.forecast_group_spending(self.history(months=13), "roommates")["explanation"]
        self.assertEqual(explanation["same_month_last_year"], 40000.0)
        self.assertTrue(any(reason.startswith("Last October") for reason in explanation["reasons"]))

    def test_a_month_without_major_festivals_is_described_as_such(self):
        # History ending in June 2026 -> forecast for July 2026, which has no major festival.
        explanation = predictor.forecast_group_spending(self.history("2026-06"), "roommates")["explanation"]
        self.assertFalse([e for e in explanation["events_next_month"] if e["scale"] == "major"])

    def test_a_running_month_is_projected_to_a_full_month(self):
        history = self.history("2026-09")
        history[-1]["total"] = 20000.0  # only part of September recorded so far
        result = predictor.forecast_group_spending(history, "roommates", today=date(2026, 9, 15))
        this_month = result["explanation"]["this_month"]
        self.assertTrue(this_month["partial"])
        self.assertGreater(this_month["projected_total"], 20000.0)
        self.assertIn("so far", result["explanation"]["reasons"][0])

    @override_settings(ML_MODELS_DIR="/nonexistent/models")
    def test_fallback_says_it_is_an_average(self):
        predictor.reset_cache()
        explanation = predictor.forecast_group_spending(self.history(), "roommates")["explanation"]
        self.assertTrue(any("average of your last three months" in reason for reason in explanation["reasons"]))

    def test_rupee_formatting_uses_lakh_grouping(self):
        self.assertEqual(predictor._npr(125000), "Rs. 1,25,000")
        self.assertEqual(predictor._npr(66256.4), "Rs. 66,256")
        self.assertEqual(predictor._npr(950), "Rs. 950")
