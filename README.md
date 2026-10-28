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

```
flask --app app seed       # deletes all data and loads synthetic demo data
flask --app app init-db    # deletes all data and leaves an empty database
```

The database is `instance/ektemat.sqlite` and is not committed. All data is synthetic. `seed` creates these local demo accounts:

| Role | Email | Password |
|---|---|---|
| Admin | admin@example.test | admin123 |
| Customer | kari@example.test | kunde123 |
| Customer | ola@example.test | kunde123 |

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
