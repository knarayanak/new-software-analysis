# New Software Analysis

Minimal service with orchestrator + executor + tests.

## Quickstart
```bash
python -m pip install -U pip
pip install -r requirements-dev.txt
python -m pytest -vv --cov --cov-fail-under=95
```

## CI
GitHub Actions runs tests & coverage on pushes and PRs.

![CI](https://github.com/knarayanak/new-software-analysis/actions/workflows/ci.yml/badge.svg)

