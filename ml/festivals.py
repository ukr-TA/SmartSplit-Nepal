"""
The Nepali festival year, as the dataset generator and the notebook see it.

Three things live here:

1. ``load_calendar`` reads ``data/festival_calendar.csv``: the real dates of every festival and
   event that noticeably changes what a household spends, for 2023-2027, each with its source.
   The dates move every year because most of them follow the lunar calendar. Dashain began on
   22 September in 2025 but on 11 October in 2026, which is why a fixed "October and November"
   rule is not good enough.

2. ``FESTIVAL_SPENDING`` says *what people buy* for each festival: new clothes and khasi meat for
   Dashain, marigold garlands, diyo and dry fruits for Tihar, a red saree and a dar party for Teej,
   rakhi and kwati for Janai Purnima, and so on. Prices come from ``data/price_reference.csv``
   where a published figure exists (khasi meat, marigold garlands, dry fruits, bus fares).
   The *number* of purchases per festival is a modelling assumption, ranked by the size of each
   festival; it is not a measured quantity, and the report says so.

3. ``national_intensity_by_month`` turns the calendar into one number per month: how much
   festival activity the whole country has in that month. This is a feature for the spending
   forecaster, and the app can compute it for any future month from the same calendar.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

CALENDAR_PATH = Path(__file__).resolve().parent / "data" / "festival_calendar.csv"


@dataclass(frozen=True)
class Festival:
    key: str
    name: str
    start: date
    end: date
    peak: date
    scale: str
    celebrated_by: frozenset[str]
    national_weight: float
    source: str

    def days(self) -> list[date]:
        return [self.start + timedelta(days=i) for i in range((self.end - self.start).days + 1)]


def load_calendar(path: Path = CALENDAR_PATH) -> list[Festival]:
    with Path(path).open(encoding="utf-8") as handle:
        return [
            Festival(
                key=row["key"],
                name=row["festival"],
                start=date.fromisoformat(row["start_date"]),
                end=date.fromisoformat(row["end_date"]),
                peak=date.fromisoformat(row["peak_date"]),
                scale=row["scale"],
                celebrated_by=frozenset(part.strip() for part in row["celebrated_by"].split(",")),
                national_weight=float(row["national_weight"]),
                source=row["source"],
            )
            for row in csv.DictReader(handle)
        ]


# --------------------------------------------------------------------------------------
# Who celebrates what
# --------------------------------------------------------------------------------------
# Each simulated household is given a celebration profile. The tags decide which festivals it
# keeps; everyone keeps the national ones. Profiles describe festivals, not people.
PROFILE_TAGS: dict[str, set[str]] = {
    "hindu_hill": {"all", "hindu"},
    "newar": {"all", "hindu", "buddhist", "newar"},
    "madhesi": {"all", "hindu", "madhesi"},
    "magar": {"all", "hindu", "magar"},
    "tamang": {"all", "buddhist", "tamang"},
    "gurung": {"all", "buddhist", "gurung"},
    "sherpa": {"all", "buddhist", "sherpa"},
    "muslim": {"all", "muslim"},
    "christian": {"all", "christian"},
    "friends": set(),  # trip groups: their festival spending happens at home, not on the trip
}

# Special cases where a festival matters much more (or less) to one profile.
PARTICIPATION_OVERRIDES: dict[tuple[str, str], float] = {
    ("dashain", "muslim"): 0.35,      # a public holiday for everyone, but not their festival
    ("dashain", "christian"): 0.35,
    ("tihar", "muslim"): 0.35,
    ("tihar", "christian"): 0.35,
    ("holi", "madhesi"): 1.8,         # Holi is a far bigger occasion in the Terai
    ("maghe_sankranti", "magar"): 3.0,  # Maghi is the new year for Magar and Tharu communities
}

# Families celebrate on a larger scale than a student in a hostel.
PERSONA_FACTOR = {"family": 1.4, "working_bachelor": 0.9, "student_hostel": 0.7,
                  "student_home": 0.8, "trip_group": 0.0}


def participation(festival: Festival, profile: str, persona: str) -> float:
    tags = set(PROFILE_TAGS.get(profile, set()))
    if persona.startswith("student"):
        tags |= {"students", "youth"}
    if persona == "working_bachelor":
        tags |= {"youth"}
    if not tags & festival.celebrated_by:
        return 0.0
    factor = PARTICIPATION_OVERRIDES.get((festival.key, profile), 1.0)
    return factor * PERSONA_FACTOR.get(persona, 1.0)


# --------------------------------------------------------------------------------------
# What people buy
# --------------------------------------------------------------------------------------
# key -> (purchases per celebrating household (low, high), [(description, category, low, high)])
FESTIVAL_SPENDING: dict[str, tuple[tuple[int, int], list[tuple[str, str, int, int]]]] = {
    "dashain": ((6, 12), [
        ("New clothes for Dashain", "shopping", 2500, 12000),
        ("Khasi meat for Dashain", "food", 2600, 9600),          # 2-6 kg at Rs 1,300-1,600/kg
        ("Khasi for Dashain (shared with family)", "food", 10000, 22000),
        ("Bus ticket home for Dashain", "transport", 1200, 3500),
        ("Tika dakshina for nieces and nephews", "other", 2000, 10000),
        ("Fruits and sweets for Dashain", "food", 1500, 5000),
        ("Jamara and puja samagri", "other", 300, 1200),
        ("Changa and lattai for Dashain", "entertainment", 300, 1500),
        ("Snacks for cards night", "food", 800, 2500),
        ("Gift for hajurba hajurama", "shopping", 1500, 5000),
    ]),
    "tihar": ((5, 10), [
        ("Sayapatri mala for Tihar", "shopping", 1000, 4000),     # Rs 1,000 per garland in 2025
        ("Diyo, candles and lights", "shopping", 500, 2500),
        ("Laxmi puja samagri", "other", 800, 3000),
        ("Sel roti ingredients", "food", 600, 2000),
        ("Dry fruits for Bhai Tika", "food", 1200, 4500),
        ("Bhai Tika gift for didi", "shopping", 2000, 8000),
        ("Deusi bhailo contribution", "other", 200, 1500),
        ("Rangoli colours", "shopping", 150, 600),
        ("Gold coin on Dhanteras", "shopping", 8000, 30000),
        ("Sweets from Bhatbhateni for Tihar", "food", 800, 3000),
    ]),
    "chhath": ((4, 7), [
        ("Fruits for Chhath", "food", 1500, 5000),
        ("Thekua ingredients", "food", 800, 2500),
        ("Soop and dauro for Chhath", "shopping", 500, 1500),
        ("Sugarcane and coconut for Chhath", "food", 400, 1200),
        ("New saree for Chhath", "shopping", 2500, 8000),
        ("Bus to Janakpur for Chhath", "transport", 1200, 2500),
    ]),
    "teej": ((2, 5), [
        ("Red saree for Teej", "shopping", 3000, 12000),
        ("Pote and chura for Teej", "shopping", 800, 3000),
        ("Dar khane party", "food", 1500, 6000),
        ("Mehendi for Teej", "other", 300, 1000),
        ("Teej program ticket", "entertainment", 500, 1500),
    ]),
    "janai_purnima": ((1, 3), [
        ("Rakhi for bhai", "shopping", 200, 800),
        ("Kwati for Janai Purnima", "food", 300, 900),
        ("Janai and dakshina", "other", 200, 1000),
        ("Raksha Bandhan gift for didi", "shopping", 1000, 4000),
    ]),
    "janmashtami": ((1, 2), [
        ("Fruits and puja for Krishna Janmashtami", "food", 500, 2000),
        ("Offerings at Krishna Mandir Patan", "other", 200, 800),
        ("Sweets for Janmashtami", "food", 400, 1500),
    ]),
    "gai_jatra": ((1, 2), [
        ("Samay baji for Gai Jatra", "food", 800, 2500),
        ("Snacks at Gai Jatra procession", "food", 300, 1000),
    ]),
    "indra_jatra": ((1, 2), [
        ("Samay baji at Indra Jatra", "food", 600, 2000),
        ("Indra Jatra mela snacks", "food", 300, 1200),
    ]),
    "yomari": ((1, 2), [
        ("Yomari ingredients", "food", 500, 1500),
        ("Yomari from Newari khaja ghar", "food", 400, 1200),
    ]),
    "holi": ((1, 3), [
        ("Holi colours and pichkari", "entertainment", 300, 1500),
        ("Holi party snacks and drinks", "food", 1000, 4000),
        ("Water balloons for Holi", "entertainment", 150, 500),
    ]),
    "shivaratri": ((1, 2), [
        ("Offerings at Pashupatinath for Shivaratri", "other", 200, 1000),
        ("Firewood for Shivaratri", "other", 200, 800),
    ]),
    "new_year": ((1, 3), [
        ("Nepali New Year dinner", "food", 1500, 6000),
        ("New Year picnic", "entertainment", 1000, 4000),
        ("Trip to Bhaktapur for Bisket Jatra", "transport", 300, 1200),
    ]),
    "buddha_jayanti": ((1, 2), [
        ("Offerings at Swayambhu for Buddha Jayanti", "other", 200, 1000),
        ("Donation at gumba", "other", 500, 3000),
    ]),
    "maghe_sankranti": ((1, 3), [
        ("Chaku, ghee and tarul", "food", 800, 2500),
        ("Til ko laddu", "food", 300, 1000),
        ("Maghi feast", "food", 2000, 8000),
        ("New clothes for Maghi", "shopping", 2000, 7000),
    ]),
    "sonam_lhosar": ((3, 6), [
        ("Sonam Lhosar feast", "food", 2000, 8000),
        ("New clothes for Lhosar", "shopping", 2500, 9000),
        ("Lhosar program ticket", "entertainment", 500, 2000),
        ("Khapse and sweets for Lhosar", "food", 500, 2000),
    ]),
    "gyalpo_lhosar": ((3, 6), [
        ("Gyalpo Lhosar feast", "food", 2000, 8000),
        ("New clothes for Lhosar", "shopping", 2500, 9000),
        ("Khapse for Lhosar", "food", 500, 2000),
        ("Offerings at Bouddha for Lhosar", "other", 500, 2000),
    ]),
    "tamu_lhosar": ((3, 6), [
        ("Tamu Lhosar feast", "food", 2000, 8000),
        ("New clothes for Tamu Lhosar", "shopping", 2500, 9000),
        ("Tamu Lhosar program at Tundikhel", "entertainment", 300, 1500),
        ("Sel roti and meat for Lhosar", "food", 1000, 4000),
    ]),
    "eid_fitr": ((3, 6), [
        ("New clothes for Eid", "shopping", 3000, 10000),
        ("Sewai and dates for Eid", "food", 800, 2500),
        ("Eid feast", "food", 2500, 8000),
        ("Eidi for children", "other", 1000, 5000),
    ]),
    "eid_adha": ((2, 3), [
        ("Qurbani share", "food", 8000, 25000),
        ("Bakr Eid feast", "food", 2000, 6000),
    ]),
    "mothers_day": ((1, 2), [
        ("Gift for mummy on Mata Tirtha Aunsi", "shopping", 1000, 5000),
        ("Sweets and fruits for aama", "food", 500, 2000),
        ("Trip to Matatirtha", "transport", 300, 1000),
    ]),
    "fathers_day": ((1, 2), [
        ("Gift for buwa on Kushe Aunsi", "shopping", 1000, 5000),
        ("Sweets for buwa", "food", 500, 2000),
    ]),
    "shree_panchami": ((1, 2), [
        ("Saraswati puja at college", "education", 100, 500),
        ("New pen and copy for Saraswati puja", "education", 200, 800),
    ]),
    "christmas": ((1, 4), [
        ("Christmas cake and dinner", "food", 1500, 6000),
        ("Christmas gifts", "shopping", 2000, 8000),
        ("Christmas party in Thamel", "entertainment", 1500, 5000),
    ]),
    "new_years_eve": ((1, 2), [
        ("New Year's Eve party", "entertainment", 1500, 6000),
        ("Countdown dinner", "food", 1500, 4500),
    ]),
    "valentines": ((0, 1), [
        ("Valentine's Day dinner", "food", 1500, 5000),
        ("Flowers and gift for Valentine's", "shopping", 800, 4000),
    ]),
    # Wedding seasons: each attended wedding means a gift and often new clothes or travel.
    "wedding_mangsir": ((1, 4), [
        ("Wedding gift envelope", "other", 1000, 5000),
        ("Clothes for a wedding", "shopping", 3000, 12000),
        ("Bus to a wedding in {trip}", "transport", 1000, 3500),
        ("Wedding gift", "shopping", 1500, 6000),
    ]),
    "wedding_magh": ((0, 3), [
        ("Wedding gift envelope", "other", 1000, 5000),
        ("Clothes for a wedding", "shopping", 3000, 12000),
        ("Wedding gift", "shopping", 1500, 6000),
    ]),
    "wedding_baisakh": ((0, 3), [
        ("Wedding gift envelope", "other", 1000, 5000),
        ("Bus to a wedding in {trip}", "transport", 1000, 3500),
        ("Wedding gift", "shopping", 1500, 6000),
    ]),
}

# Personal occasions that repeat on the same date every year.
BIRTHDAY_ITEMS = [
    ("Birthday cake for {name}", "food", 800, 2500),
    ("Birthday party dinner", "food", 2500, 9000),
    ("Birthday gift for {name}", "shopping", 1500, 6000),
]

# Major festival windows also lift everyday spending (more meat, more travel, more visitors).
# The 29% transport figure is the reported rise in petroleum consumption during Dashain.
WINDOW_UPLIFT = {"food": 1.15, "transport": 1.29, "shopping": 1.2, "entertainment": 1.1}


def major_window_days(calendar: list[Festival]) -> set[date]:
    return {day for festival in calendar if festival.scale == "major" for day in festival.days()}


# --------------------------------------------------------------------------------------
# One number per month for the forecaster
# --------------------------------------------------------------------------------------
def national_intensity_by_month(calendar: list[Festival]) -> dict[str, float]:
    """Spread each festival's national weight over the months its days fall in.

    Dashain 2025 ran from 22 September to 6 October, so 60% of its weight lands in September
    and 40% in October; Dashain 2026 falls entirely in October.
    """
    intensity: dict[str, float] = {}
    for festival in calendar:
        if festival.national_weight <= 0:
            continue
        days = festival.days()
        for day in days:
            key = f"{day.year:04d}-{day.month:02d}"
            intensity[key] = intensity.get(key, 0.0) + festival.national_weight / len(days)
    return {key: round(value, 4) for key, value in sorted(intensity.items())}


def festivals_by_month(calendar: list[Festival]) -> dict[str, list[str]]:
    """Names of the festivals (not the wedding seasons) whose main day falls in each month."""
    names: dict[str, list[str]] = {}
    for festival in sorted(calendar, key=lambda f: f.peak):
        if festival.key.startswith("wedding"):
            continue
        key = f"{festival.peak.year:04d}-{festival.peak.month:02d}"
        if festival.name not in names.setdefault(key, []):
            names[key].append(festival.name)
    return names


# What each festival usually costs a household, in plain words. Used to explain forecasts.
FESTIVAL_BLURB: dict[str, str] = {
    "dashain": "new clothes, khasi meat, tika dakshina and bus tickets home",
    "tihar": "marigold garlands, diyo and lights, dry fruits and Bhai Tika gifts",
    "chhath": "fruits, thekua and puja items for households that observe it",
    "teej": "red sarees, pote and chura, and dar parties",
    "janai_purnima": "rakhi, kwati and small gifts",
    "janmashtami": "fruits, sweets and temple offerings",
    "gai_jatra": "samay baji and snacks",
    "indra_jatra": "samay baji and fair snacks",
    "yomari": "yomari and a family meal",
    "holi": "colours, snacks and a party",
    "shivaratri": "temple offerings",
    "new_year": "a New Year dinner or picnic",
    "buddha_jayanti": "offerings and donations",
    "maghe_sankranti": "chaku, ghee, tarul and til ko laddu",
    "sonam_lhosar": "a feast and new clothes",
    "gyalpo_lhosar": "a feast and new clothes",
    "tamu_lhosar": "a feast and new clothes",
    "eid_fitr": "new clothes, sewai and a feast",
    "eid_adha": "qurbani and a feast",
    "mothers_day": "a gift and sweets for mothers",
    "fathers_day": "a gift and sweets for fathers",
    "shree_panchami": "Saraswati puja at college",
    "christmas": "cake, gifts and parties",
    "new_years_eve": "parties and dinners out",
    "valentines": "a dinner out and gifts",
    "wedding_mangsir": "wedding gifts, clothes and travel (peak wedding season)",
    "wedding_magh": "wedding gifts and clothes",
    "wedding_baisakh": "wedding gifts and travel",
}


def festival_details_by_month(calendar: list[Festival]) -> dict[str, list[dict]]:
    """For every month, the festivals and seasons that touch it, with their dates and weight.

    This is what the app uses to explain a forecast ("Dashain falls on 11-25 October ...").
    """
    details: dict[str, list[dict]] = {}
    for festival in sorted(calendar, key=lambda f: f.start):
        months = sorted({f"{d.year:04d}-{d.month:02d}" for d in festival.days()})
        for key in months:
            details.setdefault(key, []).append({
                "key": festival.key,
                "name": festival.name,
                "start": festival.start.isoformat(),
                "end": festival.end.isoformat(),
                "peak": festival.peak.isoformat(),
                "scale": festival.scale,
                "national_weight": festival.national_weight,
                "celebrated_by": sorted(festival.celebrated_by),
                "spending": FESTIVAL_BLURB.get(festival.key, ""),
            })
    return details
