"""
Serving layer for the two models trained in ``ml/notebooks/smartsplit_ml.ipynb``.

Design notes
------------
* Models are loaded **lazily** the first time a request needs them and then kept in memory,
  so importing this module never costs anything at startup.
* If the ``.joblib`` files are missing (a fresh clone where the notebook has not been run,
  or a deployment that excludes them), every function falls back to a keyword rule. The API
  keeps working and simply reports ``source="keyword"`` instead of ``source="model"``.
* Nothing here touches the database. The views pass in plain values, which keeps the
  prediction code easy to unit-test.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from django.conf import settings

CATEGORIES = [
    "food", "transport", "hotel", "entertainment", "shopping",
    "education", "utilities", "rent", "other",
]

# Fallback used when the trained model is unavailable. Deliberately small and readable.
KEYWORDS: dict[str, tuple[str, ...]] = {
    "food": ("momo", "khaja", "chiya", "tea", "lunch", "dinner", "breakfast", "restaurant",
             "thakali", "dal", "bhat", "sekuwa", "grocery", "tarkari", "vegetable", "pizza",
             "cafe", "snack", "chowmein", "cake", "milk", "meat", "chicken"),
    "transport": ("bus", "taxi", "petrol", "fuel", "pathao", "indrive", "micro", "sajha",
                  "ticket", "jeep", "flight", "fare", "scooter", "bike", "cab", "ride"),
    "hotel": ("hotel", "resort", "lodge", "guest house", "homestay", "room booking", "hostel bed",
              "check in", "check out"),
    "entertainment": ("movie", "cinema", "qfx", "ticket show", "paragliding", "boating", "concert",
                      "futsal", "netflix", "spotify", "game", "safari", "zipline", "bungee", "park"),
    "shopping": ("shopping", "shoes", "clothes", "kurta", "saree", "jacket", "daraz", "bhatbhateni",
                 "gift", "mall", "headphone", "dress", "shirt"),
    "education": ("fee", "semester", "exam", "college", "school", "book", "course", "class",
                  "tuition", "admission", "lab", "photocopy", "ielts", "stationery"),
    "utilities": ("bill", "electricity", "bijuli", "nea", "water", "khanepani", "gas", "cylinder",
                  "lpg", "internet", "wifi", "worldlink", "vianet", "ntc", "ncell", "recharge",
                  "data pack", "dish"),
    "rent": ("rent", "landlord", "flat", "room rent", "advance", "parking rent"),
}

MIN_FORECAST_MONTHS = 4

# The notebook trains on households spending tens of thousands of rupees a month. A real group
# in the app can be much smaller, so the served prediction is clamped to this band around the
# group's own three-month average. The clamp is recorded in the model bundle as well.
DEFAULT_SERVING_CLAMP = (0.6, 1.6)


def models_dir() -> Path:
    return Path(getattr(settings, "ML_MODELS_DIR", Path(settings.BASE_DIR).parent / "ml" / "models"))


def clean(text: str) -> str:
    """Same normalisation as the notebook: lower case, letters only."""
    text = re.sub(r"[^a-z\s]", " ", str(text).lower())
    return re.sub(r"\s+", " ", text).strip()


def amount_band(amount: float | None) -> str:
    """Coarse amount token, matching ``bucket()`` in the notebook."""
    if amount is None:
        return "amt_mid"
    if amount < 200:
        return "amt_tiny"
    if amount < 1000:
        return "amt_small"
    if amount < 5000:
        return "amt_mid"
    if amount < 20000:
        return "amt_large"
    return "amt_huge"


@dataclass
class _Cache:
    classifier: dict | None = None
    forecaster: dict | None = None
    loaded: set[str] = field(default_factory=set)


_CACHE = _Cache()


def _load(name: str) -> dict | None:
    """Load a joblib artefact once. Any failure disables that model, it never breaks a request."""
    if name in _CACHE.loaded:
        return getattr(_CACHE, name)
    _CACHE.loaded.add(name)

    path = models_dir() / ("category_clf.joblib" if name == "classifier" else "spend_forecast.joblib")
    if not path.exists():
        return None
    try:
        import joblib

        setattr(_CACHE, name, joblib.load(path))
    except Exception:  # noqa: BLE001 - a broken artefact must not take the API down
        setattr(_CACHE, name, None)
    return getattr(_CACHE, name)


def reset_cache() -> None:
    """Used by tests, and after retraining without a restart."""
    _CACHE.classifier = None
    _CACHE.forecaster = None
    _CACHE.loaded.clear()


# ----------------------------------------------------------------------------------
# 1. Category suggestion
# ----------------------------------------------------------------------------------
def _keyword_category(description: str) -> tuple[str, float]:
    text = f" {clean(description)} "
    best, hits = "other", 0
    for category, words in KEYWORDS.items():
        count = sum(1 for word in words if f" {word} " in text or text.strip().startswith(word))
        if count > hits:
            best, hits = category, count
    return best, (0.55 if hits else 0.2)


def suggest_category(description: str, amount: float | None = None, top: int = 3) -> dict:
    """Predict the expense category for a free-text description.

    Returns the best category, its confidence in 0..1, the next best alternatives, and
    whether the answer came from the trained model or the keyword fallback.
    """
    description = (description or "").strip()
    if not description:
        return {"category": "other", "confidence": 0.0, "alternatives": [], "source": "empty"}

    bundle = _load("classifier")
    if bundle is None:
        category, confidence = _keyword_category(description)
        return {"category": category, "confidence": confidence, "alternatives": [],
                "source": "keyword"}

    text = clean(description)
    if bundle.get("uses_amount"):
        text = f"{text} {amount_band(amount)}"

    pipeline = bundle["pipeline"]
    probabilities = pipeline.predict_proba([text])[0]
    labels = list(pipeline.classes_)
    ranked = sorted(zip(labels, probabilities), key=lambda pair: pair[1], reverse=True)

    return {
        "category": ranked[0][0],
        "confidence": round(float(ranked[0][1]), 4),
        "alternatives": [
            {"category": label, "confidence": round(float(score), 4)}
            for label, score in ranked[1:top]
        ],
        "source": "model",
    }


# ----------------------------------------------------------------------------------
# 2. Monthly spending forecast
# ----------------------------------------------------------------------------------
def _month_key(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def _next_month(key: str) -> str:
    year, month = (int(part) for part in key.split("-"))
    return f"{year + (month // 12):04d}-{month % 12 + 1:02d}"


MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August",
               "September", "October", "November", "December"]
CATEGORY_LABELS = {
    "food": "food", "transport": "transport", "hotel": "hotels", "entertainment": "entertainment",
    "shopping": "shopping", "education": "education", "utilities": "bills and utilities",
    "rent": "rent", "other": "other things",
}


def _month_name(key: str) -> str:
    return MONTH_NAMES[int(key.split("-")[1]) - 1]


def _npr(value: float) -> str:
    """Rs. 1,25,000 style, matching the rest of the app."""
    number = f"{int(round(value))}"
    if len(number) > 3:
        head, tail = number[:-3], number[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        number = ",".join(groups + [tail])
    return f"Rs. {number}"


def _short_date(iso: str) -> str:
    year, month, day = (int(part) for part in iso.split("-"))
    return f"{day} {MONTH_NAMES[month - 1][:3]}"


def _naive_forecast(history: list[dict]) -> float:
    """Average of the last three months. Used when no trained model is available."""
    recent = [row["total"] for row in history[-3:]]
    return sum(recent) / len(recent)


def _calendar_value(mapping: dict[str, float], key: str) -> float:
    """Festival intensity for a month; outside the calendar, the same month's average."""
    if key in mapping:
        return mapping[key]
    same_month = [value for month, value in mapping.items() if month[5:] == key[5:]]
    return sum(same_month) / len(same_month) if same_month else 0.0


def _events(bundle: dict | None, key: str) -> list[dict]:
    """Festivals touching a month that matter to spending, biggest first."""
    if not bundle:
        return []
    events = bundle.get("festivals", {}).get(key, [])
    if not events:
        # Beyond the calendar: reuse the same month from the latest year we know.
        candidates = sorted(month for month in bundle.get("festivals", {}) if month[5:] == key[5:])
        events = bundle["festivals"][candidates[-1]] if candidates else []
    rank = {"major": 0, "medium": 1, "minor": 2}
    return sorted(events, key=lambda e: (rank.get(e["scale"], 3), -e["national_weight"], e["peak"]))


def forecast_group_spending(history: list[dict], group_type: str = "custom",
                            today: date | None = None) -> dict:
    """Predict next month's total for one group, and explain the prediction.

    ``history`` is an ordered list of ``{"month": "YYYY-MM", "total": float, "count": int,
    "categories": {category: amount}}``, oldest first, with no gaps (see :func:`monthly_history`).
    If the last month is the current month it is not over yet: the remaining days are filled in
    at the group's recent daily rate before it is used as "last month" by the model.
    """
    public_history = [{k: row[k] for k in ("month", "total", "count")} for row in history]
    if len(history) < MIN_FORECAST_MONTHS:
        return {
            "ready": False,
            "reason": f"Needs at least {MIN_FORECAST_MONTHS} months of expenses "
                      f"({len(history)} so far).",
            "history": public_history,
        }

    last = history[-1]
    target_month = _next_month(last["month"])
    month_number = int(target_month.split("-")[1])
    bundle = _load("forecaster")

    totals = [row["total"] for row in history]
    complete_average = sum(totals[-4:-1]) / 3 if len(totals) >= 4 else sum(totals[-3:]) / 3

    # Is the latest month still running?
    partial, projected_last = False, last["total"]
    if today is not None and last["month"] == _month_key(today):
        year, month = today.year, today.month
        days_in_month = (date(year + month // 12, month % 12 + 1, 1) - date(year, month, 1)).days
        elapsed = today.day / days_in_month
        if elapsed < 1:
            partial = True
            projected_last = max(last["total"], last["total"] + (1 - elapsed) * complete_average)
            totals[-1] = projected_last

    recent_average = sum(totals[-3:]) / 3
    raw_prediction, clamped = None, False

    if bundle is None:
        prediction = _naive_forecast([{"total": value} for value in totals])
        model_name = "Average of last 3 months (fallback)"
        source = "fallback"
    else:
        try:
            import pandas as pd

            intensity = bundle.get("festival_intensity", {})
            features = {
                "lag_1": totals[-1],
                "lag_2": totals[-2],
                "lag_3": totals[-3],
                "rolling_3": recent_average,
                "lag_12": totals[-12] if len(totals) >= 12 else recent_average,
                "has_lag_12": 1 if len(totals) >= 12 else 0,
                "festival_intensity": _calendar_value(intensity, target_month),
                "intensity_lag_1": _calendar_value(intensity, last["month"]),
                "festival_month": 1 if month_number in (10, 11) else 0,
                "month_sin": math.sin(2 * math.pi * month_number / 12),
                "month_cos": math.cos(2 * math.pi * month_number / 12),
            }
            for column in bundle.get("group_columns", []):
                features[column] = 1 if column == f"grp_{group_type}" else 0

            frame = pd.DataFrame([features])[bundle["features"]]
            raw_prediction = float(bundle["model"].predict(frame)[0])
            prediction = raw_prediction

            # Keep the answer anchored to this group's own scale (see DEFAULT_SERVING_CLAMP).
            low, high = bundle.get("serving_clamp", DEFAULT_SERVING_CLAMP)
            if recent_average > 0:
                bounded = min(max(prediction, low * recent_average), high * recent_average)
                clamped = abs(bounded - prediction) > 1
                prediction = bounded

            model_name = bundle.get("model_name", "regression")
            source = "model"
        except Exception:  # noqa: BLE001 - fall back rather than fail the request
            prediction = _naive_forecast([{"total": value} for value in totals])
            model_name = "Average of last 3 months (fallback)"
            source = "fallback"
            raw_prediction, clamped = None, False

    prediction = max(0.0, prediction)
    # The notebook reports a mean absolute percentage error of roughly 40% on held-out months,
    # so the app shows a band rather than a single number it cannot justify.
    margin = 0.4
    explanation = explain_forecast(
        history=history, target_month=target_month, prediction=prediction,
        recent_average=recent_average, partial=partial, projected_last=projected_last,
        bundle=bundle, source=source, raw_prediction=raw_prediction, clamped=clamped,
    )
    return {
        "ready": True,
        "month": target_month,
        "predicted_total": round(prediction, 2),
        "lower": round(prediction * (1 - margin), 2),
        "upper": round(prediction * (1 + margin), 2),
        "model": model_name,
        "source": source,
        "history": public_history,
        "explanation": explanation,
    }


def explain_forecast(*, history, target_month, prediction, recent_average, partial,
                     projected_last, bundle, source, raw_prediction, clamped) -> dict:
    """Plain-language reasons for a forecast.

    These are the inputs the model actually receives - the group's recent months, the same month
    last year, the festival calendar - described in words. They explain what the forecast is
    based on; they are not an exact breakdown of how the model weighed each one.
    """
    last = history[-1]
    this_name, next_name = _month_name(last["month"]), _month_name(target_month)

    categories = sorted((last.get("categories") or {}).items(), key=lambda item: item[1], reverse=True)
    spent = last["total"]
    top = [
        {"category": name, "amount": round(value, 2), "share": round(value / spent, 3) if spent else 0}
        for name, value in categories[:3] if value > 0
    ]

    change = (prediction - recent_average) / recent_average if recent_average > 0 else 0.0
    direction = "up" if change > 0.08 else "down" if change < -0.08 else "same"

    next_events = [e for e in _events(bundle, target_month) if e["scale"] != "minor" or e["national_weight"] > 0]
    this_events = [e for e in _events(bundle, last["month"]) if e["scale"] != "minor" or e["national_weight"] > 0]
    next_keys = {e["key"] for e in next_events}
    ending = [e for e in this_events if e["key"] not in next_keys and e["scale"] in ("major", "medium")]

    reasons: list[str] = []

    # 1. What happened this month.
    so_far = " so far" if partial else ""
    if top:
        parts = [f"{CATEGORY_LABELS.get(t['category'], t['category'])} ({round(t['share'] * 100)}%)" for t in top]
        joined = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
        reasons.append(f"This group has spent {_npr(spent)} in {this_name}{so_far}, mostly on {joined}.")
    else:
        reasons.append(f"This group has spent {_npr(spent)} in {this_name}{so_far}.")
    if partial:
        reasons.append(
            f"{this_name} isn't over yet, so the rest of the month is counted at your recent daily rate: "
            f"it could end somewhere near {_npr(projected_last)}."
        )

    # 2. What is coming next month.
    if next_events:
        described = []
        for event in next_events[:3]:
            dates = _short_date(event["start"]) if event["start"] == event["end"] \
                else f"{_short_date(event['start'])} to {_short_date(event['end'])}"
            text = f"{event['name']} ({dates})"
            if event.get("spending"):
                text += f", which often brings {event['spending']}"
            described.append(text)
        reasons.append(f"{next_name} has " + "; ".join(described) + ".")
    else:
        reasons.append(f"{next_name} has no major festival in the Nepali calendar.")

    # 3. What is ending.
    if ending:
        names = " and ".join(e["name"] for e in ending[:2])
        reasons.append(f"{this_name} had {names}, which won't come round again in {next_name}.")

    # 4. Same month last year.
    if len(history) >= 12:
        last_year = history[-12]
        reasons.append(f"Last {next_name}, this group spent {_npr(last_year['total'])}.")

    # 5. Honesty about the model.
    if source == "fallback":
        reasons.append("No trained model is available, so this estimate is simply the average of your last three months.")
    elif clamped and raw_prediction is not None:
        reasons.append(
            f"The model's own estimate was {_npr(raw_prediction)}, but it is kept within "
            f"{'1.6×' if raw_prediction > prediction else '0.6×'} your recent average, because this group "
            "is smaller than the households the model learned from, so a jump that big is less likely here."
        )

    # The short version the card shows: one or two sentences, always worded as a possibility.
    main_event = next((e for e in next_events
                       if e["scale"] in ("major", "medium") and e["national_weight"] > 0), None)
    ending_event = ending[0]["name"] if ending else None
    first_cat = CATEGORY_LABELS.get(top[0]["category"], top[0]["category"]) if top else None
    sentence_one = (f"You've spent {_npr(spent)} in {this_name}{so_far}"
                    + (f", mostly on {first_cat}." if first_cat else "."))
    if main_event:
        start, end = main_event["start"], main_event["end"]
        if not (main_event["scale"] == "major" or main_event["key"].startswith("wedding")):
            start = end = main_event["peak"]  # a one-day festival: give its main day
        if start == end:
            span = _short_date(start)
        elif start[:7] == end[:7]:
            span = f"{_short_date(start).split()[0]}\u2013{_short_date(end)}"
        else:
            span = f"{_short_date(start)} \u2013 {_short_date(end)}"
        # Keep "11–25 Oct" together on one line.
        span = span.replace(" \u2013 ", "\u00a0\u2013 ").replace("\u2013", "\u2060\u2013\u2060").replace(" ", "\u00a0")
        event_name = main_event["name"]
        if main_event["key"].startswith("wedding"):
            event_name = "the " + event_name.replace("Wedding season (", "").rstrip(")") + " wedding season"
    if direction == "up" and main_event:
        sentence_two = f"{next_name} might come in higher, around {_npr(prediction)}, with {event_name} on {span}."
    elif direction == "up":
        sentence_two = f"{next_name} might come in a little higher, around {_npr(prediction)}."
    elif direction == "down" and ending_event:
        sentence_two = f"{next_name} might be lighter, around {_npr(prediction)}, with {ending_event} behind you."
    elif direction == "down":
        sentence_two = f"{next_name} might be lighter, around {_npr(prediction)}, with no big festival coming."
    elif main_event:
        sentence_two = f"{next_name} might look much like usual, around {_npr(prediction)}, even with {event_name} on {span}."
    else:
        sentence_two = f"{next_name} might look much like usual, around {_npr(prediction)}."
    summary = f"{sentence_one} {sentence_two}"

    if direction == "up":
        headline = (f"{next_name} might cost around {_npr(prediction)}, possibly about "
                    f"{round(abs(change) * 100)}% more than your recent monthly average.")
    elif direction == "down":
        headline = (f"{next_name} might cost around {_npr(prediction)}, possibly about "
                    f"{round(abs(change) * 100)}% less than your recent monthly average.")
    else:
        headline = f"{next_name} might cost around {_npr(prediction)}, probably close to your usual month."

    return {
        "summary": summary,
        "headline": headline,
        "direction": direction,
        "change_vs_average": round(change, 4),
        "recent_average": round(recent_average, 2),
        "this_month": {"month": last["month"], "total": round(spent, 2), "partial": partial,
                       "projected_total": round(projected_last, 2), "top_categories": top},
        "events_next_month": [
            {k: e[k] for k in ("name", "start", "end", "peak", "scale", "spending")} for e in next_events[:4]
        ],
        "events_ending": [e["name"] for e in ending],
        "same_month_last_year": round(history[-12]["total"], 2) if len(history) >= 12 else None,
        "capped": bool(clamped),
        "reasons": reasons,
    }


def monthly_history(rows, months: int = 13) -> list[dict]:
    """Turn ``(date, amount[, category])`` rows into a gap-free monthly series, oldest first.

    Months with no expenses are included as zero, because the lag features assume a
    continuous series. Thirteen months are kept so "the same month last year" is available.
    """
    if not rows:
        return []

    buckets: dict[str, dict] = {}
    for row in rows:
        when, amount = row[0], float(row[1])
        category = row[2] if len(row) > 2 else None
        bucket = buckets.setdefault(_month_key(when), {"total": 0.0, "count": 0, "categories": {}})
        bucket["total"] += amount
        bucket["count"] += 1
        if category:
            bucket["categories"][category] = bucket["categories"].get(category, 0.0) + amount

    keys = sorted(buckets)
    filled, cursor = [], keys[0]
    while cursor <= keys[-1]:
        bucket = buckets.get(cursor, {"total": 0.0, "count": 0, "categories": {}})
        filled.append({"month": cursor, "total": round(bucket["total"], 2), "count": bucket["count"],
                       "categories": {k: round(v, 2) for k, v in bucket["categories"].items()}})
        cursor = _next_month(cursor)

    return filled[-months:]
