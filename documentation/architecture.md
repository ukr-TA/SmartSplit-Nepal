# Architecture

SmartSplit Nepal is a **single-page React app** that talks to a **Django REST Framework API** over JSON. Data lives in **PostgreSQL**.

```text
┌──────────────────────────┐   HTTPS/JSON (Token auth)   ┌──────────────────────────────┐      SQL      ┌──────────────┐
│  React 19 + Vite (5173)  │ ─────────────────────────▶  │  Django 5.1 + DRF (8000)     │ ───────────▶ │ PostgreSQL   │
│  React Router, Axios     │ ◀─────────────────────────  │  apps: users, groups,        │ ◀─────────── │  smartsplit  │
│  Context: Auth, UI       │                             │  expenses, settlements,      │              └──────────────┘
└────────────┬─────────────┘                             │  notifications               │
             │  form POST / redirect (test gateways)     └──────────────┬───────────────┘
             ▼                                                          │ server-to-server verify
   eSewa ePay v2 test site / Khalti KPG-2 sandbox  ◀────────────────────┘
```

## Backend

| Package | Responsibility |
|---------|----------------|
| `config/` | settings (read from `.env`), root URLs, health check |
| `common/` | shared helpers: `money.py` (paisa maths, NPR formatting), `testing.py` |
| `users/` | custom `User` (email login, unique Nepali phone, picture), register/login/logout, profile, user search, `seed_demo` command |
| `groups/` | `Group`, `GroupMember`, `GroupInvitation`; member management, invites and joining, balances/suggestions/analytics endpoints |
| `expenses/` | `Expense`, `ExpenseSplit`; split calculation (`splitting.py`), preview, receipt upload |
| `settlements/` | `Settlement`; balance engine (`balances.py`), smart settlement (`algorithm.py`), eSewa/Khalti (`gateways.py`), dashboard |
| `notifications/` | `Activity` timeline, `Notification`; `services.py` helpers used by other apps |

**Layers inside each app**

- **models.py**: tables, relationships and database constraints.
- **serializers.py**: input validation and JSON output.
- **views.py**: ViewSets and APIViews, which handle permissions and orchestration.
- **Pure-logic modules** (`splitting.py`, `algorithm.py`): no database access, so they are easy to unit test.

**Key decisions**

- **Custom user model from the first migration.** Django can't easily swap user models later, and email plus phone login is needed from day one.
- **Token authentication (DRF authtoken).** It is simple for a React SPA: there are no cookies or CSRF tokens, logout deletes the token on the server, and a password change rotates it.
- **Balances are computed, not stored.** Net balances and the settlement plan are recalculated from expenses and successful settlements on every request. There is no stored "balance" column that could drift out of sync. For group sizes in this app, this costs only a few queries.
- **Integer paisa arithmetic.** Splits and balances are calculated in paisa so totals always match exactly.
- **Settlement validation mirrors the plan.** A payer must actually owe money, the recipient must actually be owed, and the amount can't exceed either. This keeps the data consistent without manual database edits.
- **Two payment channels.** *Simulation* (offline, used in the demo) and *sandbox* (the real eSewa/Khalti test environments). Both end in the same `complete_settlement()` function, which records the activity and the notification.
- **Permissions.** Every queryset is filtered to groups the requesting user belongs to. Non-members get `404`, so group IDs aren't revealed. Only owners can edit or delete groups and remove other members. Expenses can be edited by their creator, their payer or the group owner.
- **Privacy.** Other users are returned without their email, and with their phone masked (`98XXXX1234`). Phone search only matches a full 10-digit number, so numbers can't be enumerated.

## Frontend

```text
src/
├── api/          client.js (Axios, token, error messages) · services.js (every endpoint)
├── context/      AuthContext (session) · UIContext (toasts, confirm dialog)
├── hooks/        useApi (loading / error / reload)
├── components/   Layout, ui kit, ExpenseList, ExpenseDetailModal, SuggestionList,
│                 SettlementItem, Timeline, charts, Add/Invite/Group modals
├── pages/        Login, Register, Dashboard, Groups, GroupDetail (+ group/* tabs),
│                 SplitExpense (wizard), SettleUp (payment hub), PaySimulation,
│                 PaymentReturn, Receipt, Settlements, ActivityPage, Profile, JoinGroup
└── utils/        currency (NPR, en-IN grouping), format (dates), constants (categories, types)
```

- **Routing.** `RequireAuth` redirects to `/login?next=…`, so invite links still work after logging in. Wallet and receipt pages are full-screen, without the sidebar.
- **Quick Split wizard.** It has five steps: Details → Paid by → Split with → How to split → Review. The Review step calls `POST /api/expenses/preview/`, so the backend's own maths is shown before anything is saved.
- **Payment Hub.** You choose a method and a mode. The backend's response `next.type` decides what happens next: `done` (cash), `simulation` (the in-app wallet screen), `form_post` (a signed eSewa form is auto-submitted) or `redirect` (the Khalti `payment_url`).
- **Styling.** A single `index.css` with design tokens (brand teal, green for receive, red for give), responsive down to phone width with a bottom navigation bar, and a print style for receipts.
- **Charts.** Dependency-free CSS/SVG bars: one hue for magnitude, hover tooltips, and a table view for daily spending.

## Request flow example — adding an expense

1. The wizard collects the input and calls `/expenses/preview/`. The serializer validates the membership and calculates the shares, and the preview is shown.
2. **Confirm** calls `POST /expenses/`. It creates the `Expense` and its `ExpenseSplit` rows in a single database transaction, logs the activity, and notifies the participants.
3. If a receipt was chosen, it is uploaded with `POST /expenses/{id}/receipt/` (multipart).
4. The group's balances are recalculated automatically the next time they are displayed.
