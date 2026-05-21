# Troubleshooting: "This site can't be reached"

## Most common cause

**The Flask server is not running.** Your browser cannot connect if nothing is listening on port 5000.

You must keep a terminal open with the server running. Closing the terminal stops the server.

---

## Step-by-step checklist

### 1. Verify the server is running

**What it means:** "Can't be reached" = no process accepted the connection (server off, wrong port, or crash).

**Fix:**

```powershell
cd "c:\Users\Aryan Bhushan\Downloads\osint project"
.\venv\Scripts\activate
python run.py
```

You **must** see:

```
Running on http://127.0.0.1:5000
```

**Wrong command (this project has no `app.py`):**

```bash
python app.py   # FAILS — file does not exist
```

**Correct:**

```bash
python run.py
```

Or double-click **`start.bat`** in the project folder.

---

### 2. Correct entry file

**What it means:** Flask needs a file that calls `app.run()`. Here that is `run.py`, not `app.py`.

**Fix:** Always use:

```bash
python run.py
```

Or with Flask CLI:

```powershell
$env:FLASK_APP = "run:app"
flask run --host=127.0.0.1 --port=5000
```

---

### 3. Port conflict

**What it means:** Another app already uses port 5000; Flask may fail to start or bind elsewhere.

**Check (PowerShell):**

```powershell
netstat -ano | findstr ":5000"
```

If you see `LISTENING` on 5000 and it's not your Python process, change port in `.env`:

```
PORT=5001
```

Then open: **http://127.0.0.1:5001**

---

### 4. Flask installed in the right environment

**What it means:** System Python without Flask → `ModuleNotFoundError` and server never starts.

**Fix:**

```powershell
.\venv\Scripts\activate
pip install -r requirements.txt
pip show flask
```

---

### 5. Firewall / antivirus

**What it means:** Rare for `127.0.0.1`, but some tools block local servers.

**Fix:**

- Allow **Python** through Windows Firewall when prompted.
- Prefer `HOST=127.0.0.1` in `.env` (not `0.0.0.0`) for local-only dev.
- Temporarily test with firewall off to rule this out.

---

### 6. Process crashed (traceback in terminal)

**What it means:** Server started then exited; browser shows "can't be reached".

**Fix:** Read the **red error** in the terminal. Common fixes:

```powershell
pip install -r requirements.txt
```

---

### 7. Virtual environment

**What it means:** Wrong Python = missing packages.

**Fix:**

```powershell
.\venv\Scripts\activate
python run.py
```

Prompt should show `(venv)`.

---

### 8. Frontend + backend

**What it means:** This project serves UI and API from **one** Flask app on one port. No separate frontend server.

**Fix:** Only `python run.py` is required. API is same origin (`/api/...`).

---

### 9. Test both URLs

Try:

- http://127.0.0.1:5000
- http://localhost:5000

Both should work when the server is running.

---

### 10. Minimal test app

**What it means:** Isolates Flask/network from your full app.

```powershell
.\venv\Scripts\activate
python test_minimal.py
```

Open http://127.0.0.1:5000 — you should see **"Server Working"**.

| Result | Meaning |
|--------|---------|
| Minimal works, `run.py` fails | Missing dependency or app bug — read terminal traceback |
| Both fail | Python install, firewall, or port issue |

---

## Quick diagnostic commands

```powershell
# Is anything listening on 5000?
netstat -ano | findstr ":5000"

# Can Python reach the server?
.\venv\Scripts\python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:5000/api/health', timeout=3).read())"
```

---

## Debug reloader on Windows

With `FLASK_DEBUG=true`, Flask restarts twice. During restart the browser may briefly show "can't be reached".

**Fix in `.env`:**

```
FLASK_DEBUG=false
FLASK_USE_RELOADER=false
```
