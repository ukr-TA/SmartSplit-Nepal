# SmartSplit Nepal - Submission Contents

| Requirement | Where it is in this ZIP |
|---|---|
| Project files | `backend/` (Django), `frontend/` (React), `documentation/`, `README.md`, `SETUP.md` |
| Dataset | `ml/data/expenses.csv` (12,822 labelled expenses), `ml/data/monthly_spending.csv`, `ml/data/price_reference.csv` (the published Nepali prices every amount is based on, with sources), `ml/data/festival_calendar.csv` (118 festivals and seasons 2023-2027 on their real dates, with sources), `ml/data/households.csv` |
| ML notebook | `ml/notebooks/smartsplit_ml.ipynb` - preprocessing, training, evaluation, model export (saved with all outputs) |
| Final report | `SmartSplit-Nepal-Report.docx` |
| Supporting files | `ml/build_dataset.py`, `ml/festivals.py`, `ml/models/` (trained models + metrics.json), `ml/requirements.txt`, `documentation/machine-learning.md`, `.github/workflows/ci.yml`, 71 automated tests |

Setup instructions: `SETUP.md`. Machine-learning method and results: `documentation/machine-learning.md`.
