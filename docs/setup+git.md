# Setup on another Windows PC (Git + Python)

This guide walks through **installing Git**, **cloning** the Retirement Planner repository from GitHub, **creating the project virtual environment**, and **pulling updates** when the repo changes on GitHub.

It assumes a second Windows machine (home, laptop, work PC). The same Git and Python steps work on macOS or Linux; only paths and the venv activation command differ (see [Activate the virtual environment](#activate-the-virtual-environment) notes).

**Repository (personal GitHub):**  
`https://github.com/ohalloranmike/Retirement.git`

For what the app does and how to use it after install, see [features.md](features.md). For a short install snippet only, see [README.md](../README.md).

---

## What you need before you start

| Requirement | Notes |
|-------------|--------|
| **Windows 10 or 11** | 64-bit recommended |
| **Python 3.10+** | Install from [python.org](https://www.python.org/downloads/) or the Microsoft Store. On first install, check **“Add python.exe to PATH”** (or use the `py` launcher below). |
| **Git** | Command-line Git for Windows (see next section) |
| **Internet** | To clone, pull, and `pip install` packages |
| **GitHub access** | Public repo: no account required to clone. Private repo: sign in via browser, PAT, or SSH key when Git prompts you. |

The project **does not** commit `.venv` to Git. You create `.venv` on each machine after cloning.

---

## Install Git on Windows

1. Download **Git for Windows** from [https://git-scm.com/download/win](https://git-scm.com/download/win).
2. Run the installer. Defaults are fine for most users. Useful options:
   - **Git from the command line and also from 3rd-party software** — so `git` works in PowerShell and Command Prompt.
   - **Use Windows’ default console window** or your preferred terminal (Windows Terminal is a good choice).
3. Close and reopen PowerShell (or Windows Terminal) so `PATH` updates.

Verify:

```powershell
git --version
```

You should see something like `git version 2.x.x.windows.x`.

Optional but helpful:

```powershell
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

Use the same email as your GitHub account if you plan to push commits from that machine later. Pulling and updating does not require this, but it is good practice.

---

## One-time setup: clone the project

Pick a folder where you keep code (examples below use `Projects` under your user profile). Adjust paths to taste.

### Open PowerShell

Press **Win**, type **PowerShell** or **Terminal**, open it.

### Create a parent folder (if needed)

```powershell
mkdir $HOME\Projects -ErrorAction SilentlyContinue
cd $HOME\Projects
```

### Clone from GitHub

**HTTPS** (simplest; Git may open a browser to sign in if the repo is private):

```powershell
git clone https://github.com/ohalloranmike/Retirement.git
cd Retirement
```

**SSH** (if you already use SSH keys with GitHub):

```powershell
git clone git@github.com:ohalloranmike/Retirement.git
cd Retirement
```

After clone, `git status` should report **On branch main** and **nothing to commit, working tree clean** (or only harmless untracked local files you create later).

Check that you are on `main` and tracking GitHub:

```powershell
git branch -vv
git remote -v
```

You should see `origin` pointing at `https://github.com/ohalloranmike/Retirement.git` (or the SSH URL).

---

## One-time setup: Python virtual environment

All app entry points (`gui.py`, `streamlit_app.py`, `main.py`) expect the **project** `.venv`, not system Python. The launcher scripts `run-gui.ps1` and `run-streamlit.ps1` call `.venv\Scripts\python.exe` directly.

From the **repository root** (the folder that contains `pyproject.toml` and `gui.py`):

### Create `.venv`

```powershell
cd $HOME\Projects\Retirement   # if you are not already there
py -3 -m venv .venv
```

If `py` is not found, try:

```powershell
python -m venv .venv
```

### Activate the virtual environment

**PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

If you see an error about running scripts being disabled, either:

- Run once (current user):  
  `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`  
  then activate again, or
- Skip activation and use the full path to the venv Python (see [Run without activating](#run-without-activating) below).

**Command Prompt (cmd.exe):**

```cmd
.venv\Scripts\activate.bat
```

**macOS / Linux** (for reference): `source .venv/bin/activate`

When active, your prompt often shows `(.venv)`.

### Upgrade pip and install the project

Still in the repo root, with venv active:

```powershell
python -m pip install --upgrade pip
python -m pip install -e .
```

`pip install -e .` installs dependencies from `pyproject.toml` (numpy, pandas, matplotlib, streamlit, customtkinter, openpyxl, etc.) and registers the `retirement` package in editable mode.

Alternative (requirements file only, no editable install):

```powershell
python -m pip install -r requirements.txt
```

Prefer **`pip install -e .`** so imports and IDE tooling match how the repo is intended to run.

### Verify the install

```powershell
python main.py --summary
```

You should see a short plan summary with no import errors.

Optional:

```powershell
python -c "import retirement; print('ok')"
```

---

## Run the application

Always use the project `.venv` (activate it, or use the `run-*.ps1` / `run-*.bat` scripts).

| Goal | Command |
|------|---------|
| Desktop GUI | `.\run-gui.ps1` or double-click **`run-gui.bat`** |
| Browser (Streamlit) | `.\run-streamlit.ps1` or **`run-streamlit.bat`** |
| CLI | `python main.py --summary` |
| CLI with sample config | `python main.py --config config\sample_v2.json --summary` |

With venv active you can also run:

```powershell
python gui.py
python -m streamlit run streamlit_app.py
```

### Run without activating

```powershell
.\.venv\Scripts\python.exe main.py --summary
.\.venv\Scripts\python.exe gui.py
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

### Cursor / VS Code

1. **File → Open Folder** → select the `Retirement` folder (repo root).
2. **Python: Select Interpreter** → `.venv\Scripts\python.exe`.

If you open only a subfolder, workspace settings may not apply and the wrong Python may be selected.

---

## Keep the project updated from GitHub

When you (or someone else) push changes to `main` on GitHub, update your other PC like this.

### 1. Close the app

Quit the GUI, stop Streamlit (Ctrl+C in the terminal), so no files are locked.

### 2. Go to the repo and fetch changes

```powershell
cd $HOME\Projects\Retirement
git status
```

If you have **local edits** to tracked files, either commit them, stash them, or discard them before pulling (see [Local changes and Git](#local-changes-and-git)).

Pull the latest `main`:

```powershell
git pull origin main
```

If your branch already tracks `origin/main`, this is enough:

```powershell
git pull
```

Git downloads new commits and updates tracked files (code, docs, `config/` samples, etc.). It does **not** recreate `.venv` for you.

### 3. Refresh Python dependencies when needed

Run **`pip install -e .` again** after a pull when any of these changed on GitHub:

- `pyproject.toml` (new or updated dependencies)
- `requirements.txt` (if you use that instead)

Safe habit after every pull:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

If only Python source or docs changed and dependencies did not, `pip install -e .` is quick and harmless.

### 4. Smoke test

```powershell
python main.py --summary
```

Then launch the GUI or Streamlit if you use them regularly.

### Typical update session (copy-paste)

```powershell
cd $HOME\Projects\Retirement
git pull
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python main.py --summary
```

---

## What Git does and does not sync

| In Git (updated by `git pull`) | Not in Git (stay on each machine) |
|--------------------------------|-----------------------------------|
| Source code, `config/sample*.json`, docs, launchers | `.venv/` (you create locally) |
| | `output/` (CLI chart/CSV output; gitignored) |
| | `retirement_planner.xlsx` (export saves; gitignored) |
| | Your own `config\my_plan.json` if you add it and do not commit |
| | `%APPDATA%\RetirementPlanner\gui_prefs.json` (desktop sidebar width) |

To move **your plan** between computers: copy a JSON config you edited, or re-export Excel/CSV/HTML from one machine and re-enter or archive on the other. Exports are not auto-synced by Git unless you choose to commit a config file.

---

## Local changes and Git

### See what changed locally

```powershell
git status
git diff
```

### Stash local edits, pull, then reapply

Useful for quick experiments on tracked files:

```powershell
git stash push -m "wip"
git pull
git stash pop
```

Resolve any conflicts Git reports, then test the app.

### Discard local changes to a tracked file

**Destructive** — you lose uncommitted edits to that file:

```powershell
git restore path\to\file
```

### Untracked files

New files you created (for example `config\my_plan.json`) are **untracked** until you `git add` them. `git pull` will not delete untracked files. To stop tracking something you accidentally committed, that is a different workflow; this project keeps personal spreadsheets out of Git via `.gitignore`.

---

## Authentication (HTTPS and private repos)

- **Public repo:** `git clone` and `git pull` usually work without logging in.
- **Private repo:** GitHub will ask you to sign in. Use a **Personal Access Token** as the password when using HTTPS, or set up **SSH keys** and clone with the `git@github.com:...` URL.
- **Git Credential Manager** (installed with Git for Windows) can remember credentials so you are not prompted every pull.

This project’s default remote is the **personal** account repo (`ohalloranmike/Retirement`). A work GitHub copy is a separate remote or clone unless you add one yourself:

```powershell
git remote add work https://github.com/YOUR_ORG/Retirement.git
git fetch work
git pull work main   # only if you use that remote
```

---

## Troubleshooting

| Problem | What to try |
|---------|-------------|
| `'git' is not recognized` | Reinstall Git; reopen terminal; confirm Git was added to PATH. |
| `Missing .venv` from `run-gui.ps1` | Run `py -3 -m venv .venv` and `pip install -e .` from repo root. |
| `Must use local .venv` when running scripts | You used system `python`. Use `.\.venv\Scripts\python.exe` or activate `.venv` first. |
| `Activate.ps1` blocked | `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`, or use `run-gui.bat` / full path to venv Python. |
| Errors after `git pull` | Run `pip install -e .` again; read merge conflict markers if Git reported conflicts. |
| `ModuleNotFoundError: retirement` | From repo root: `pip install -e .` with venv active. |
| Streamlit does not open | Run `python -m streamlit run streamlit_app.py` from repo root with venv; check firewall if using a non-default URL. |

---

## Quick reference

**First machine setup**

```powershell
mkdir $HOME\Projects -ErrorAction SilentlyContinue
cd $HOME\Projects
git clone https://github.com/ohalloranmike/Retirement.git
cd Retirement
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python main.py --summary
.\run-gui.ps1
```

**Later: get updates**

```powershell
cd $HOME\Projects\Retirement
git pull
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

---

## Related docs

- [features.md](features.md) — features, inputs, exports, troubleshooting for the app itself  
- [README.md](../README.md) — project overview and layout  
