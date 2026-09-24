# SmartSplit Nepal - Complete Setup Guide (macOS)

This guide takes you from a clean Mac to a running SmartSplit Nepal app, step by step.
It assumes you are still learning - every command is written out in full.

- Type commands into the **Terminal** app (or the terminal inside VS Code: *View → Terminal*).
- Lines starting with `#` are comments - you don't need to type them.
- `path/to/SmartSplit-Nepal` means *the folder where you extracted the project*.

**Contents**

1. [Prerequisites](#1-prerequisites)
2. [PostgreSQL](#2-postgresql)
3. [Backend (Django)](#3-backend-django)
4. [Frontend (React)](#4-frontend-react)
5. [Running the complete application](#5-running-the-complete-application)
6. [Optional: demo data](#6-optional-demo-data)
7. [Optional: real eSewa / Khalti test gateways](#7-optional-real-esewa--khalti-test-gateways)
8. [First-time setup checklist](#8-first-time-setup-checklist)
9. [Testing the application](#9-testing-the-application)
10. [Troubleshooting](#10-troubleshooting)
11. [Reset / reinstall](#11-reset--reinstall)

---

## 1. Prerequisites

| Tool | Version needed | Check with |
|------|----------------|------------|
| Python | **3.10 or newer** (3.12 / 3.13 recommended) | `python3 --version` |
| Node.js | **20.19+ or 22.12+** | `node --version` |
| npm | comes with Node.js | `npm --version` |
| PostgreSQL | **14 or newer** | `psql --version` |

Run all four checks:

```bash
python3 --version
node --version
npm --version
psql --version
```

### 1.1 If something is missing

The easiest installer on macOS is **Homebrew**. Check it with `brew --version`; if it's missing, copy the install command from <https://brew.sh> and run it.

| Missing | Install command |
|---------|-----------------|
| Python (or version is 3.9) | `brew install python@3.12` |
| Node.js / npm (or version too old) | `brew install node@22` |
| PostgreSQL | **Postgres.app** from <https://postgresapp.com> (recommended), or `brew install postgresql@16` |

> ⚠️ macOS ships with **Python 3.9**, which is too old for Django 5.1. If `python3 --version` shows 3.9 after installing, use `python3.12` everywhere this guide says `python3`.

After installing anything, **close the Terminal window and open a new one**, then run the version checks again.

---

## 2. PostgreSQL

SmartSplit stores everything in a PostgreSQL database called `smartsplit`.

### 2.1 Start PostgreSQL

Pick the section that matches how PostgreSQL is installed on your Mac.

**Postgres.app (recommended)**

1. Open **Postgres.app** from Applications.
2. Click **Start** (or check that the elephant icon in the menu bar says *Running*).
3. In Postgres.app → **Settings**, tick **Automatically start at login** so you never forget.
4. Make its command-line tools available (one time only):

   ```bash
   sudo mkdir -p /etc/paths.d && echo /Applications/Postgres.app/Contents/Versions/latest/bin | sudo tee /etc/paths.d/postgresapp
   ```

   Close and reopen Terminal afterwards.

**Homebrew**

```bash
brew services start postgresql@16
```

**Official installer (EnterpriseDB, comes with pgAdmin)** - it starts automatically at boot. Add its tools to your PATH once:

```bash
echo 'export PATH="/Library/PostgreSQL/17/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

> Only run **one** PostgreSQL server at a time - they all want port **5432**.

### 2.2 Check it's running

```bash
pg_isready -h localhost -p 5432
```

Expected: `localhost:5432 - accepting connections`.
If you see `no response`, PostgreSQL isn't running - go back to 2.1.

To see *which* PostgreSQL is answering:

```bash
lsof -nP -iTCP:5432 -sTCP:LISTEN
```

### 2.3 Create the database and a database user

Open the PostgreSQL shell as an administrator:

```bash
# Postgres.app / Homebrew (admin user = your Mac username):
psql postgres

# Official installer (admin user is "postgres", asks for the password you chose when installing):
psql -U postgres -h localhost
```

The prompt changes to `postgres=#`. Type these lines one at a time (choose your own password - letters and numbers only keeps things simple):

```sql
CREATE USER smartsplit WITH PASSWORD 'smartsplit_pass123' CREATEDB;
CREATE DATABASE smartsplit OWNER smartsplit;
\q
```

What they do:

- `CREATE USER …` creates a login just for this app. `CREATEDB` lets Django create a temporary database when running tests.
- `CREATE DATABASE …` creates the empty `smartsplit` database, owned by that user.
- `\q` quits the PostgreSQL shell.

Expected output: `CREATE ROLE` then `CREATE DATABASE`.
(If you see `role "smartsplit" already exists`, that's fine - just run the second line.)

### 2.4 Verify the new login works

```bash
psql -U smartsplit -d smartsplit -h localhost -c "SELECT current_user, version();"
```

Expected: a small table showing `smartsplit` and your PostgreSQL version.

---

## 3. Backend (Django)

### 3.1 Create the Python virtual environment and install packages

```bash
cd path/to/SmartSplit-Nepal/backend
python3 -m venv venv              # creates an isolated Python environment in the "venv" folder
source venv/bin/activate          # switches this Terminal into it - the prompt now starts with (venv)
python --version                  # should be 3.10 or newer
pip install --upgrade pip
pip install -r requirements.txt   # Django, Django REST Framework, psycopg2, Pillow, …
```

Expected last line: `Successfully installed … Django-5.1.x … djangorestframework-3.x … psycopg2-binary-2.9.x …`

> **Every new Terminal window** needs `cd path/to/SmartSplit-Nepal/backend` and `source venv/bin/activate` before any `python manage.py …` command.
> If VS Code asks *"select the new environment for the workspace?"* click **Yes**.
> If your prompt shows `(base)` from Anaconda, run `conda deactivate` first.

### 3.2 Create the `.env` settings file

`.env` holds your private settings (secret key, database password). It is **never** committed to Git.

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(50))"
open -e .env
```

TextEdit opens `.env`. Change these lines and save:

| Line | Set it to |
|------|-----------|
| `SECRET_KEY=` | the long random text printed by the second command |
| `DATABASE_USER=` | `smartsplit` |
| `DATABASE_PASSWORD=` | the password from step 2.3 |

Leave everything else as it is. (Alternative without TextEdit - this one command fills in both values automatically; change the password if yours is different:)

```bash
python - <<'EOF'
import secrets
t = open(".env.example").read()
t = t.replace("replace-me-with-a-long-random-string", secrets.token_urlsafe(50))
t = t.replace("DATABASE_PASSWORD=your-password", "DATABASE_PASSWORD=smartsplit_pass123")
open(".env", "w").write(t)
print(".env created")
EOF
```

### 3.3 Create the database tables

```bash
python manage.py migrate
```

Expected: about 30 lines ending in `... OK` (users, groups, expenses, settlements, notifications…).

### 3.4 (Optional) Admin account

```bash
python manage.py createsuperuser
```

It asks for email, full name, phone number (10 digits starting with 97 or 98) and a password.
Admin panel: <http://127.0.0.1:8000/admin/>

### 3.5 (Optional) Run the automated tests

```bash
python manage.py test
```

Expected: `Ran 71 tests … OK`.

---

## 4. Frontend (React)

Open a **second** Terminal window (in VS Code: the **+** button on the terminal panel):

```bash
cd path/to/SmartSplit-Nepal/frontend
npm install        # downloads React, Vite, etc. into node_modules (about a minute, first time only)
```

Expected: `added … packages` and `found 0 vulnerabilities`.

---

## 5. Running the complete application

You need **two terminals running at the same time**.

**Terminal 1 - backend**

```bash
cd path/to/SmartSplit-Nepal/backend
source venv/bin/activate
python manage.py runserver
```

Expected:

```text
System check identified no issues (0 silenced).
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

**Terminal 2 - frontend**

```bash
cd path/to/SmartSplit-Nepal/frontend
npm run dev
```

Expected:

```text
VITE v8.x.x  ready in … ms
➜  Local:   http://localhost:5173/
```

**Open <http://localhost:5173> in your browser.**
The login page shows a green **"Server connected"** dot at the bottom when the backend is reachable.

To stop a server, click its terminal and press **Ctrl + C**.

---

## 6. Optional: demo data

Creates five demo friends you can add to groups (all use password **`SmartSplit@123`**):

| Name | Phone | Email |
|------|-------|-------|
| Ram Sharma | 9800000001 | ram@smartsplit.np |
| Sita Thapa | 9800000002 | sita@smartsplit.np |
| Hari Gurung | 9800000003 | hari@smartsplit.np |
| Mina Rai | 9800000004 | mina@smartsplit.np |
| Bikash Tamang | 9800000005 | bikash@smartsplit.np |

```bash
cd path/to/SmartSplit-Nepal/backend
source venv/bin/activate
python manage.py seed_demo
```

Want ready-made sample groups (College Project, Kathmandu Flat, Friends Hangout, Pokhara Trip (Sample)) in **your** account? Register in the app first, then:

```bash
python manage.py seed_demo --owner your-email@example.com
```

Kathmandu Flat also gets 13 months of past bills and festival spending, settled at the end of each
month, so the spending forecast has history to learn from. To start the sample groups again from
scratch, add `--reset`.

Or put them in a separate demo account (`demo@smartsplit.np` / `SmartSplit@123`):

```bash
python manage.py seed_demo --with-groups
```

The command is safe to run more than once.

By default it also adds **13 months of past bills and festival spending** (Dashain, Tihar, Teej,
New Year and more, on their real dates) to the Kathmandu Flat group, so the machine-learning
spending forecast has a year of history to work from and can compare with the same month last year.
Change it with `--history 18`, or turn it off with `--history 0`.

---

## 7. Machine learning: the models

The trained models ship with the project in `ml/models/`, so **nothing extra is needed to run the
app**. The category suggestion in the Quick Split wizard and the spending forecast (with its one-line
reason) on a group's Overview tab work as soon as the backend is running. If the model files are ever missing, the app
keeps working: category suggestions fall back to keyword matching and the forecast falls back to a
three-month average.

To retrain them yourself, or to look through the notebook:

```bash
cd path/to/SmartSplit-Nepal
source backend/venv/bin/activate
pip install -r ml/requirements.txt

python ml/build_dataset.py                          # rebuild the dataset (same output every time)
jupyter notebook ml/notebooks/smartsplit_ml.ipynb   # then Run All
```

Running the notebook rewrites `ml/models/`. Restart the backend afterwards so it loads the new
models. Full details of the dataset and the evaluation are in
[documentation/machine-learning.md](documentation/machine-learning.md).

---

## 8. Optional: real eSewa / Khalti test gateways

SmartSplit has two payment modes for eSewa and Khalti:

| Mode | What happens | Needs internet? | Needs keys? |
|------|--------------|-----------------|-------------|
| **Demo simulation** (default) | An in-app wallet screen confirms the payment and generates a mock transaction ID | No | No |
| **Test gateway** | You are redirected to the wallet's official **test** website, pay with test credentials, and are sent back; the backend verifies the payment | Yes | eSewa: no · Khalti: yes |

No real money moves in either mode. You choose the mode on the Payment Hub screen.

### eSewa (works out of the box)

eSewa publishes public test credentials, already configured in `backend/config/settings.py`.
On the eSewa test site, log in with:

- eSewa ID: `9806800001` (or …0002 to …0005)
- Password: `Nepal@123`
- MPIN: `1122`
- Token / OTP: `123456`

To hide the eSewa test gateway option, set `ESEWA_ENABLED=False` in `backend/.env`.

### Khalti (needs a free test key)

1. Go to <https://test-admin.khalti.com/#/join/merchant> and sign up as a merchant (use any test details; the OTP for the sandbox is `987654`).
2. Log in and find **Keys** in the dashboard. Copy the **Live Secret Key** shown in the *test* dashboard - it is a sandbox key.
3. Open `backend/.env` and set:

   ```env
   KHALTI_SECRET_KEY=paste-your-test-secret-key-here
   ```

4. Restart the backend (Ctrl + C, then `python manage.py runserver`).
5. On the Khalti test checkout, pay with Khalti ID `9800000001` (…0000 to …0005), MPIN `1111`, OTP `987654`.

Khalti's minimum payment is **Rs. 10**.

> Never commit `.env` or share your key. The key in the *test* dashboard cannot move real money, but treat it as private anyway.

---

## 9. First-time setup checklist

```text
[ ] Python 3.10+ installed          (python3 --version)
[ ] Node.js 20.19+/22.12+ installed (node --version)
[ ] npm installed                   (npm --version)
[ ] PostgreSQL installed            (psql --version)
[ ] PostgreSQL running              (pg_isready -h localhost → accepting connections)
[ ] Project extracted
[ ] Backend virtual environment created   (backend/venv exists)
[ ] Backend dependencies installed        (pip install -r requirements.txt)
[ ] Frontend dependencies installed       (frontend/node_modules exists)
[ ] backend/.env created and filled in
[ ] PostgreSQL database "smartsplit" created
[ ] Django migrations completed           (python manage.py migrate)
[ ] Backend started                       (http://127.0.0.1:8000/api/health/ shows "status": "ok")
[ ] Frontend started                      (npm run dev)
[ ] Application opened                    (http://localhost:5173, "Server connected")
[ ] Registration tested
[ ] Login tested
```

---

## 10. Testing the application

A click-by-click test plan (registration, groups, every split type, balances, smart settlement, cash / eSewa / Khalti, history, analytics, receipts, notifications, QR invites) is in
**[documentation/testing-guide.md](documentation/testing-guide.md)**.

The 5–10 minute presentation script is in
**[documentation/demo-guide.md](documentation/demo-guide.md)**.

---

## 11. Troubleshooting

### Backend does not start

```bash
python3 --version     # must be 3.10+
which python          # after "source venv/bin/activate" this must end in backend/venv/bin/python
pip list              # Django, djangorestframework, psycopg2-binary, Pillow… must be listed
```

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: No module named 'django'` | The virtual environment isn't active: `source venv/bin/activate` (then check `which python`). |
| `ImproperlyConfigured: Missing environment variable 'SECRET_KEY'` | `backend/.env` is missing - do step 3.2. |
| `SyntaxError` / `requires Python 3.10` | venv was made with Python 3.9. Delete `backend/venv` and recreate it with `python3.12 -m venv venv`. |
| `command not found: python` | Activate the venv, or use `python3`. |

### PostgreSQL connection error

`connection to server at "localhost" … failed: Connection refused`
→ PostgreSQL isn't running. `pg_isready -h localhost` must say *accepting connections* (step 2.1).

`password authentication failed for user "smartsplit"`
→ The password in `backend/.env` doesn't match step 2.3. Reset it:

```bash
psql postgres                                          # or: psql -U postgres -h localhost
ALTER USER smartsplit WITH PASSWORD 'smartsplit_pass123';
\q
```

`database "smartsplit" does not exist` → run the `CREATE DATABASE` line from step 2.3.

`role "smartsplit" does not exist` → run both lines from step 2.3.

Check `.env` is right: `cat .env` inside `backend/` (the `DATABASE_…` lines).

### Migration error

```bash
python manage.py showmigrations     # [X] = applied, [ ] = not applied
python manage.py migrate
```

`permission denied for schema public` (PostgreSQL 15+) → make the app user the owner:

```bash
psql postgres -c "ALTER DATABASE smartsplit OWNER TO smartsplit;"
```

If migrations are badly broken during development, use the database reset in section 11.

### Frontend dependency error

```bash
cd path/to/SmartSplit-Nepal/frontend
node --version                  # 20.19+ or 22.12+
rm -rf node_modules
npm install
npm run dev
```

`Vite requires Node.js version …` → upgrade Node: `brew install node@22`.

### CORS / API connection problem

- The red **"Cannot reach the SmartSplit server"** / "Server offline" message means the frontend can't reach the backend.
- Backend must be at **http://127.0.0.1:8000** (Terminal 1 running), frontend at **http://localhost:5173**.
- Open <http://127.0.0.1:8000/api/health/> directly - it should show `"status": "ok"`.
- CORS: `backend/.env` → `CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`. Restart the backend after changing it.
- Browser developer console: **View → Developer → JavaScript Console** (Chrome/Brave) or **Develop → Show JavaScript Console** (Safari). A message containing `CORS` means the frontend address isn't in `CORS_ALLOWED_ORIGINS`.
- If the backend runs somewhere else, create `frontend/.env` with `VITE_API_BASE_URL=http://127.0.0.1:8000/api` (adjust) and restart `npm run dev`.

### Port already in use

```bash
lsof -i :8000        # who is using the backend port
lsof -i :5173        # who is using the frontend port
kill <PID>           # stop it (PID is the number in the second column)
```

Or run the backend on another port: `python manage.py runserver 8001` - then create `frontend/.env` with `VITE_API_BASE_URL=http://127.0.0.1:8001/api` and restart the frontend.
The frontend port is fixed to **5173** on purpose (CORS and payment return URLs depend on it). If you must change it, edit `frontend/vite.config.js` **and** update `CORS_ALLOWED_ORIGINS` and `FRONTEND_URL` in `backend/.env`.

### Other

| Problem | Fix |
|---------|-----|
| Logged out unexpectedly | Your token was removed (logout elsewhere / password change). Log in again. |
| Receipt / profile picture doesn't show | The backend must run with `DEBUG=True` to serve uploaded files in development. |
| Phone search finds nobody | Type all 10 digits (partial numbers are hidden for privacy), or search by name. Run `python manage.py seed_demo` for demo friends. |
| QR code opens on phone but can't load | The link points to `localhost`, which only works on the same computer. For phones on the same Wi-Fi, run `npm run dev -- --host` and add your Mac's IP to `CORS_ALLOWED_ORIGINS` / `ALLOWED_HOSTS`. |
| eSewa test gateway: "could not reach" | It needs internet. Use **Demo simulation** instead. |
| Khalti test gateway button disabled | `KHALTI_SECRET_KEY` is empty in `backend/.env` (section 7). |

---

## 12. Reset / reinstall

**Safe to delete** (they are recreated by the commands shown):

| Item | Recreate with |
|------|---------------|
| `backend/venv/` | `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt` |
| `frontend/node_modules/` | `npm install` |
| `frontend/dist/` | `npm run build` (only needed for production builds) |
| `backend/media/` | uploaded receipts/profile pictures - deleting removes those images only |
| `__pycache__/` folders | created automatically |
| `backend/.env` | `cp .env.example .env` and fill it in again (step 3.2) |

**Do NOT delete**: `backend/manage.py`, `backend/config/`, the app folders (`users/`, `groups/`, `expenses/`, `settlements/`, `notifications/`, `common/`), any `migrations/` folder, `backend/requirements.txt`, `frontend/src/`, `frontend/public/`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/index.html`, `frontend/vite.config.js`, the documentation.

### Reset the Python environment

```bash
cd path/to/SmartSplit-Nepal/backend
deactivate 2>/dev/null; rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Reset Node dependencies

```bash
cd path/to/SmartSplit-Nepal/frontend
rm -rf node_modules
npm install
```

### Reset the database (⚠️ deletes all SmartSplit data)

Stop the backend first (Ctrl + C), then:

```bash
psql postgres -c "DROP DATABASE smartsplit;"
psql postgres -c "CREATE DATABASE smartsplit OWNER smartsplit;"
# Official installer users: add -U postgres -h localhost after psql

cd path/to/SmartSplit-Nepal/backend
source venv/bin/activate
python manage.py migrate
python manage.py seed_demo        # optional
```

Never delete the `migrations/` folders - they describe the database structure.

### Reset `.env`

```bash
cd path/to/SmartSplit-Nepal/backend
rm .env
cp .env.example .env    # then fill it in (step 3.2)
```

### Restart the development servers

Press **Ctrl + C** in each terminal, then start them again (section 5).
