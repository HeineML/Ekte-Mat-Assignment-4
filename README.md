# Ekte Mat Online

INFO212 Obligatory Assignment 4: a first version of an online catering and ordering system, built with Flask using MVC.

The requirements are in [docs/requirements.md](docs/requirements.md). The architecture and phase plans are in [docs/plans/](docs/plans/).

## Installation

Requires Python 3.13 (3.10 or newer should work).

```
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS/Linux
pip install -r requirements.txt
```

## Run

```
flask --app app run --debug
```

Then open http://127.0.0.1:5000.

## Seed data

Coming in phase 2 (`flask --app app init-db` and `flask --app app seed`). All data will be synthetic.

## Tests

```
pytest
```

## Project structure

```
app/
  models/       Model: domain entities, repositories, SQLite storage
  controllers/  Controller: Flask blueprints and routes
  views/        View: Jinja2 templates
  static/       CSS, JavaScript and images
tests/          pytest tests
docs/           requirements and plans
```
