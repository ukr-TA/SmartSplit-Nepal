# GitHub & Portfolio Guide

This guide covers:

- putting the project on GitHub with **meaningful commits**,
- choosing and placing screenshots,
- presenting the project in your portfolio.

> Commit honestly. Git records real dates, and reviewers sometimes check them. If your university asks, say that you used an AI assistant — and be ready to explain every part (the docs in this folder help with that).

## 1. One-time Git setup

```bash
git config --global user.name "Your Name"
git config --global user.email "the-email-on-your-github-account@example.com"
```

## 2. Create the repository

```bash
cd path/to/SmartSplit-Nepal
git init -b main
git status        # backend/.env, venv/, node_modules/ must NOT appear
git check-ignore backend/.env backend/venv frontend/node_modules   # should print all three
```

## 3. Commit in meaningful steps

Rather than `git add .` in one go, commit the project in logical parts. Each commit then shows one piece of work.

```bash
# 1 — project skeleton
git add .gitignore .editorconfig LICENSE .github backend/manage.py backend/requirements.txt backend/.env.example backend/config backend/common/__init__.py backend/common/money.py
git commit -m "chore: initialize Django project with PostgreSQL, env-based settings and CI"

# 2 — authentication
git add backend/users
git commit -m "feat: add custom user model and token authentication API"

# 3 — groups
git add backend/groups
git commit -m "feat: add group management, members and invitations"

# 4 — expenses and splitting
git add backend/expenses
git commit -m "feat: implement expense splitting (equal, custom, percentage) with receipts"

# 5 — balances, smart settlement, payments
git add backend/settlements
git commit -m "feat: add balance engine, smart settlement and eSewa/Khalti payments"

# 6 — activity and notifications
git add backend/notifications
git commit -m "feat: add activity timeline and notifications"

# 7 — test helpers
git add backend/common/testing.py
git commit -m "test: add shared API test helpers"

# 8 — frontend foundation
git add frontend/package.json frontend/package-lock.json frontend/vite.config.js frontend/index.html frontend/public frontend/.env.example frontend/.oxlintrc.json frontend/src/main.jsx frontend/src/api frontend/src/context frontend/src/hooks frontend/src/utils frontend/src/index.css
git commit -m "feat: set up React app with API client, auth context and design system"

# 9 — frontend screens
git add frontend/src
git commit -m "feat: add dashboard, groups, quick split, balances, payment hub and trip analytics UI"

# 10 — documentation
git add README.md SETUP.md documentation
git commit -m "docs: add setup guide, architecture, API and smart settlement documentation"

git status   # should say "nothing to commit"
git log --oneline
```

**From now on, commit each change as you make it.** Examples:

```bash
git commit -m "fix: resolve balance calculation issue"
git commit -m "style: improve dashboard UI"
git commit -m "docs: add screenshots to README"
```

## 4. Push to GitHub

1. Go to <https://github.com/new>. Name the repository `SmartSplit-Nepal` and add the description *"Nepal-focused group expense splitting & smart settlement app — Django REST Framework, React, PostgreSQL, eSewa/Khalti"*.
2. **Don't** add a README, .gitignore or license there — the project already has them.
3. Then run:

   ```bash
   git remote add origin https://github.com/YOUR-USERNAME/SmartSplit-Nepal.git
   git push -u origin main
   ```

   When Git asks for a password, use a **personal access token** (GitHub → Settings → Developer settings → Personal access tokens), not your account password.

4. On GitHub:
   - Add topics: `django`, `django-rest-framework`, `react`, `postgresql`, `nepal`, `esewa`, `khalti`, `expense-splitter`.
   - Pin the repository on your profile.

## 5. Screenshots — what to capture and where to put them

Save the images in `documentation/screenshots/` (PNG, around 1440×900, browser zoom 100%, with realistic demo data). The README already expects these file names; replace the included examples with your own captures.

| File | What to capture | Where it appears |
|------|-----------------|------------------|
| `dashboard.png` | Dashboard as **Mina** (shows "You need to give" and **You should pay**) | README hero image |
| `balances.png` | Pokhara Trip → Balances, with "How it works" open and the 3-vs-10 banner visible | README "Smart settlement" |
| `quick-split.png` | Split Expense → **Review** step of the Hotel expense | README "Quick split" |
| `payment-hub.png` | Payment Hub with Khalti selected | README "Payments" |
| `khalti.png` | Khalti simulation (MPIN entered) or the success screen | README "Payments" |
| `receipt.png` | Settlement receipt | README "Payments" |
| `analytics.png` | Trip Analytics tab (whole page) | README "Trip mode" |
| `invite.png` | Invite dialog with the QR code | README "Nepal-first" |
| `expenses.png` | Expenses tab timeline | README "Features" |
| `mobile.png` | Dashboard in iPhone view (crop to about 390px wide) | README "Responsive" |

**How to capture on macOS**

- **⌘⇧4**, then **Space**, then click the browser window.
- For full-page captures in Chrome/Brave: DevTools → **⌘⇧P** → "Capture full size screenshot".

## 6. Portfolio / CV wording

> **SmartSplit Nepal** — Group expense splitting and smart settlement web app. Built with Django REST Framework, PostgreSQL and React. Implemented equal, custom and percentage splits with exact paisa arithmetic; a balance engine and greedy debt-minimisation algorithm (≤ n−1 payments); token-authenticated REST API with membership-based permissions; eSewa (HMAC-signed) and Khalti sandbox payment flows with server-side verification; trip analytics, QR invitations and phone-number member discovery. 48 automated tests.

**LinkedIn:** post 3–4 screenshots (the dashboard, balances with the smart plan, the Khalti payment and trip analytics) with a short story: the problem → your algorithm → what you learned.

## 7. Before every push — checklist

```text
[ ] git status shows no .env, venv/, node_modules/, media/, .DS_Store
[ ] python manage.py test passes
[ ] npm run build succeeds
[ ] README describes only features that exist
[ ] No passwords or API keys in any committed file (search: git grep -i "secret")
    (the eSewa key in backend/config/settings.py is eSewa's *public* test key; that one is fine)
```
