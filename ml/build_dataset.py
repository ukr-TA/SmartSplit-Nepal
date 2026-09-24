"""
Build the SmartSplit Nepal machine-learning dataset.

The dataset is *synthesised*, but it is not invented: every amount is drawn from
a price range in ``data/price_reference.csv``, which lists published Nepali
prices (NOC fuel and LPG rates, NEA tariff slabs, Kalimati wholesale vegetable
prices, ISP and telecom pack prices, published bus, cinema and hotel rates,
room-rent listings and college fee guides) together with the source of each one.
Descriptions use the vendor, place and item names a Nepali user would actually
type.

The year follows the real Nepali festival calendar (``data/festival_calendar.csv``,
built in ``festivals.py``): Dashain, Tihar, Chhath, Teej, Janai Purnima, Krishna
Janmashtami, Holi, Shivaratri, Nepali New Year, Buddha Jayanti, Maghe Sankranti,
the three Lhosars, Eid, Christmas, Mother's and Father's Day, Shree Panchami,
the Newar jatras and the wedding seasons, each on its actual date for that year.
Households celebrate according to a profile (a Newar family keeps Gai Jatra and
Yomari Punhi, a Madhesi family keeps Chhath, a Gurung student keeps Tamu Lhosar),
and every household has its own birthdays. Recurring bills, monsoon vegetable
prices, winter electricity use and semester fees are modelled as before.

Running this file twice produces exactly the same data (fixed seed).

    python ml/build_dataset.py

Outputs
-------
data/expenses.csv          one row per expense: date, description, amount, category, festival
data/monthly_spending.csv  monthly totals per household, used by the spending forecaster
data/households.csv        the 15 simulated households, their profile and birthdays
"""

from __future__ import annotations

import csv
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from festivals import (  # noqa: E402
    BIRTHDAY_ITEMS, FESTIVAL_SPENDING, WINDOW_UPLIFT, load_calendar, major_window_days,
    national_intensity_by_month, participation,
)

SEED = 20260924
DATA = Path(__file__).resolve().parent / "data"
START = date(2023, 10, 1)
MONTHS = 36

# --------------------------------------------------------------------------------------
# Vocabulary: real places, vendors and items
# --------------------------------------------------------------------------------------
KTM_AREAS = [
    "Baneshwor", "Kirtipur", "Thamel", "Lagankhel", "Koteshwor", "Patan", "Balkhu",
    "Kalanki", "Chabahil", "Jhamsikhel", "Maharajgunj", "Sundhara", "Bouddha", "Satdobato",
]
TRIP_PLACES = ["Pokhara", "Sauraha", "Nagarkot", "Bandipur", "Lumbini", "Ilam", "Dhulikhel", "Sarangkot"]
FOOD_VENDORS = [
    "Everest Momo Center", "Thakali Kitchen", "Newari khaja ghar", "Bajeko Sekuwa",
    "Momo Magic", "Roadhouse Cafe", "Himalayan Java", "Nanglo", "Bakery Cafe",
    "college canteen", "Chikusa cafe", "Trisara", "local bhojanalaya",
]
SHOPS = ["Bhatbhateni", "Big Mart", "Salesberry", "Civil Mall", "KL Tower", "Durbarmarg showroom", "Daraz"]
CINEMAS = ["QFX Civil Mall", "QFX Labim", "Big Movies", "One Cinemas", "Jai Nepal", "FCube Chhaya Center"]
NEP_MONTHS = ["Baishakh", "Jestha", "Asar", "Shrawan", "Bhadra", "Asoj", "Kartik", "Mangsir",
              "Poush", "Magh", "Falgun", "Chaitra"]

# --------------------------------------------------------------------------------------
# Templates: (description template, low, high)
# Ranges come from ml/data/price_reference.csv.
# --------------------------------------------------------------------------------------
TEMPLATES: dict[str, list[tuple[str, int, int]]] = {
    "food": [
        ("Momo at {food_vendor}", 120, 320),
        ("Chicken momo plate", 150, 280),
        ("Buff momo {area}", 90, 200),
        ("Thakali khana set {area}", 350, 700),
        ("Dal bhat at {food_vendor}", 250, 450),
        ("Lunch at {food_vendor}", 280, 900),
        ("Dinner {food_vendor}", 400, 1800),
        ("Newari khaja set", 350, 800),
        ("Sekuwa and chiura", 400, 1200),
        ("Chowmein and coke", 150, 350),
        ("Samosa chiya {area}", 60, 180),
        ("Chiya for everyone", 50, 220),
        ("Breakfast", 180, 600),
        ("Vegetables from Kalimati", 300, 1600),
        ("Tarkari kinne", 200, 900),
        ("Aalu pyaj golbheda", 250, 800),
        ("Grocery {shop}", 800, 6500),
        ("Monthly grocery", 3000, 12000),
        ("Chicken 1 kg", 420, 650),
        ("Milk and eggs", 150, 500),
        ("Birthday cake", 800, 2500),
        ("Pizza night", 700, 2200),
        ("Khaja", 80, 350),
        ("Cafe bill {area}", 300, 1400),
        ("Ice cream", 100, 500),
        ("Water jar", 60, 120),
    ],
    "transport": [
        ("Bus fare {area} to {area2}", 25, 60),
        ("Sajha bus to {area}", 25, 50),
        ("Micro to {area}", 30, 60),
        ("Taxi {area} to {area2}", 250, 800),
        ("Pathao ride", 120, 400),
        ("InDrive to {area}", 150, 500),
        ("Petrol", 500, 2500),
        ("Petrol 5 litre", 1000, 1050),
        ("Bike petrol {np_month}", 800, 3000),
        ("Tourist bus Kathmandu to Pokhara", 1200, 1600),
        ("Deluxe bus ticket to {trip}", 1200, 2000),
        ("Night bus tickets", 1400, 3400),
        ("Jeep to {trip}", 1500, 5000),
        ("Airport taxi", 700, 1500),
        ("Bus", 25, 200),
        ("Scooter servicing", 1200, 4000),
        ("Bike repair puncture", 150, 800),
        ("Cable car ticket", 700, 1000),
    ],
    "hotel": [
        ("Hotel {trip} 2 nights", 3000, 9000),
        ("Lakeside hotel booking", 1500, 6000),
        ("Guest house {trip}", 1200, 4000),
        ("Homestay {trip}", 1000, 3500),
        ("Room booking advance", 2000, 8000),
        ("Resort {trip} per night", 4000, 14000),
        ("Hostel dorm bed", 600, 1500),
        ("Hotel check out bill", 2500, 12000),
    ],
    "entertainment": [
        ("Movie ticket {cinema}", 300, 800),
        ("Movie tickets for 4", 1200, 2800),
        ("Paragliding Sarangkot", 11000, 12500),
        ("Boating Phewa lake", 600, 1200),
        ("Zipline {trip}", 2500, 4500),
        ("Bungee jump", 6000, 10000),
        ("Concert ticket", 1000, 3500),
        ("Futsal booking", 1200, 2400),
        ("Pool and snooker", 400, 1200),
        ("Netflix subscription split", 400, 1200),
        ("Spotify family", 300, 900),
        ("Park entry ticket", 100, 500),
        ("Chitwan jungle safari", 2500, 6000),
        ("Swimming pool entry", 500, 1200),
    ],
    "shopping": [
        ("Dashain kurta shopping", 2500, 12000),
        ("Tihar shopping {shop}", 2000, 9000),
        ("New shoes", 2500, 8000),
        ("Jacket {shop}", 3000, 9000),
        ("Daraz order", 800, 6000),
        ("Phone cover and screen guard", 500, 1800),
        ("Headphones", 1500, 8000),
        ("Gift for {name}", 1000, 5000),
        ("Kitchen utensils", 900, 4500),
        ("Bedsheet and pillow", 1200, 4000),
        ("Stationery and printing", 200, 1200),
        ("Laptop bag", 1500, 4000),
        ("Saree for mummy", 4000, 15000),
        ("Winter blanket", 2000, 6000),
    ],
    "education": [
        ("Semester fee {np_month}", 60000, 110000),
        ("Exam form fee", 1500, 6000),
        ("Admission fee instalment", 25000, 90000),
        ("Course book", 600, 3500),
        ("Photocopy of notes", 50, 400),
        ("IELTS class fee", 8000, 18000),
        ("Python course subscription", 1200, 5000),
        ("Lab fee", 1500, 6000),
        ("Project printing and binding", 400, 1800),
        ("College bus fee", 1200, 3000),
        ("Tuition fee monthly", 3000, 12000),
    ],
    "utilities": [
        ("NEA bijuli bill {np_month}", 700, 3200),
        ("Electricity bill", 700, 3500),
        ("Khanepani bill", 200, 900),
        ("Gas cylinder", 2050, 2060),
        ("LPG refill", 1900, 2100),
        ("Worldlink internet 3 months", 3300, 3900),
        ("Vianet renewal", 1000, 3900),
        ("Wifi bill", 800, 1200),
        ("NTC data pack", 29, 399),
        ("Ncell combo 399", 199, 699),
        ("Mobile recharge", 100, 600),
        ("Dish home recharge", 350, 900),
        ("Waste management fee", 150, 400),
    ],
    "rent": [
        ("Room rent {np_month}", 5000, 16000),
        ("Flat rent {area}", 12000, 34000),
        ("Rent {np_month}", 5000, 30000),
        ("Advance for new room", 10000, 40000),
        ("Hostel fee monthly", 8000, 18000),
        ("Parking rent", 500, 2000),
    ],
    "other": [
        ("Medicine from pharmacy", 200, 2500),
        ("Doctor visit", 500, 2000),
        ("Haircut", 200, 900),
        ("Temple donation", 100, 1000),
        ("Laundry", 200, 900),
        ("Photocopy", 20, 200),
        ("Emergency cash to {name}", 500, 5000),
        ("Bank charge", 50, 500),
        ("Insurance premium", 2000, 9000),
        ("Miscellaneous", 100, 2000),
        ("Repair work", 300, 3000),
    ],
}

# Descriptions that are genuinely ambiguous: the same wording is used in real life for more than
# one category. Each entry carries a probability distribution over categories, so the same text can
# appear with different labels. This puts a realistic ceiling on achievable accuracy (the Bayes
# error of the task) instead of letting the model learn a one-to-one template-to-label mapping.
AMBIGUOUS: list[tuple[str, dict[str, float], int, int]] = [
    ("Snacks during movie", {"food": 0.55, "entertainment": 0.45}, 200, 700),
    ("Popcorn and coke at {cinema}", {"entertainment": 0.6, "food": 0.4}, 350, 900),
    ("Canteen lunch at college", {"food": 0.75, "education": 0.25}, 100, 400),
    ("Hotel dinner {trip}", {"food": 0.6, "hotel": 0.4}, 600, 2500),
    ("Hotel bill with breakfast", {"hotel": 0.7, "food": 0.3}, 2000, 7000),
    ("Taxi to hotel", {"transport": 0.7, "hotel": 0.3}, 300, 900),
    ("Bus ticket and khaja on the way", {"transport": 0.6, "food": 0.4}, 300, 1200),
    ("Gas cylinder", {"utilities": 0.7, "shopping": 0.3}, 2050, 2060),
    ("Fruits for Dashain tika", {"food": 0.6, "shopping": 0.4}, 500, 2500),
    ("Dashain shopping", {"shopping": 0.75, "food": 0.25}, 2500, 10000),
    ("Room rent and wifi together", {"rent": 0.65, "utilities": 0.35}, 8000, 20000),
    ("College canteen chiya", {"food": 0.8, "education": 0.2}, 30, 150),
    ("Book shopping", {"education": 0.6, "shopping": 0.4}, 500, 3000),
    ("Trip contribution", {"other": 0.5, "transport": 0.25, "hotel": 0.25}, 1000, 6000),
    ("Grocery {shop}", {"food": 0.7, "shopping": 0.3}, 800, 6500),
    ("Water jar", {"food": 0.55, "utilities": 0.45}, 60, 120),
    ("Monthly bill paid", {"utilities": 0.5, "rent": 0.3, "other": 0.2}, 800, 12000),
    ("Paid for group", {"other": 0.4, "food": 0.35, "transport": 0.25}, 500, 4000),
    ("Stationery and printing", {"education": 0.6, "shopping": 0.4}, 200, 1200),
    ("Cab to airport with luggage", {"transport": 0.8, "other": 0.2}, 700, 1500),
]

NAMES = ["Ram", "Sita", "Hari", "Mina", "Bikash", "Anisha", "Sujan", "Prakriti", "dai", "bhai", "didi"]

# Free-text tails people add. They make the descriptions vary the way real entries do,
# and they deliberately make the classification task harder.
MODIFIERS: dict[str, list[str]] = {
    "food": ["with {name}", "for {n} people", "after class", "office lunch", "team khaja",
             "Saturday", "evening", "half plate", "veg", "takeaway", "extra chutney"],
    "transport": ["to college", "to office", "morning", "late night", "one way", "return",
                  "with {name}", "airport drop", "Ring Road", "shared"],
    "hotel": ["for {n} people", "advance paid", "2 rooms", "with breakfast", "weekend rate"],
    "entertainment": ["for {n} people", "with friends", "evening show", "weekend", "group booking"],
    "shopping": ["for {name}", "online", "sale price", "with cashback", "EMI", "for home"],
    "education": ["4th sem", "6th sem", "final year", "part payment", "late fee included"],
    "utilities": ["{np_month}", "shared 3 ways", "paid via eSewa", "paid by Khalti", "due date",
                  "last month", "advance"],
    "rent": ["{np_month}", "paid to landlord", "shared 2 ways", "with water charge", "advance"],
    "other": ["urgent", "for {name}", "cash", "reimburse later", "emergency"],
}

# How many independent households of each persona to simulate.
HOUSEHOLDS = 3

# Bills that repeat every month (or in fixed months) for a given household. Real households
# pay rent, electricity and internet on a schedule; only discretionary spending is random.
# Each entry: (description, category, low, high, months) - months=None means every month.
RECURRING: dict[str, list[tuple[str, str, int, int, tuple[int, ...] | None]]] = {
    "student_hostel": [
        ("Room rent {np_month}", "rent", 5000, 8000, None),
        ("NEA bijuli bill {np_month}", "utilities", 700, 1400, None),
        ("Wifi bill", "utilities", 800, 1200, None),
        ("NTC data pack", "utilities", 299, 399, None),
        ("Semester fee {np_month}", "education", 60000, 95000, (2, 8)),
    ],
    "student_home": [
        ("College bus fee", "transport", 1200, 2500, None),
        ("Ncell combo 399", "utilities", 199, 699, None),
        ("Tuition fee monthly", "education", 3000, 9000, None),
        ("Semester fee {np_month}", "education", 60000, 95000, (2, 8)),
    ],
    "working_bachelor": [
        ("Flat rent {area}", "rent", 12000, 22000, None),
        ("Electricity bill", "utilities", 900, 2200, None),
        ("Worldlink internet 3 months", "utilities", 1000, 1300, None),
        ("Gas cylinder", "utilities", 2050, 2060, (1, 3, 5, 7, 9, 11)),
    ],
    "family": [
        ("Rent {np_month}", "rent", 18000, 32000, None),
        ("NEA bijuli bill {np_month}", "utilities", 1200, 3200, None),
        ("Khanepani bill", "utilities", 200, 700, None),
        ("Wifi bill", "utilities", 900, 1200, None),
        ("Gas cylinder", "utilities", 2050, 2060, (1, 3, 5, 7, 9, 11)),
        ("School fee for {name}", "education", 4000, 12000, None),
    ],
    "trip_group": [],
}

PERSONAS = {
    # persona: (category weights, monthly expense count range)
    "student_hostel": ({"food": 46, "transport": 20, "education": 4, "utilities": 4, "rent": 0,
                        "entertainment": 10, "shopping": 10, "other": 5, "hotel": 1}, (14, 22)),
    "student_home": ({"food": 40, "transport": 20, "education": 5, "utilities": 4, "rent": 0,
                      "entertainment": 12, "shopping": 11, "other": 7, "hotel": 1}, (12, 20)),
    "working_bachelor": ({"food": 38, "transport": 18, "rent": 0, "utilities": 5, "shopping": 16,
                          "entertainment": 12, "other": 9, "education": 1, "hotel": 1}, (12, 20)),
    "family": ({"food": 44, "utilities": 6, "transport": 14, "shopping": 17, "education": 2,
                "rent": 0, "other": 10, "entertainment": 6, "hotel": 1}, (16, 26)),
    "trip_group": ({"hotel": 22, "food": 26, "transport": 24, "entertainment": 18, "shopping": 6,
                    "other": 4, "utilities": 0, "rent": 0, "education": 0}, (8, 16)),
}

GROUP_TYPE = {"student_hostel": "roommates", "student_home": "college", "working_bachelor": "roommates",
              "family": "family", "trip_group": "trip"}

# Which festivals each household keeps (see festivals.PROFILE_TAGS).
HOUSEHOLD_PROFILES = {
    "family_1": "hindu_hill", "family_2": "newar", "family_3": "madhesi",
    "student_hostel_1": "magar", "student_hostel_2": "tamang", "student_hostel_3": "hindu_hill",
    "student_home_1": "newar", "student_home_2": "gurung", "student_home_3": "muslim",
    "working_bachelor_1": "sherpa", "working_bachelor_2": "christian", "working_bachelor_3": "hindu_hill",
    "trip_group_1": "friends", "trip_group_2": "friends", "trip_group_3": "friends",
}


def seasonal_factor(day: date, category: str, major_days: set[date] | None = None) -> float:
    """Multiplier applied to amounts, reflecting documented seasonal behaviour.

    Festival purchases themselves are generated separately (see festivals.FESTIVAL_SPENDING);
    this only lifts *everyday* spending inside the Dashain and Tihar windows, on their real
    dates for that year.
    """
    factor = 1.0
    month = day.month
    if major_days and day in major_days:
        factor *= WINDOW_UPLIFT.get(category, 1.0)
    if month in (6, 7, 8) and category == "food":  # monsoon vegetable prices
        factor *= 1.18
    if month in (12, 1) and category == "utilities":  # winter heating load
        factor *= 1.25
    if month in (4, 5) and category == "entertainment":  # spring travel season
        factor *= 1.1
    return factor


def volume_factor(month: int, persona: str) -> float:
    """Multiplier applied to the *number* of expenses in a month."""
    factor = 1.0
    if month in (6, 7) and persona.startswith("student"):
        factor *= 0.85  # semester break
    if persona == "trip_group":
        factor *= {3: 1.4, 4: 1.6, 10: 1.7, 11: 1.3, 12: 1.2}.get(month, 0.6)
    return factor


def pick(rng: random.Random, weights: dict[str, int]) -> str:
    items = [k for k, v in weights.items() if v > 0]
    return rng.choices(items, weights=[weights[k] for k in items])[0]


def render(rng: random.Random, template: str, month: int, category: str) -> str:
    area, area2 = rng.sample(KTM_AREAS, 2)
    text = (
        template.replace("{area2}", area2)
        .replace("{area}", area)
        .replace("{trip}", rng.choice(TRIP_PLACES))
        .replace("{food_vendor}", rng.choice(FOOD_VENDORS))
        .replace("{shop}", rng.choice(SHOPS))
        .replace("{cinema}", rng.choice(CINEMAS))
        .replace("{name}", rng.choice(NAMES))
        .replace("{np_month}", NEP_MONTHS[(month + 8) % 12])
    )
    if rng.random() < 0.45:
        tail = rng.choice(MODIFIERS.get(category, ["cash"]))
        tail = (
            tail.replace("{name}", rng.choice(NAMES))
            .replace("{n}", str(rng.randint(2, 8)))
            .replace("{np_month}", NEP_MONTHS[(month + 8) % 12])
        )
        text = f"{text} {tail}" if rng.random() < 0.7 else f"{text} - {tail}"

    roll = rng.random()
    if roll < 0.10:  # people type in lower case
        text = text.lower()
    elif roll < 0.13:  # and sometimes in caps
        text = text.upper()
    if rng.random() < 0.05:  # and sometimes with a typo
        idx = rng.randrange(len(text))
        text = text[:idx] + text[idx + 1:]
    return text.strip()


def amount(rng: random.Random, low: int, high: int, factor: float) -> int:
    base = rng.uniform(low, high) * factor * rng.lognormvariate(0, 0.10)
    if base < 100:
        return max(10, int(round(base / 5) * 5))
    if base < 2000:
        return int(round(base / 10) * 10)
    return int(round(base / 50) * 50)


def month_start(index: int) -> date:
    year = START.year + (START.month - 1 + index) // 12
    month = (START.month - 1 + index) % 12 + 1
    return date(year, month, 1)


def build() -> None:
    rng = random.Random(SEED)
    rows: list[dict] = []
    calendar = load_calendar()
    major_days = major_window_days(calendar)
    end = month_start(MONTHS)  # first day after the data window

    # Each household keeps its own persistent character: how much it spends relative to others
    # of the same type, and how many expenses it records in a typical month. Without this the
    # series would be pure noise month to month, which no forecaster (and no real household)
    # would ever look like.
    households = []
    for persona, (weights, count_range) in PERSONAS.items():
        for index in range(HOUSEHOLDS):
            households.append({
                "persona": persona,
                "name": f"{persona}_{index + 1}",
                "weights": weights,
                "scale": rng.lognormvariate(0, 0.22),
                "bills": [
                    (description, category, rng.uniform(low, high), months, rng.randint(1, 27))
                    for description, category, low, high, months in RECURRING[persona]
                ],
                "base_count": rng.uniform(*count_range),
                "drift": rng.uniform(-0.004, 0.007),   # slow monthly trend
                "profile": HOUSEHOLD_PROFILES[f"{persona}_{index + 1}"],
                # Birthdays in the household: the same day every year.
                "birthdays": [] if persona == "trip_group" else sorted(
                    (rng.randint(1, 12), rng.randint(1, 28))
                    for _ in range(rng.randint(1, 4 if persona == "family" else 2))
                ),
            })

    def emit(home, when, description, category, value_npr, festival=""):
        rows.append(
            {
                "date": when.isoformat(),
                "description": render(rng, description, when.month, category),
                "amount_npr": value_npr,
                "category": category,
                "persona": home["persona"],
                "household": home["name"],
                "group_type": GROUP_TYPE[home["persona"]],
                "festival": festival,
            }
        )

    for index in range(MONTHS):
        first = month_start(index)
        days = ((month_start(index + 1)) - first).days
        for home in households:
                persona, weights = home["persona"], home["weights"]
                trend = 1 + home["drift"] * index

                # Recurring bills: same items every month, with small variation.
                for description, category, level, months, day in home["bills"]:
                    if months and first.month not in months:
                        continue
                    when = first + timedelta(days=min(day, days - 1))
                    value = level * trend * rng.uniform(0.94, 1.08) * seasonal_factor(when, category)
                    emit(home, when, description, category, amount(rng, int(value), int(value) + 1, 1.0))

                count = max(
                    4,
                    int(round(home["base_count"] * volume_factor(first.month, persona)
                              * trend * rng.uniform(0.92, 1.08))),
                )
                for _ in range(count):
                    if rng.random() < 0.14:
                        template, distribution, low, high = rng.choice(AMBIGUOUS)
                        category = rng.choices(list(distribution), weights=list(distribution.values()))[0]
                    else:
                        category = pick(rng, weights)
                        template, low, high = rng.choice(TEMPLATES[category])
                    when = first + timedelta(days=rng.randrange(days))
                    factor = seasonal_factor(when, category, major_days) * home["scale"] * trend
                    emit(home, when, template, category, amount(rng, low, high, factor))

    # Festivals, on their real dates, for the households that keep them.
    for festival in calendar:
        if festival.end < START or festival.start >= end:
            continue
        (low_count, high_count), items = FESTIVAL_SPENDING[festival.key]
        for home in households:
            share = participation(festival, home["profile"], home["persona"])
            if share <= 0:
                continue
            count = int(round(rng.uniform(low_count, high_count + 0.999) * share))
            if count == 0 and high_count > 0 and rng.random() < share:
                count = 1
            # Most festival shopping happens before the main day, not after it.
            window = [d for d in festival.days() if d <= festival.peak and START <= d < end] \
                or [d for d in festival.days() if START <= d < end]
            if not window:
                continue
            months_in = (window[0].year - START.year) * 12 + window[0].month - START.month
            trend = 1 + home["drift"] * months_in
            for _ in range(count):
                description, category, low, high = rng.choice(items)
                when = rng.choice(window)
                emit(home, when, description, category,
                     amount(rng, low, high, home["scale"] * trend), festival.key)

    # Birthdays: the same date every year, for every household that is not a trip group.
    for home in households:
        for month, day in home["birthdays"]:
            for year in range(START.year, end.year + 1):
                when = date(year, month, day)
                if not (START <= when < end):
                    continue
                for _ in range(rng.randint(1, 3)):
                    description, category, low, high = rng.choice(BIRTHDAY_ITEMS)
                    emit(home, when, description, category,
                         amount(rng, low, high, home["scale"]), "birthday")

    rows.sort(key=lambda r: (r["date"], r["household"]))
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / "expenses.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # Monthly aggregation per household, used by the spending-forecast model.
    intensity = national_intensity_by_month(calendar)
    monthly: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (row["household"], row["date"][:7])
        bucket = monthly.setdefault(
            key,
            {
                "household": row["household"],
                "group_type": row["group_type"],
                "month": row["date"][:7],
                "total_npr": 0,
                "expense_count": 0,
                "festival_intensity": intensity.get(row["date"][:7], 0.0),
                "festival_npr": 0,
                "food_npr": 0,
                "transport_npr": 0,
            },
        )
        bucket["total_npr"] += row["amount_npr"]
        bucket["expense_count"] += 1
        if row["festival"]:
            bucket["festival_npr"] += row["amount_npr"]
        if row["category"] == "food":
            bucket["food_npr"] += row["amount_npr"]
        if row["category"] == "transport":
            bucket["transport_npr"] += row["amount_npr"]

    fields = ["household", "group_type", "month", "total_npr", "expense_count",
              "festival_intensity", "festival_npr", "food_npr", "transport_npr"]
    with (DATA / "monthly_spending.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for key in sorted(monthly, key=lambda k: (k[0], k[1])):
            writer.writerow(monthly[key])

    with (DATA / "households.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["household", "persona", "group_type", "celebration_profile", "birthdays"])
        for home in households:
            writer.writerow([home["name"], home["persona"], GROUP_TYPE[home["persona"]], home["profile"],
                             " ".join(f"{m:02d}-{d:02d}" for m, d in home["birthdays"])])

    festival_rows = sum(1 for row in rows if row["festival"])
    print(f"expenses.csv          {len(rows):>6} rows ({festival_rows} festival or birthday purchases)")
    print(f"monthly_spending.csv  {len(monthly):>6} rows")


if __name__ == "__main__":
    build()
