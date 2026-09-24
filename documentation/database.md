# Database Design (PostgreSQL)

All tables are created by Django migrations (`python manage.py migrate`). Money columns are `NUMERIC(12,2)`.

## Entity–relationship overview

```text
User ─┬─< GroupMember >─┬─ Group ─┬─< GroupInvitation
      │                 │         ├─< Expense ─< ExpenseSplit >─ User
      │                 │         ├─< Settlement (payer → recipient: User)
      │                 │         ├─< Activity (actor: User)
      │                 │         └─< Notification (optional link)
      └─< Notification (recipient)
```

`─<` means one-to-many. `GroupMember` is the many-to-many link between users and groups, and it also stores each member's role.

## Tables

### users_user (`users.User`)

| Column | Type | Notes |
|--------|------|-------|
| id | bigint PK | |
| email | varchar, **unique** | login identifier (stored lowercase) |
| full_name | varchar(120) | |
| phone_number | varchar(10), **unique** | Nepali mobile, validated `^9[78]\d{8}$` |
| profile_picture | image path, nullable | `media/profile_pictures/` |
| password | hashed (PBKDF2) | |
| is_active, is_staff, is_superuser, date_joined, last_login | | from `AbstractUser` (no username field) |

### groups_group

| Column | Type | Notes |
|--------|------|-------|
| id | PK | |
| name | varchar(80) | |
| description | varchar(300) | |
| group_type | varchar | trip, college, friends, roommates, family, custom |
| is_trip | boolean | Trip Mode (forced true for type `trip`) |
| start_date, end_date | date, nullable | **check:** `end_date >= start_date` |
| created_by_id | FK → user (PROTECT) | |
| created_at, updated_at | timestamptz | |

### groups_groupmember

| Column | Type | Notes |
|--------|------|-------|
| group_id | FK → group (CASCADE) | |
| user_id | FK → user (CASCADE) | |
| role | owner / member | |
| joined_at | timestamptz | |
| | | **unique (group, user)** |

### groups_groupinvitation

| Column | Type | Notes |
|--------|------|-------|
| group_id | FK → group | |
| token | varchar, **unique** | 10 characters from an unambiguous alphabet, generated with `secrets` |
| created_by_id | FK → user | |
| expires_at | timestamptz | 7 days from creation |
| is_active | boolean | set to false when the link is regenerated |
| use_count | int | |

### expenses_expense

| Column | Type | Notes |
|--------|------|-------|
| group_id | FK → group (CASCADE) | indexed with `date` |
| description | varchar(120) | |
| amount | numeric(12,2) | **check:** `amount > 0` |
| category | varchar | food, transport, hotel, entertainment, shopping, education, utilities, rent, other |
| date | date | not in the future |
| paid_by_id | FK → user (PROTECT) | |
| split_method | equal / custom / percentage | |
| notes | text | |
| receipt | image path, nullable | `media/receipts/YYYY/MM/` |
| created_by_id | FK → user (PROTECT) | |
| created_at, updated_at | timestamptz | |

### expenses_expensesplit

| Column | Type | Notes |
|--------|------|-------|
| expense_id | FK → expense (CASCADE) | |
| user_id | FK → user (PROTECT) | |
| amount | numeric(12,2) | **check:** `amount >= 0` |
| percentage | numeric(5,2), nullable | only for percentage splits |
| | | **unique (expense, user)** |

The application guarantees that the sum of `amount` for an expense equals `expense.amount`.

### settlements_settlement

| Column | Type | Notes |
|--------|------|-------|
| group_id | FK → group | |
| payer_id, recipient_id | FK → user (PROTECT) | **check:** payer ≠ recipient |
| amount | numeric(12,2) | **check:** `amount > 0` |
| method | cash / esewa / khalti | |
| channel | cash / simulation / sandbox | how it was paid |
| status | pending / successful / failed | only **successful** rows affect balances |
| transaction_id | varchar, **unique** | e.g. `SMRT-KHL-20260916-X82K9` |
| gateway_reference | varchar | eSewa `transaction_code`, Khalti `pidx` / `transaction_id`, or the simulation reference |
| note | varchar(200) | |
| created_by_id | FK → user | |
| created_at, completed_at | timestamptz | |

### notifications_activity

Group timeline: `group`, `actor` (nullable), `action` (group_created, member_added, member_joined, member_removed, member_left, expense_added, expense_updated, expense_deleted, settlement), `description`, `amount`, `created_at`.

### notifications_notification

`recipient`, `kind` (expense, settlement, member, group), `title`, `message`, `group` (nullable), `is_read`, `created_at`. It is indexed on `(recipient, is_read)`.

### authtoken_token

DRF token table, with one token per user.

## Why `PROTECT` on users in money tables

Expenses, splits and settlements are financial history. `on_delete=PROTECT` stops a user from being deleted while their records exist, so balances can never silently change.

## Useful queries

```sql
-- total spent per group
SELECT g.name, SUM(e.amount) FROM expenses_expense e JOIN groups_group g ON g.id = e.group_id GROUP BY g.name;

-- every split adds up to its expense (should return no rows)
SELECT e.id, e.amount, SUM(s.amount)
FROM expenses_expense e JOIN expenses_expensesplit s ON s.expense_id = e.id
GROUP BY e.id HAVING SUM(s.amount) <> e.amount;

-- successful settlements
SELECT transaction_id, amount, method, status FROM settlements_settlement WHERE status = 'successful';
```

Run these with `psql -U smartsplit -d smartsplit -h localhost`.
