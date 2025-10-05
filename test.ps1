param()
$ErrorActionPreference = "Stop"

# Ensure venv exists
if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
  py -m venv .venv
}

# Activate venv
. .\.venv\Scripts\Activate.ps1

# Run tests
pytest -q
