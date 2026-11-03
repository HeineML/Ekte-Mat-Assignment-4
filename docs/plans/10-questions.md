# 10 – Questions and Answers

**Status:** implemented 2026-11-03. Written and implemented in one session at the user's request; the group has **not yet reviewed** this plan. Decisions marked **[Decision]** are open for the group to change.

## Context

The repository and seed data already have questions (phase 2). Phase 10 adds the pages: **C5** for customers and **A4** for admins.

**Requirements:**
- C5: customers must be able to ask a question about a specific order and read the administrator's answer.
- A4: administrators must be able to see customer questions, see which order a question belongs to, read the question and write an answer. Customers must then be able to see the answer.
- §8: customers only access their own orders and questions.

---

## Behaviour

**Customer**, on their order page `/orders/<id>`:
- A "Questions" section lists the order's questions, oldest first, with the date asked and either the answer (with the date answered) or "Waiting for an answer".
- A form to ask a new question: `POST /orders/<id>/questions`. The order is looked up with `get_for_customer`, so another customer's order gives 404. The question is required; **[Decision]** at most 2000 characters.

**Admin:**
- `GET /admin/questions` lists all questions, newest first: the question, the order it belongs to (link to the admin order page), the customer, when it was asked, and the answer or an answer form. `?unanswered=1` shows only unanswered questions. The nav link shows "Questions".
- `POST /admin/questions/<id>/answer` stores the answer and the time. **[Decision]** An answered question can be answered again; the new text replaces the old answer, so typos can be fixed.
- The admin order page also lists that order's questions with the same answer form.
- After answering, the admin returns to the page they came from (local `next` only).

## Implementation

- **Model, `services.py`:** `ask_question(order, customer_id, text)` → `(question, errors)` and `answer_question(question, text)` → errors. `customers_by_id` works for questions too, since both have `customer_id`.
- **Controllers:** `orders.py` gets `ask`; new `admin_questions.py` (blueprint `admin_questions`, prefix `/admin/questions`); `admin_orders.detail` passes the order's questions.
- **Views:** `orders/detail.html` (questions section), `admin/questions.html`, `admin/_question.html` (one question with its answer form, used by both admin pages), admin nav link.

## Tests (`tests/test_questions.py`)

- Customer asks a question on their own order and sees it as waiting; asking on another customer's order → 404; empty or too long question is rejected.
- Customer sees the admin's answer on their order page.
- Customers never see questions from other orders.
- Admin routes require admin.
- Admin list shows question, order link and customer; `unanswered=1` filters.
- Admin answers; answer is saved with `answered_at`; empty answer is rejected; answering again replaces the answer; unknown question → 404.
- The admin order page lists the order's questions.

## Verification

1. `pytest`
2. Seeded server: as Ola, ask a question on order 3; as admin, answer it under Questions; as Ola, read the answer.
