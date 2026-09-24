# Smart Settlement — How SmartSplit Works Out Who Pays Whom

This document explains the money logic, from a single expense to the final "who pays whom" plan.

Code:

| Step | File |
|------|------|
| Splitting an expense into shares | `backend/expenses/splitting.py` |
| Net balances & direct debts | `backend/settlements/balances.py` |
| Settlement matching | `backend/settlements/algorithm.py` |
| Tests | `backend/expenses/tests.py`, `backend/settlements/tests.py` |

All calculations use **integer paisa** (1 rupee = 100 paisa), so the totals always add up exactly and floating-point rounding can't creep in.

---

## 1. From an expense to individual shares

Each expense has a **payer** (who paid the bill) and **participants** (who shares it). The split method decides each participant's **share**:

| Method | Rule | Validation |
|--------|------|------------|
| Equal | `total ÷ number of participants` | at least one participant |
| Custom | each person's amount is entered | amounts must add up **exactly** to the total |
| Percentage | `total × percentage ÷ 100` | percentages must add up to **exactly 100%** |

**Leftover paisa.** Rs. 100 split between 3 people is 3333.33… paisa each. SmartSplit gives 3334, 3333, 3333 — the leftover paisa goes to the first participants — so the shares add up to exactly 10000 paisa. The percentage method fixes rounding the same way.

The shares are stored as `ExpenseSplit` rows (one per participant), and the backend validates them again even if the browser already did.

**Example — Hotel Rs. 12,000 paid by Utsuk, equal split between 5 people**

| Person | Share |
|--------|------:|
| Utsuk | 2,400 |
| Ram | 2,400 |
| Sita | 2,400 |
| Hari | 2,400 |
| Mina | 2,400 |

---

## 2. From shares to net balances

For every person in a group:

```text
net = total they paid for expenses
    − total of their shares
    + successful settlements they paid
    − successful settlements they received
```

- `net > 0` → the group owes them → they should **receive**
- `net < 0` → they owe the group → they should **give**
- `net = 0` → settled

Only settlements with status **successful** count. A pending eSewa/Khalti payment does not change anything until it is confirmed.

Because every rupee paid is someone's share, **the nets of a group always add up to zero**. The algorithm relies on this, and it checks it.

### Worked example — Pokhara Trip

| Expense | Amount | Paid by | Split |
|---------|-------:|---------|-------|
| Hotel | 12,000 | Utsuk | equal (5) |
| Dinner | 6,500 | Ram | equal (5) |
| Taxi & bus | 8,000 | Sita | custom: Utsuk 2,000, others 1,500 |
| Paragliding | 4,000 | Hari | 20% each |

| Person | Paid | Share | Net |
|--------|-----:|------:|----:|
| Utsuk | 12,000 | 2,400 + 1,300 + 2,000 + 800 = 6,500 | **+5,500** |
| Ram | 6,500 | 2,400 + 1,300 + 1,500 + 800 = 6,000 | **+500** |
| Sita | 8,000 | 6,000 | **+2,000** |
| Hari | 4,000 | 6,000 | **−2,000** |
| Mina | 0 | 6,000 | **−6,000** |
| **Sum** | | | **0** ✔ |

---

## 3. Identifying creditors and debtors

- **Creditors** (receive): Utsuk 5,500 · Sita 2,000 · Ram 500
- **Debtors** (give): Mina 6,000 · Hari 2,000

---

## 4. Settlement matching

`minimize_transactions(balances)` in `settlements/algorithm.py`:

1. **Ignore settled people** (net = 0).
2. **Exact matches first.** If a debtor owes exactly what a creditor is owed, pair them. One payment clears two people at once.
3. **Greedy matching.** Repeatedly take the person who owes the most and the person who is owed the most, and transfer `min(owes, owed)`. Whichever of the two reaches zero drops out.
4. Repeat until nobody is left.

Ties are broken by name, so the plan is the same every time the page loads.

### Applied to the example

| Round | Biggest debtor | Biggest creditor | Payment | Remaining |
|-------|----------------|------------------|---------|-----------|
| Exact match | Hari (2,000) | Sita (2,000) | **Hari → Sita 2,000** | both cleared |
| 1 | Mina (6,000) | Utsuk (5,500) | **Mina → Utsuk 5,500** | Mina 500, Utsuk cleared |
| 2 | Mina (500) | Ram (500) | **Mina → Ram 500** | everyone cleared |

**Smart plan: 3 payments.**

---

## 5. Why this reduces transactions

**Without optimisation**, each participant would pay back each payer for every shared expense. After netting pairs in both directions, the Pokhara example still leaves **10** separate person-to-person debts (the app shows this number as "direct payments" on the Balances page).

**With smart settlement** it takes **3** payments.

Why it's never worse than *n − 1* payments:

- Every payment brings **at least one** person to zero (it transfers the smaller of the two amounts).
- Once a person is at zero, they never appear again.
- With *n* unsettled people, after *n − 1* payments only one person can remain, and since the balances sum to zero that person must also be at zero.

So a group of 5 needs **at most 4** payments; the exact-match step often saves more. (Finding the absolute minimum number of payments in every case is an NP-hard problem. This greedy method is simple, fast, predictable and gives near-optimal plans for groups of friends.)

The automated tests check this on 200 random groups: every plan settles everyone exactly and never uses more than *n − 1* payments.

---

## 6. After a payment

1. The user picks a suggested payment and chooses **Cash**, **eSewa** or **Khalti**.
2. The backend checks that the payer really owes money, the recipient is really owed money, and the amount is not more than either.
3. Cash is recorded as successful immediately. eSewa and Khalti start as **pending** and become **successful** only after the simulation is confirmed or the gateway response is verified: eSewa checks the HMAC-SHA256 signature, and Khalti uses the lookup API.
4. Balances and the smart plan are **recalculated from the database** every time they are displayed, so the paid suggestion disappears automatically.

---

## 7. Individual balances ("between you and each member")

The Balances page also shows, for each other member:

- **You give / gives you**: your payments to or from them in the smart plan (what you actually need to do).
- **Shared expenses**: the expenses you both took part in, and who owes whom for each.
- A note when the direct debt differs from the smart plan. The smart plan may route money through other members, for example: you owe Ram, but you're asked to pay Sita, who owes Ram.
