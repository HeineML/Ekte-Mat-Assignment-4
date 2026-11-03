# 05 – Register and Login

**Status:** implemented 2026-11-03. Written and implemented in one session at the user's request ("complete everything"); the group has **not yet reviewed** this plan. Decisions marked **[Decision]** are open for the group to change.

## Context

Phases 0–4 delivered the menu (C1) and the session cart (C2). Checkout (phase 6), my orders (phase 7) and the whole admin panel need to know who the user is. Phase 5 adds the register/login part of **C3** and the access rules in **§8**.

**Requirements:**
- C3: customers must be able to register and log in.
- §6 Admin: admins log in.
- §8: passwords are never stored as plain text; admin functionality requires administrator access.
- `00-architecture.md` §4: admins log in at the same `/login`; admin accounts come only from the seed data.

**Out of scope:** checkout (phase 6), password reset, email confirmation, CSRF tokens (not required; `SESSION_COOKIE_SAMESITE = "Lax"` from phase 4 stays the safeguard).

---

## Behaviour

| Route | Does |
|---|---|
| `GET/POST /register` | Form: name, email, password, repeat password. Creates a **customer** (never an admin), logs them in and redirects to `next` or the menu. |
| `GET/POST /login` | Form: email, password. On success redirects to `next`; otherwise admins go to the admin area (the menu until phase 9 adds `/admin/orders`) and customers to the menu. Wrong email or password gives one generic error message. |
| `POST /logout` | Logs out (the cart is cleared too, because the whole session is cleared) and redirects to the menu. |

Validation on register:
- Name and email are required; email must contain `@`. Email is stored trimmed and lower-case.
- **[Decision]** Password must be at least 8 characters. The requirements don't set a rule.
- Passwords must match.
- An email that is already registered gives "An account with this email already exists."
- On an error the form is shown again with the name and email filled in (never the password).

**[Decision]** Registering logs the new customer in straight away, so they can continue to checkout.

The cart survives logging in: the session is cleared on login (to avoid session fixation) but the cart is copied over.

Nav (in `base.html`): "Log in" and "Register" when logged out; the user's name and a "Log out" button when logged in.

---

## Implementation

**Model: `app/models/services.py`.**
- `register_customer(name, email, password, password2)` → `(user, errors)`. Validates, hashes with `werkzeug.security.generate_password_hash`, catches `EmailAlreadyRegistered`.
- `authenticate(email, password)` → user or None, using `check_password_hash`.

**Controller:**
- `app/controllers/auth.py` (blueprint `auth`): the three routes above, and a `before_app_request` hook that loads `g.user` from `session["user_id"]` (or `None`).
- `app/controllers/decorators.py`: `login_required` (redirects to `/login?next=<current page>` with an info flash) and `admin_required` (not logged in → login; logged in but not admin → 403).
- `app/controllers/helpers.py`: `safe_next(target, default)`, moved out of `cart.py` so login and cart share the open-redirect check.

**Views:** `auth/login.html`, `auth/register.html`; nav changes in `base.html`; small form styles in `style.css`.

---

## Tests (`tests/test_auth.py`)

- Register creates a customer with a hashed password and logs them in.
- Register errors: missing fields, invalid email, short password, mismatched passwords, duplicate email (case-insensitive).
- Register can't create an admin (a `role=admin` field is ignored).
- Login with the right password works; wrong password or unknown email gives the generic error.
- Login keeps the cart and honours a local `next`, but not an external one.
- Logout clears the user.
- `login_required` redirects to login with `next`; `admin_required` gives 403 to customers.

## Verification

1. `pytest`
2. `flask --app app seed`, run the server: register a new customer, log out, log in as `kari@example.test` / `kunde123`, log in as `admin@example.test` / `admin123`.
