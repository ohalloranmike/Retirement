# Linux Mint setup

## System packages

The **desktop GUI** needs Tkinter from the OS (the pip package is not enough):

```bash
sudo apt update
sudo apt install python3-tk python3-venv
```

## Project virtual environment

```bash
cd ~/path/to/Retirement
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
chmod +x run-gui.sh run-streamlit.sh
```

The `run-*.sh` scripts (and the app bootstrap) will run `pip install -e .` automatically if Streamlit or the `retirement` package is missing from `.venv`.

```bash
# manual one-liner if you prefer
.venv/bin/python -m pip install -e .
```

## Launch

| UI | Command |
|----|---------|
| Desktop (Tkinter) | `./run-gui.sh` |
| Browser (Streamlit) | `./run-streamlit.sh` then open **http://127.0.0.1:8501** |

Prefer the shell scripts (or `.venv/bin/python` directly). If you run `streamlit run` with **system** `/usr/bin/python3`, recent versions of this project **re-launch** using `.venv/bin/python` automatically. If you still see a venv error, create `.venv` and run `./run-streamlit.sh`.

## Troubleshooting

### Streamlit: blank page and spinning runner icon

1. Run from a terminal: `./run-streamlit.sh` and read any red traceback.
2. Use the URL printed in the terminal (`127.0.0.1:8501`), not a hostname.
3. `git pull` for the latest `streamlit_app.py` (entry point must call `main()` on every run).
4. Try another browser; disable VPN/proxy for localhost.

### GUI: nothing appears

1. Install `python3-tk` (see above).
2. Run `./run-gui.sh` from a **desktop** terminal (not SSH without display).
3. On Wayland, if the window still fails: `GDK_BACKEND=x11 ./run-gui.sh`
4. If the terminal says “wrong interpreter”, use `./run-gui.sh` instead of `python3 gui.py`.
