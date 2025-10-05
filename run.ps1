param()
$ErrorActionPreference = "Stop"

# Ensure venv exists
if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
  py -m venv .venv
}

# Activate venv
. .\.venv\Scripts\Activate.ps1

# Keep pip current & install deps
python -m pip install -U pip
python -m pip install -r requirements.txt

# Start API
uvicorn app.main:app --reload
