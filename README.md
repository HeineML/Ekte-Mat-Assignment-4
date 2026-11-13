# Ekte Mat Online

INFO212 Obligatory Assignments 4 and 5: an online catering and ordering system, built with Flask using MVC.

Reports: Oblig 4 (features with screenshots, diagrams, design and reflection) in [docs/report-oblig4.md](docs/report-oblig4.md); Oblig 5 (graph data model) in [docs/report-oblig5.md](docs/report-oblig5.md), also as [PDF](docs/report-oblig5.pdf).

Assessed versions: tag `v1.0` (Oblig 4, SQLite) and tag `oblig5` (Oblig 5, Neo4j).

Storage: **Neo4j** (Neo4j Aura), through the official `neo4j` Python driver. Only the repositories in `app/models/neo4j/` talk to the database; controllers and templates use the repository interfaces in `app/models/`. The SQLite implementation from Oblig 4 is kept for reference in [legacy/](legacy/README.md) and is not used.

## Features

**Customers**
- **Menu by event (C1):** published dishes grouped by event (Birthday, Confirmation, Wedding, Conference, Christmas party) with picture, description, price, minimum order, allergens and dietary labels. The menu can be filtered to dishes without chosen allergens and with chosen dietary labels (a graph query over `CONTAINS` and `HAS_LABEL`).
- **Shopping cart (C2):** add, change and remove dishes, with an estimated total. Quantities below a dish's minimum are rejected.
- **Register, log in and order (C3):** event date, number of guests, delivery address, and allergy and dietary notes per guest group. Prices are fixed when the order is submitted. No online payment.
- **My orders (C4):** the customer's own orders with order status and payment status.
- **Questions (C5):** ask a question on an order and read the answer.

**Administrators**
- **Food items (A1):** create, edit, delete, publish and unpublish.
- **Pictures (A2):** upload a picture with a preview before saving; dishes without one show a placeholder.
- **Orders (A3):** all orders filtered by status and/or event date; change order status (submitted, approved, in preparation, delivered, rejected, cancelled) and payment status (not paid, deposit paid, invoiced, paid).
- **Questions (A4):** all or unanswered questions with the order they belong to; write or update answers.

## Installation

Requires Python 3.13 (3.10 or newer should work).

```
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS/Linux
pip install -r requirements.txt
```

## Neo4j Aura

1. Create a free instance at https://console.neo4j.io. Aura shows the password once and offers a credentials file; keep it.
2. Copy `.env.example` to `.env` and fill in `NEO4J_URI` (`neo4j+s://….databases.neo4j.io`), `NEO4J_USER` and `NEO4J_PASSWORD`. Flask reads `.env` automatically. Never commit `.env`.
3. For the tests, fill in `NEO4J_TEST_URI`, `NEO4J_TEST_USER` and `NEO4J_TEST_PASSWORD` with a **second** instance (Aura Free allows one instance per account, so use another group member's). Every test deletes all data in it. Without these, the database tests are skipped.

A free instance pauses after a few days without use; resume it in the Aura console.

## Seed data

```
flask --app app seed       # deletes all data and loads synthetic demo data
flask --app app init-db    # deletes all data and leaves an empty database
```

Both delete every node in the configured Neo4j instance and create the constraints (unique ids and emails). All data is synthetic. `seed` creates 11 dishes with photos (one unpublished), 6 orders (one in each order status), 2 questions (one answered) and these local demo accounts:

| Role | Email | Password |
|---|---|---|
| Admin | admin@example.test | admin123 |
| Customer | kari@example.test | kunde123 |
| Customer | ola@example.test | kunde123 |

Admin accounts only come from the seed data; public registration always creates customers.

The dish photos are freely licensed pictures from Wikimedia Commons, stored in `app/static/img/food/`. `seed` copies them into the upload folder, so admins can replace or remove them, and resetting the data also empties the upload folder. The photographers and licences are listed on the *Photo credits* page (`/photo-credits`, linked in the footer) and in `app/static/img/food/credits.json`.

## Run

```
flask --app app run --debug
```

Then open http://127.0.0.1:5000. For anything other than local development, set a random `SECRET_KEY` environment variable. Uploaded pictures are saved in `app/static/uploads/` (not committed).

## Tests

```
pytest                                   # all tests (needs NEO4J_TEST_* in .env)
pytest tests/test_checkout.py            # one file
pytest tests/test_cart.py::test_remove   # one test
```

## Manual test walkthrough

Run `flask --app app seed` and start the server.

1. **Customer:** on the menu, filter by event, tick "milk" under *Without allergens* and "vegan" under *Dietary labels*, and add dishes to the cart (try a quantity below the minimum). Change a quantity on `/cart` and go to checkout. Log in as `kari@example.test` and submit with a guest group, for example "Children, 5, nut allergy". You land on the new order's page. Ask a question at the bottom.
2. **Access control:** still as Kari, open `/orders/3` (Ola's order) and get "Page not found"; open `/admin/orders` and get "Access denied".
3. **Admin:** log out and log in as `admin@example.test`. Under *Orders*, filter by status or date, open Kari's new order and change its order and payment status. Under *Questions*, answer Kari's question. Under *Food*, create a dish with a picture (the preview appears before you save), publish it, and check the menu.
4. **Customer again:** log in as Kari and see the new statuses and the answer on the order page.

## Project structure

```
app/
  __init__.py   app factory, blueprints, error pages
  config.py     configuration (SECRET_KEY from the environment)
  models/       Model: entities, repository interfaces, services (domain rules), images, seed
    neo4j/      Neo4j storage: driver, Cypher repositories, constraints
  controllers/  Controller: one Flask blueprint per area, access-control decorators
  views/        View: Jinja2 templates
  static/       CSS, JavaScript and the placeholder image
tests/          pytest tests
docs/           report material
legacy/sqlite/  the Oblig 4 SQLite storage, kept for reference, not used
```
