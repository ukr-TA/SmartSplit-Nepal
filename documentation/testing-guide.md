# Testing Guide — What to Click and What You Should See

**Before you start**

- Both servers are running (see SETUP.md section 5).
- The demo friends exist (run `python manage.py seed_demo` once).
- Demo friends: Ram 9800000001 · Sita 9800000002 · Hari 9800000003 · Mina 9800000004 · Bikash 9800000005. Their password is `SmartSplit@123`.

**Tip:** to act as two people at once, use a normal browser window for yourself and a **private/incognito** window for a friend. Each window keeps its own login.

## Automated tests

```bash
cd backend && source venv/bin/activate
python manage.py test
```

Expected: `Ran 71 tests … OK`.

---

## Test 1 — Registration

1. Open <http://localhost:5173> and click **Create an account**.
2. Fill in:
   - Name: `Utsuk Kharel`
   - Email: `utsuk@example.com`
   - Mobile: `9812345678`
   - Password and confirmation: `Kathmandu@2026`
3. Click **Create account**.

✅ **Expected:** the toast "Account created successfully", then the Dashboard showing "Namaste, Utsuk" and an empty state "Start your first group".

**Negative checks:**

- Phone `12345` → "Enter a 10-digit Nepali mobile number".
- Registering the same phone again → "This phone number is already registered".
- Password `password` → "This password is too common".

## Test 2 — Login / logout

1. In the sidebar, click **Log out** and confirm.
2. Log in with `9812345678` and a **wrong** password.
   - ✅ "Incorrect email/phone or password."
3. Log in with the correct password. Logging in with your email also works.
   - ✅ The Dashboard opens.
4. Refresh the page.
   - ✅ You stay logged in.

## Test 3 — Create a group

1. Click **Dashboard → New group**.
2. Name it `Pokhara Trip`, and choose the type **Trip**. Trip Mode switches on automatically.
3. Set Start `12 Sep 2026` and End `15 Sep 2026`, then click **Create group**.

✅ **Expected:**

- The group page opens with the **Add members** window.
- "Pokhara Trip" appears in **Groups → My Groups** with a *Trip* label.

**Negative check:** an end date before the start date → "End date cannot be before the start date."

## Test 4 — Add members (phone-based discovery)

1. In **Add members**, type `98000`.
   - ✅ "Keep typing — enter all 10 digits". Partial numbers are hidden for privacy.
2. Type `9800000001`.
   - ✅ Ram Sharma appears with a masked phone, `98XXXX0001`. Click **Add**.
   - ✅ The toast "Ram Sharma added to Pokhara Trip", and the button changes to *Member*.
3. Add Sita (`9800000002`), then search by name `Hari`, and by email `mina@smartsplit.np`.
4. Click **Done**.

✅ **Expected:** the header shows **5 members**, and the **Members** tab lists everyone, with you as *Owner*.

## Test 5 — QR invitation

1. On the group page, click **Invite**.
   - ✅ A QR code, a 10-character invite code, a link like `http://localhost:5173/join/ABCD234XYZ`, and a **Copy** button.
2. Click **Copy**.
   - ✅ The toast "Invite link copied".
3. **Do this step at the very end (after Test 18),** so the balance numbers in Tests 9–15 stay the same. In a private window, open the link and log in as Bikash (`9800000005`).
   - ✅ The page "You're invited — Pokhara Trip". Click **Join group**.
   - ✅ The group opens with 6 members.
4. Back as Utsuk:
   - The **Activity** tab shows "Bikash Tamang joined the group".
   - The bell shows a notification.

## Test 6 — Expense with equal split + receipt

1. Click **+ Split Expense** (on the group page).
2. **Details:** Description `Hotel`, Amount `12000`, Category **Hotel**, Date `12 Sep 2026`. Click **Next**.
3. **Paid by:** You. Click **Next**.
4. **Split with:** everyone. The screen shows "about Rs. 2,400 each". Click **Next**.
5. **How to split:** Equally. Click **Review**.
   - ✅ Review shows Total Rs. 12,000, your share Rs. 2,400, and your balance effect **+Rs. 9,600**. Everyone else shows −Rs. 2,400.
6. Click **Attach receipt**, choose any photo, then click **Confirm & add expense**.
   - ✅ The toast "Hotel added · Rs. 12,000", then the Expenses tab.
7. Click the Hotel card.
   - ✅ The details show the receipt thumbnail. Clicking it enlarges it.

## Test 7 — Custom split

1. Add `Taxi & bus`, Rs. `8000`, Transport, paid by **Sita**.
2. In **How to split**, choose **Custom amounts**. Enter You `2000`, and everyone else `1500` (with 5 people).
   - Enter a wrong total first.
   - ✅ You see the orange "Rs. X left" message, and **Review** shows "Custom amounts must add up to Rs. 8,000".
3. Fix the amounts, then click **Review → Confirm**.

## Test 8 — Percentage split

1. Add `Paragliding`, Rs. `4000`, Entertainment, paid by **Hari**.
2. Choose **Percentages**.
   - Enter `50` for one person only.
   - ✅ Review shows "Percentages must add up to 100% (currently 50%)".
3. Click **Fill equally**, or enter 20 for everyone. Then click **Review → Confirm**.

Also add `Dinner at Lakeside`, Rs. `6500`, Food, paid by **Ram**, split **equally**.

## Test 9 — View balances

Open the **Balances** tab. With the 5 original members and the 4 expenses above:

| Person | Group balance |
|--------|---------------|
| You (Utsuk) | receives Rs. 5,500 |
| Sita | receives Rs. 2,000 |
| Ram | receives Rs. 500 |
| Hari | gives Rs. 2,000 |
| Mina | gives Rs. 6,000 |

✅ **Suggested settlements:**

- **Hari → Sita Rs. 2,000**
- **Mina → You Rs. 5,500**
- **Mina → Ram Rs. 500**

The banner reads "Smart settlement needs 3 payments instead of 10".

Also check:

- Click **How it works** to see the algorithm explained.
- Under **Your balance with each member**, "Mina Rai — Gives you Rs. 5,500". Expand it to see your shared expenses.

## Test 10 — Khalti simulation

1. In a private window, log in as **Mina** (`9800000004`).
   - ✅ The Dashboard shows "You need to give Rs. 6,000", and **You should pay** lists Utsuk (Rs. 5,500) and Ram (Rs. 500).
2. Click **Settle** next to Utsuk.
   - ✅ The Payment Hub shows "Settle with Utsuk Kharel" and Amount Rs. 5,500.
3. Choose **Khalti**. The mode should be **Demo simulation**. Click **Continue**.
   - ✅ The purple Khalti Payment screen shows Recipient, Amount, and a Transaction ID like `SMRT-KHL-20260917-XXXXX`.
4. Enter MPIN `1111` and click **Confirm Payment**.
   - ✅ After about a second: "Payment Successful", with the transaction ID and a Khalti reference.
5. Click **View receipt**.
   - ✅ A printable receipt. **Print / Save PDF** works.

## Test 11 — eSewa simulation

1. Log in as **Hari** (`9800000003`).
2. On the Dashboard, click **Settle** (Sita, Rs. 2,000), choose **eSewa**, keep *Demo simulation*, and click **Continue**.
3. Click **Confirm Payment**.
   - ✅ The green eSewa screen, then "Payment Successful" with a transaction ID starting `SMRT-ESW-`.

## Test 12 — Cash settlement

**Option A**

1. As Mina, open Pokhara Trip → **Balances**.
2. Click **Settle** next to Ram (Rs. 500), choose **Cash**, and click **Mark as paid**.
   - ✅ The receipt shows "Payment Successful" and Method *Cash*.

**Option B**

1. As **Utsuk**, find a suggestion where you *receive* money.
2. Click **Record cash**, then **Mark as received**.

## Test 13 — Updated balances

1. As Utsuk, open **Balances**.
   - ✅ "Everyone is settled up" (if all three payments were made).
   - ✅ Every member shows *settled*.
2. Open the Dashboard.
   - ✅ You need to give Rs. 0 / You will receive Rs. 0 / Net Rs. 0.

**Negative check:** try to settle again (for example, visit a Settle link from history).

- ✅ The page says "Nothing to settle".
- The backend also rejects over-payments with "The most that can be settled here is …".

## Test 14 — Settlement history

1. Open the group's **Settlements** tab, or **Settlements** in the sidebar.
   - ✅ Each entry shows who paid whom, the amount, the method badge, the date/time, the transaction ID, a *Successful* status, and a **Receipt** link.
2. Try the filters (I paid / I received, method, status).
3. Test a cancelled payment (do this **before** the last payment in Test 12, while someone still owes money):
   1. Start a Khalti simulation.
   2. Click **Cancel** and confirm.
   - ✅ It appears as *Failed*, and the balances didn't change.

## Test 15 — Trip analytics

Open the **Trip Analytics** tab.

✅ **Expected:**

- The trip banner shows **Total spending Rs. 30,500** and "12 Sept – 15 Sept 2026 · 4 days".
- Average per day and average per person.
- **Spending by category**: Hotel 39.3%, Transport 26.2%, Food 21.3%, Entertainment 13.1%.
- **Spending by member**: bars show what each person paid, with a black tick for their fair share.
- **Daily spending**: columns for Sep 12–15. Hover to see the amount, and click **Show table** for a table.

## Test 16 — Notifications & activity

1. As Utsuk, click the **bell**.
   - ✅ Notifications such as "Mina Rai … Settlement received · paid you Rs. 5,500 via Khalti" and "New member joined".
2. Click one.
   - ✅ It opens the group, and the unread count drops.
3. Open **Activity** in the sidebar.
   - ✅ A timeline across your groups: expenses added, members joined, settlements.
4. Open the **Notifications** tab and click **Mark all read**.

## Test 17 — Edit / delete expense and permissions

1. As Utsuk, open an expense you added, click **Edit**, change the amount, and save.
   - ✅ The balances update.
2. As Mina, open an expense Utsuk added.
   - ✅ There are no Edit/Delete buttons (Mina isn't the creator, payer or owner).
3. As Utsuk, try **Delete group** while balances are unsettled.
   - ✅ "This group still has unsettled balances."

## Test 18 — Profile

1. Click **Profile → camera icon** and choose a photo.
   - ✅ "Profile picture updated", and the avatar changes everywhere.
2. Change your name and click **Save changes**.
3. Change your password.
   - Log out and back in with the new password.

## Test 19 — Mobile layout

In Chrome/Brave, open **View → Developer → Developer Tools**, then the device toolbar (**⌘⇧M**), and choose an iPhone.

✅ **Expected:**

- The sidebar is replaced by a bottom navigation bar with a round **+** button.
- The cards stack vertically.
- There is no sideways scrolling.

## Test 20 — Backend offline handling

1. Stop the backend (Ctrl + C) and refresh the app.
   - ✅ A red "Cannot reach the SmartSplit server. Is the backend running on port 8000?" message with a **Try again** button.
2. Start the backend again and click **Try again**.

## Optional — real test gateways

Follow SETUP.md section 7.

**eSewa**

1. In the Payment Hub, choose **eSewa → eSewa test gateway → Continue**.
   - ✅ You are redirected to `rc-epay.esewa.com.np`.
2. Log in with `9806800001` / `Nepal@123`, use token `123456`, and pay.
   - ✅ You are sent back to SmartSplit, you see "Verifying your eSewa payment…", and then the receipt, with Mode *Gateway test environment*.

**Khalti** (needs the key): pay with `9800000001`, MPIN `1111`, OTP `987654`.

---

## Machine-learning features

| # | Step | Expected result |
|---|------|-----------------|
| 1 | **Split Expense** → type `Tourist bus Kathmandu to Pokhara` in "What was it for?" | After about half a second a dashed box appears: *Suggested category: Transport · 99% confident* |
| 2 | Click **Use this** | Transport becomes the selected category and the suggestion disappears |
| 3 | Type `Momo at Bajeko Sekuwa` instead | No suggestion appears, because the model agrees with the default category (Food) |
| 4 | Click **No thanks** on any suggestion | It disappears for that description and does not come back |
| 5 | Open a group with at least 4 months of expenses (seed with `seed_demo --owner … --history 13`) → **Overview** | A **Spending forecast** card shows what next month might cost, a range, and a dashed bar after the history bars |
| 5a | Read the line under the chart | One or two sentences: what the group spent this month and mostly on what, and whether next month might be higher or lighter, naming the festival if there is one (for October 2026: *Dashain on 11–25 Oct*). It says *might*, never *will* |
| 6 | Open a brand-new group → **Overview** | The forecast card says there is not enough history yet |
| 7 | `curl -H "Authorization: Token <token>" http://127.0.0.1:8000/api/ml/info/` | Reports `classifier_available: true`, `forecaster_available: true` and the notebook's metrics |
| 8 | Rename `ml/models` temporarily, restart the backend, repeat steps 1 and 5 | The app still works: the suggestion comes from keywords (`source: keyword`) and the forecast says *Average of last 3 months (fallback)* |
