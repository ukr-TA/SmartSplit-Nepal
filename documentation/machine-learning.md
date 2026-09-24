# Machine Learning in SmartSplit Nepal

SmartSplit uses two supervised models. Both are trained in
[`ml/notebooks/smartsplit_ml.ipynb`](../ml/notebooks/smartsplit_ml.ipynb), exported to
`ml/models/`, and served by the Django API.

| Model | Type | Task | Where you see it |
|---|---|---|---|
| Expense category classifier | Multi-class text classification | description → one of 9 categories | Quick Split wizard, step 1 |
| Monthly spending forecaster | Regression | what a group might spend next month, with a one-line reason | Group Overview tab |

---

## 1. The dataset

### Why it had to be built

There is no public dataset of individual Nepali household transactions, and collecting real
transactions from users was not possible within the project. The dataset is therefore
**synthesised from published Nepali data**, and it is described that way everywhere it appears. It
is realistic in prices, dates and seasonality; it is not a record of real people.

### Prices

[`ml/data/price_reference.csv`](../ml/data/price_reference.csv) holds 51 price points, each with its
source and the date it applied. Among them:

| Item | Value used | Source |
|---|---|---|
| Petrol, diesel, kerosene | Rs. 200/litre (Kathmandu band) | Nepal Oil Corporation retail price |
| LPG cylinder (14.2 kg) | Rs. 2,050–2,060 | Nepal Oil Corporation / market rate |
| Electricity | Rs. 11–13 per unit by slab, plus service charge | NEA domestic tariff FY 2082/83 |
| Vegetables | potato Rs. 48/kg, onion Rs. 90/kg, tomato Rs. 70/kg | Kalimati wholesale, 1 Sept 2026 |
| Khasi meat | Rs. 1,300–1,600/kg | Retail meat price guide; Dashain fixed rates |
| Marigold garland (Tihar) | Rs. 1,000 each | Nepal News, Tihar 2025 |
| Data packs | NTC 20 GB Rs. 399; Ncell combos Rs. 199–699 | Published operator packs |
| Home internet | Rs. 775–999 per month equivalent | WorldLink / Vianet / Subisu / ClassicTech |
| Kathmandu → Pokhara bus | Rs. 1,200–2,000 (deluxe to VIP) | Published operator timetables |
| Cinema ticket | Rs. 150–800 by hall and seat | Showtime Nepal price comparison |
| Room rent (student) | Rs. 5,000–7,000 per month | Kathmandu rental listings |
| Semester fee (private college) | Rs. 60,000–110,000 | Published fee guides |

### The festival calendar

[`ml/data/festival_calendar.csv`](../ml/data/festival_calendar.csv) lists **118 festivals, occasions
and seasons from 2023 to 2027, each on its real date for that year, with a source for each**. Most
Nepali festivals follow the lunar calendar and move every year: Dashain began on **22 September in
2025** but on **11 October in 2026**. A fixed "October and November" rule would have put the 2025
Dashain spending in the wrong month, which is exactly what the first version of this dataset did.

| Kind | Festivals |
|---|---|
| Major | Dashain, Tihar |
| Festivals | Teej, Chhath, Holi, Nepali New Year, Maghe Sankranti, Sonam / Gyalpo / Tamu Lhosar, Eid al-Fitr, Eid al-Adha, Mangsir wedding season |
| Occasions | Janai Purnima, Krishna Janmashtami, Maha Shivaratri, Buddha Jayanti, Mother's Day, Father's Day, Shree Panchami, Gai Jatra, Indra Jatra, Yomari Punhi, Christmas, New Year's Eve, Valentine's Day, Magh–Falgun and Baisakh–Asar wedding seasons |

[`ml/festivals.py`](../ml/festivals.py) says what each festival makes people buy: new clothes, khasi
meat, tika dakshina and bus tickets home for Dashain; marigold garlands, diyo, dry fruits and Bhai
Tika gifts for Tihar; a red saree, pote and a dar party for Teej; rakhi and kwati for Janai Purnima;
fruits and temple offerings for Janmashtami; and so on. Where a published price exists it is used.
The *number* of purchases each festival causes is a modelling assumption, ranked by the size of the
festival; that is stated in the notebook and the report.

### How a year is generated

[`ml/build_dataset.py`](../ml/build_dataset.py) simulates 15 households of five kinds (hostel
student, student living at home, working bachelor, family, trip group) over 36 months, from October
2023 to September 2026, producing **12,822 expenses** with 5,342 different descriptions.

1. **Recurring bills come first.** Rent, electricity, water, internet and school fees repeat every
   month at a level fixed per household; the gas cylinder repeats every second month; semester fees
   land in two months of the year.
2. **Discretionary expenses are sampled** from category weights that differ by household type, using
   real vendor, place and item names.
3. **Festivals happen on their real dates**, for the households that keep them. Each household has a
   celebration profile, recorded in `data/households.csv`: a Newar family keeps Gai Jatra, Indra
   Jatra and Yomari Punhi; a Madhesi family keeps Chhath and has a bigger Holi; a Magar student
   celebrates Maghi as the new year; Tamang, Sherpa and Gurung households keep their own Lhosar; a
   Muslim household keeps both Eids; a Christian household keeps Christmas. Everyone keeps the
   national festivals, and families celebrate on a bigger scale than a student in a hostel. Most
   festival shopping is dated before the main day, not after it.
4. **Birthdays** recur on the same date every year for every household, bringing cakes, gifts and
   dinners out. **Wedding seasons** bring gift envelopes, clothes and travel.
5. **Everyday spending rises inside the Dashain and Tihar windows** (transport by 29%, the reported
   rise in petroleum use during Dashain). Monsoon months raise vegetable prices and winter raises
   electricity use.
6. **Ambiguity is added on purpose.** About one entry in seven comes from descriptions that
   genuinely belong to more than one category ("Snacks during movie", "Hotel dinner", "Gas
   cylinder"), each labelled by a probability distribution, so no model can score a perfect 100%.

Festival, wedding and birthday purchases end up as 14% of all expenses and 16% of all money spent.
The script is deterministic: `python ml/build_dataset.py` reproduces the same data every time.

---

## 2. Category classifier

**Features.** Descriptions are lower-cased and stripped to letters, then vectorised as a union of
TF-IDF word 1–2 grams and character 3–5 grams, so typos and inconsistent Romanised Nepali (*khaja*,
*khaaja*) still match.

**Avoiding leakage.** Many people write exactly the same description. A plain random split puts
identical text on both sides and produced an accuracy of 100% that meant nothing. The notebook groups
rows by their cleaned text (`GroupShuffleSplit`, `GroupKFold`), so no wording is in both training and
test.

**Result.** Logistic Regression, **97.2% accuracy and 0.96 macro F1** on held-out descriptions
(5-fold grouped cross-validation: Logistic Regression 0.960, Linear SVM 0.958, Naive Bayes 0.954).
The remaining errors are the deliberately ambiguous entries, which is why the app treats the answer
as a suggestion the user can ignore.

---

## 3. Spending forecaster

**Data.** The 36 months are aggregated per household, giving 540 household-months.

**Features.** Everything the model sees exists before the month it predicts:

| Feature | What it captures |
|---|---|
| Last three months, and their average | the group's usual level and recent trend |
| **Same month last year** | birthdays, a household's own festivals and anything else that repeats yearly - without the app needing to know what they are |
| **Festival intensity of the target month** | the national festival calendar as one number per month (Dashain weighs 1.0, Tihar 0.7, Teej 0.25 ...) spread over the days each festival covers |
| Festival intensity of the current month | spending that falls back after a festival month |
| Month of the year (sine and cosine) | season |
| Group type | family, roommates, college, trip |

The target month's festival intensity is allowed because the calendar is published in advance; the
app computes it for any future month from the same file.

**Evaluation: time-series cross-validation.** Two held-out windows (September 2025 – February 2026,
which contains Dashain 2025, and March – September 2026), each predicted by a model trained only on
earlier months.

| Features | Best model | Average MAE |
|---|---|---|
| **Festival calendar + same month last year** | **Random Forest** | **Rs. 22,985** |
| Old "October or November" flag | Random Forest | Rs. 25,282 |
| Festival calendar only | Gradient Boosting | Rs. 25,298 |
| Naive: average of last 3 months | - | Rs. 30,691 |
| Naive: repeat last month | - | Rs. 35,283 |

The calendar together with the same-month-last-year feature beats the old calendar-blind rule by
about 9% and the best naive baseline by about 25%. The calendar on its own is roughly level with the
old flag: most of the gain comes from "the same month last year". In the window that contains
Dashain 2025, the old flag happened to score slightly better; the notebook shows both windows
rather than only the average, so this is visible.

The relative error remains about 42%. Trip groups are the hardest (their spending comes in bursts);
families, dominated by recurring bills, are predicted most closely. This is why the app presents the
forecast as a range, worded as what *might* happen.

---

## 4. The reason under each forecast

Under the predicted amount, the card shows **one or two short sentences** saying what the estimate
is based on, always worded as a possibility:

> You've spent Rs. 39,000 in September so far, mostly on rent. October might come in higher, around
> Rs. 73,842, with Dashain on 11–25 Oct.

The first sentence comes from the group's own spending this month (its biggest category). The second
names the most important national festival in the coming month, if there is one, and says whether
the month might be higher, lighter or much like usual. A few other examples it can produce:

- *December might come in higher, around Rs. 63,643, with the Mangsir wedding season on 16 Nov – 15 Dec.*
- *March might come in higher, around Rs. 46,474, with Holi (Fagu Purnima) on 2 Mar.*
- *July might look much like usual, around Rs. 42,222.*

It never says *will*. The sentence describes what the forecast is based on; it does not claim to be
an exact breakdown of how the model weighed each input. The API also returns the fuller details
behind it (categories, festival dates, the same month last year, whether the safety clamp was
applied) for anyone who wants them, but the card deliberately shows only the short version.

Two details worth knowing: if the latest month is still running, its remaining days are filled in at
the group's recent daily rate before the model uses it; and when the model's raw estimate falls
outside 0.6–1.6× the group's recent average, it is clamped to that band.

---

## 5. How the models reach the app

```
ml/notebooks/smartsplit_ml.ipynb
        │  exports
        ▼
ml/models/category_clf.joblib, spend_forecast.joblib (+ festival calendar), metrics.json
        │  loaded lazily by
        ▼
backend/insights/predictor.py
        │  exposed through
        ▼
POST /api/ml/suggest-category/      GET  /api/groups/{id}/forecast/      GET /api/ml/info/
        │  consumed by
        ▼
CategorySuggestion.jsx (Quick Split)   ForecastCard.jsx (Group Overview)
```

If the `.joblib` files are missing, category suggestions fall back to keyword matching and the
forecast to a three-month average, and the `source` field reports which path answered.

---

## 6. Reproducing the results

```bash
cd SmartSplit-Nepal
source backend/venv/bin/activate
pip install -r ml/requirements.txt

python ml/build_dataset.py                          # regenerates data/ (deterministic)
jupyter notebook ml/notebooks/smartsplit_ml.ipynb   # Run All: retrains and re-exports models
```

Restart the backend afterwards so it loads the new models. `backend/insights/tests.py` covers the
model path, the fallback path and the forecast wording, and runs as part of `python manage.py test`.

---

## 7. Limitations

1. The dataset is synthesised from published prices and dates, not collected from users.
   Individual behaviour is modelled, not observed.
2. The number of purchases each festival causes is an assumption ranked by festival size; the dates
   and prices are sourced, the volumes are not measured.
3. Thirty-six months across fifteen households is a small basis for forecasting, and the model
   cannot know about one-off events.
4. The festival calendar runs to December 2027. Beyond that, the app reuses the same month from the
   latest year it knows, which is only approximate for lunar festivals.
5. Descriptions are Romanised Nepali and English; Devanagari would need transliteration.
6. The most valuable next step is retraining on real data: every time a user overrides a suggested
   category, that is a labelled example from the real distribution.
