# How to Demonstrate SmartSplit Nepal

A 5–10 minute presentation script for a mentor or university assessment. Everything is done through the app — no database editing.

## Before the presentation (5 minutes, the day before)

1. Start PostgreSQL (Postgres.app → *Running*).
2. **Terminal 1:**

   ```bash
   cd backend && source venv/bin/activate && python manage.py runserver
   ```

3. **Terminal 2:**

   ```bash
   cd frontend && npm run dev
   ```

4. Make sure the demo friends exist:

   ```bash
   python manage.py seed_demo
   python manage.py seed_demo --owner your-email@example.com   # sample groups, incl. a year of flat bills and festivals
   ```

5. Optional clean start: reset the database (SETUP.md §11), then run `migrate` and `seed_demo` again.
6. Open two browser windows side by side:
   - **Window A (normal):** <http://localhost:5173>, where you are *Utsuk*.
   - **Window B (private/incognito):** you'll log in as *Mina* (`9800000004` / `SmartSplit@123`) in step 10.
7. Zoom the browser to 110–125% so the audience can read it.

**Backup plan:** if the internet is down, everything still works. The demo uses the **Demo simulation** payment mode, and Google Fonts falls back to the system font.

---

## The script

| # | Do this | Say this |
|---|---------|----------|
| 1 | **Register** as Utsuk (or log in). Point at the green "Server connected" dot. | "React frontend, Django REST API and PostgreSQL. Login works with email or a Nepali mobile number." |
| 2 | **New group** → `Pokhara Trip`, type **Trip**, dates 12–15 Sep → **Create group** | "Trip Mode adds dates and analytics." |
| 3 | **Add members**: type `98000` (hint), then `9800000001` → Add. Add `9800000002`, search `Hari`, `mina@smartsplit.np`. Click **Invite** to show the QR code. | "Friends are found by phone number — only a full number matches, and it's shown masked for privacy. People who aren't registered yet can join with the QR code." |
| 4 | **Split Expense** → `Hotel`, Rs. 12,000, Hotel, paid by you, everyone, **Equally** → **Review** (attach a receipt photo) → **Confirm** | "The review screen comes from the backend's own calculation — your share and how your balance changes." |
| 5 | **Split Expense** → `Dinner at Lakeside`, Rs. 6,500, Food, paid by **Ram**, equally | |
| 6 | **Split Expense** → `Taxi & bus`, Rs. 8,000, Transport, paid by **Sita**, **Custom**: you 2,000, others 1,500 (show the "left" warning first) | "Custom amounts must match the total — checked in the browser *and* on the server." |
| 7 | (Optional) `Paragliding`, Rs. 4,000, paid by **Hari**, **Percentages** 20% each | "Percentages must total 100%." |
| 8 | **Expenses** tab → click Hotel | "Timeline cards, category icons, participants, and the uploaded receipt for proof." |
| 9 | **Balances** tab → **How it works** | "Net balance = paid − share ± settlements. The algorithm pairs exact matches, then the biggest giver with the biggest receiver: **3 payments instead of 10**." Point at *Hari → Sita 2,000 · Mina → Utsuk 5,500 · Mina → Ram 500*. |
| 10 | **Window B**: log in as **Mina** → Dashboard | "Mina immediately sees: *You need to give Rs. 6,000*, and exactly whom to pay." |
| 11 | **Settle** (Utsuk, Rs. 5,500) → **Khalti** → Demo simulation → **Continue** → MPIN `1111` → **Confirm Payment** | "Balance → Settlement → Payment in three clicks. The transaction ID `SMRT-KHL-…` is generated on the server." |
| 12 | **View receipt** → show **Print / Save PDF** | "Every settlement has a receipt." |
| 13 | Window B → Pokhara Trip → **Balances** | "Mina's balance has already updated — only Rs. 500 to Ram is left." |
| 14 | (Optional) Log in as Hari (`9800000003`) → **Settle** → **eSewa** → Confirm | "eSewa works the same way. With internet, *eSewa test gateway* redirects to eSewa's real test site." |
| 15 | **Window A** (Utsuk): the bell shows a notification → open it. **Settlements** tab | "Settlement history: who, whom, amount, method, date, transaction ID, status." |
| 16 | **Trip Analytics** tab | "Total spending, spending by category, by member (paid versus fair share), and a daily chart." |
| 17 | **Dashboard** | "Back home: you will receive, you need to give, net balance, recent activity." |
| 18 | **Split Expense** → type `Tourist bus Kathmandu to Pokhara` | "Machine learning, part one: the model reads the description and suggests *Transport*, with its confidence. It's only a suggestion — one click to accept, one to ignore." |
| 19 | **Groups → Kathmandu Flat → Overview** → scroll to **Spending forecast** | "Part two: what the flat *might* spend next month. It uses the last three months, the same month last year and the real Nepali festival calendar, and the line underneath gives the reason in one sentence — here, Dashain on 11–25 October. Always *might*, never *will*: the measured error is about 40%." |
| 20 | (If time) Device toolbar → iPhone view | "Responsive — bottom navigation on mobile." |

**Closing line:** *"Split less. Settle smarter. SmartSplit Nepal turns a pile of shared bills into the fewest possible payments, in rupees, with the wallets Nepali students actually use."*

---

## Likely questions — short answers

- **How do you stop someone overpaying?** The backend only accepts a settlement if the payer owes money, the recipient is owed money, and the amount is at most the smaller of the two.
- **Is the eSewa/Khalti payment real?** The simulation is not. The *test gateway* mode uses the official eSewa ePay v2 and Khalti KPG-2 **sandbox** APIs, with signature (eSewa) and lookup (Khalti) verification. No real money moves. Merchant APIs pay a business account, so real person-to-person wallet transfers would need an agreement with the wallet provider.
- **What if two people pay at once?** Settlements are completed inside a database transaction with a row lock, and balances are always recalculated from the stored records.
- **Why not store balances?** Calculating them from expenses and settlements means they can never go out of sync.
- **Is the algorithm optimal?** It needs at most *n − 1* payments and is usually close to the minimum. The exact minimum is an NP-hard problem, so a predictable greedy method is the practical choice (see `documentation/smart-settlement.md`).
- **How is it tested?** There are 71 Django tests (splits, balances, algorithm on random groups, permissions, payments, the ML endpoints, their explanations and fallbacks), plus a full browser run-through of this exact demo.
- **Is the ML data real?** It is synthesised from published Nepali prices and the real festival calendar, with a source for every price and date. It is not collected from users, and the notebook and report say so.
- **Why did Dashain need a calendar?** It follows the lunar calendar: it began on 22 September in 2025 but 11 October in 2026. A fixed "October and November" rule put 2025's spending in the wrong month, so it was replaced by 118 sourced festival dates for 2023–2027.
- **Why say "might"?** Across two held-out windows the forecaster's error is about 40% of a month's total. Household spending is volatile, so the app shows a range and words it as a possibility.

## Future enhancements (if asked)

- Scanning receipt photos to fill in expenses automatically (OCR).
- Recurring expenses (monthly rent).
- Push/email notifications and reminders.
- Multiple currencies for trips abroad.
- A mobile app, and live wallet payouts via provider partnership.
- Splitting by shares or units, and offline mode.
