# REST API Reference

- **Base URL:** `http://127.0.0.1:8000/api`
- **Format:** JSON. Money is sent as strings such as `"1250.00"`, and dates as `YYYY-MM-DD`.
- **Authentication:** add `Authorization: Token <token>` to every request, except register, login and health.

## Conventions

| Status | Meaning |
|--------|---------|
| 200 / 201 | OK / created |
| 204 | deleted / logged out (no body) |
| 400 | validation error, e.g. `{"splits": ["Percentages must add up to 100% …"]}` or `["message"]` |
| 401 | missing or invalid token |
| 403 | logged in but not allowed (e.g. a non-owner editing a group) |
| 404 | not found, **or not a member of that group** |
| 429 | too many login/register attempts |

## Authentication & profile

| Method | Endpoint | Body | Notes |
|--------|----------|------|-------|
| POST | `/auth/register/` | `full_name, email, phone_number, password` | returns `{token, user}` |
| POST | `/auth/login/` | `identifier` (email **or** phone), `password` | returns `{token, user}` |
| POST | `/auth/logout/` | – | deletes the token (204) |
| POST | `/auth/change-password/` | `current_password, new_password` | returns a new `{token, user}` |
| GET | `/profile/` | – | own profile |
| PATCH | `/profile/` | any of `full_name, email, phone_number`; multipart `profile_picture`; `remove_picture: true` | |
| GET | `/users/search/?q=` | – | full 10-digit phone, exact email, or name (≥ 2 characters); other users' phones are masked |
| GET | `/health/` | – | public; API + database status |

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"identifier": "9800000001", "password": "SmartSplit@123"}'
```

## Groups

| Method | Endpoint | Body / notes |
|--------|----------|--------------|
| GET | `/groups/` | my groups, with `my_net`, `total_spent`, `member_count`, `members_preview` |
| POST | `/groups/` | `name, description, group_type, is_trip, start_date, end_date, member_ids[]` (I become the owner) |
| GET | `/groups/{id}/` | detail including `members[]` and `my_role` |
| PATCH | `/groups/{id}/` | owner only |
| DELETE | `/groups/{id}/` | owner only, and only when everyone is settled |
| POST | `/groups/{id}/members/` | `{user_id}` |
| DELETE | `/groups/{id}/members/{user_id}/` | owner removes a member, or a member leaves; that person's balance must be zero |
| POST | `/groups/{id}/invite/` | returns the active invite `{token, expires_at, use_count}`; `{"regenerate": true}` replaces it |
| GET | `/groups/join/{token}/` | invite preview |
| POST | `/groups/join/{token}/` | join the group |
| GET | `/groups/{id}/balances/` | see below |
| GET | `/groups/{id}/settlement-suggestions/` | `{suggestions[], direct_transactions, smart_transactions}` |
| GET | `/groups/{id}/activity/` | timeline (latest 100 entries) |
| GET | `/groups/{id}/analytics/` | trip analytics, see below |

**`GET /groups/{id}/balances/`**

```json
{
  "total_spent": 30500.0,
  "my_net": 5500.0,
  "you_give": [],
  "you_receive": [{"user": {"id": 5, "full_name": "Mina Rai"}, "amount": 5500.0}],
  "members": [{"user": {...}, "paid": 12000.0, "share": 6500.0, "settlements_paid": 0.0,
               "settlements_received": 0.0, "net": 5500.0, "status": "receive", "is_member": true}],
  "individual": [{"user": {...}, "you_give": 0.0, "you_receive": 5500.0, "direct_net": 2400.0,
                  "shared_expenses": [{"id": 1, "description": "Hotel", "direction": "they_owe", "amount": "2400.00"}]}],
  "suggestions": [{"from_user": {...}, "to_user": {...}, "amount": 2000.0}],
  "stats": {"direct_transactions": 10, "smart_transactions": 3, "is_settled": false}
}
```

**`GET /groups/{id}/analytics/`** returns `total_spent`, `days`, `average_per_day`, `average_per_person`, `by_category[] {category, amount, percentage, count}`, `by_member[] {user, paid, share}`, `daily[] {date, amount}` (with missing days filled with 0), and `top_expenses[]`.

## Expenses

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/expenses/?group=&category=&search=&limit=` | only groups I belong to |
| POST | `/expenses/preview/` | same body as create; returns the shares and balance effects **without saving** |
| POST | `/expenses/` | create |
| GET | `/expenses/{id}/` | detail including `splits[]`, `my_share`, `can_edit` |
| PATCH | `/expenses/{id}/` | creator, payer or group owner |
| DELETE | `/expenses/{id}/` | creator, payer or group owner |
| POST | `/expenses/{id}/receipt/` | multipart `receipt` (image, max 5 MB) |
| DELETE | `/expenses/{id}/receipt/` | remove the receipt |

**Create body**

```json
{
  "group": 1, "description": "Hotel", "amount": "12000", "category": "hotel",
  "date": "2026-09-12", "paid_by": 1, "notes": "",
  "split_method": "equal", "participants": [1, 2, 3, 4, 5]
}
```

```json
{ "split_method": "custom", "splits": [{"user": 1, "amount": "2000"}, {"user": 2, "amount": "1500"}] }
{ "split_method": "percentage", "splits": [{"user": 1, "percentage": "50"}, {"user": 2, "percentage": "50"}] }
```

**Validation rules**

- The payer and every participant must be members of the group.
- Custom amounts must add up exactly to the expense amount.
- Percentages must add up to exactly 100.
- The amount must be between Rs. 0.01 and Rs. 1 crore, with at most 2 decimal places.
- The date can't be in the future.

## Settlements & payments

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/settlements/?group=&status=&mine=1` | history |
| POST | `/settlements/` | see below |
| GET | `/settlements/{id}/` | receipt data |
| POST | `/settlements/{id}/confirm/` | simulation only; `{pin}` (4 digits for Khalti); payer only |
| POST | `/settlements/{id}/cancel/` | pending → failed |
| POST | `/settlements/{id}/verify-esewa/` | `{data}` (the base64 value eSewa returned) or `{failed: true}` |
| POST | `/settlements/{id}/verify-khalti/` | `{pidx}` |
| GET | `/payments/config/` | which test gateways are available |
| GET | `/dashboard/` | totals, what to pay and receive, recent expenses, settlements and activity |

**Create body**

```json
{ "group": 1, "recipient": 3, "amount": "2000", "method": "esewa", "channel": "simulation", "note": "" }
```

- `method` is one of `cash`, `esewa` or `khalti`.
- `channel` applies to eSewa and Khalti only: `simulation` (the default) or `sandbox` (the real test gateway).
- `payer` is optional and defaults to me. A **recipient** can record cash they received by setting `payer` to the other person.
- **Rules:**
  - The payer must owe money in the group.
  - The recipient must be owed money.
  - `amount ≤ min(what the payer owes, what the recipient is owed)`.
  - Khalti's test gateway needs at least Rs. 10.

**The response tells the frontend what to do next**

```json
{ "settlement": { "id": 7, "transaction_id": "SMRT-ESW-20260917-K3PQA", "status": "pending", ... },
  "next": { "type": "simulation" } }
```

| `next.type` | Meaning |
|-------------|---------|
| `done` | cash, already successful |
| `simulation` | open `/pay/{id}`, the in-app wallet screen |
| `form_post` | auto-submit a form to `next.url` with `next.fields` (eSewa ePay v2, HMAC-SHA256 signed) |
| `redirect` | send the browser to `next.url` (Khalti `payment_url`) |

Settlement `status` is one of `pending`, `successful` or `failed`. **Only successful settlements change balances.**

## Notifications & activity

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/notifications/` | `{unread_count, results[]}` (latest 50) |
| PATCH | `/notifications/{id}/` | `{is_read: true}` |
| POST | `/notifications/mark-all-read/` | |
| GET | `/activity/` | timeline across all my groups |


## Machine learning

### `POST /api/ml/suggest-category/`

Suggest a category for an expense description. Requires authentication.

```json
{ "description": "Tourist bus Kathmandu to Pokhara", "amount": 1400 }
```

```json
{
  "category": "transport",
  "confidence": 0.9912,
  "alternatives": [
    { "category": "hotel", "confidence": 0.0031 },
    { "category": "other", "confidence": 0.0018 }
  ],
  "source": "model"
}
```

`source` is `model` when the trained classifier answered, `keyword` when the model file was not
available and the keyword fallback was used, and `empty` for a blank description.

### `GET /api/groups/{id}/forecast/`

What the group might spend next month, and why. Requires group membership. The app shows
`explanation.summary` (one or two sentences); the other fields are the details behind it.

```json
{
  "ready": true,
  "month": "2026-10",
  "predicted_total": 73842.13,
  "lower": 44305.28,
  "upper": 103378.99,
  "model": "Random Forest",
  "source": "model",
  "group_type": "roommates",
  "history": [{ "month": "2026-09", "total": 39000.0, "count": 9 }],
  "explanation": {
    "summary": "You've spent Rs. 39,000 in September so far, mostly on rent. October might come in higher, around Rs. 73,842, with Dashain on 11–25 Oct.",
    "headline": "October might cost around Rs. 73,842, possibly about 60% more than your recent monthly average.",
    "direction": "up",
    "change_vs_average": 0.6,
    "recent_average": 46151.33,
    "this_month": {
      "month": "2026-09", "total": 39000.0, "partial": true, "projected_total": 47894.0,
      "top_categories": [{ "category": "rent", "amount": 30000.0, "share": 0.769 }]
    },
    "events_next_month": [
      { "name": "Dashain", "start": "2026-10-11", "end": "2026-10-25", "peak": "2026-10-21",
        "scale": "major", "spending": "new clothes, khasi meat, tika dakshina and bus tickets home" }
    ],
    "events_ending": ["Haritalika Teej"],
    "same_month_last_year": 52910.0,
    "capped": true,
    "reasons": ["This group has spent Rs. 39,000 in September so far, mostly on rent (77%) ...", "..."]
  }
}
```

With fewer than four months of expenses the response is `{"ready": false, "reason": "...",
"history": [...]}`.

### `GET /api/ml/info/`

Reports whether each model is loaded, the category list, and the metrics recorded by the notebook.
Useful for checking a deployment, and for marking the project.
