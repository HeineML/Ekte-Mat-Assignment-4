# Ekte Mat Online – Project Requirements

## 1. Project context

This project is INFO212 Obligatory Assignment 4: **Ekte Mat Online**.

The goal is to build a first working version of an online catering/order system using **Claude Code**, GitHub and Flask.

Important: The group did **not** complete Lab 7. The project foundation is therefore reconstructed from the Obligatory Assignment 4 requirements and the Lab 7 instructions. We must not claim that Lab 7 was completed.

The application should be a simple, beginner-friendly first version that satisfies the mandatory requirements before implementing optional extensions.

---

## 2. Technology requirements

- Backend: Flask
- Architecture: MVC
- Frontend: HTML/CSS/JavaScript and/or Jinja2 templates
- Temporary storage: SQLite or JSON is allowed
- Storage access must be isolated in the model/data-access layer so that Neo4j can replace it later
- GitHub must be used for version control
- The project must include `CLAUDE.md`
- Synthetic/test data only
- No API keys or secrets may be committed to GitHub

### MVC

**Model**
- Domain models
- Data access
- Storage-related logic

**View**
- HTML/Jinja2 templates
- CSS/JavaScript where needed
- User interface

**Controller**
- Flask routes/blueprints
- Receives requests
- Calls the model
- Selects the appropriate view

The architecture should keep these responsibilities separated.

---

# 3. Customer functionality

## C1 – Menu by event

Customers must be able to browse food items grouped by event category.

Examples of event categories:
- Birthday
- Confirmation
- Wedding
- Conference
- Christmas party

Each food item should display:
- Picture
- Name
- Description
- Price in NOK
- Minimum order quantity
- Allergens
- Dietary labels

Only published food items should be visible to customers.

---

## C2 – Shopping cart

Customers must be able to:
- Add food items to the cart
- Change quantities
- Remove items
- See an estimated total

The system must reject quantities below the food item's minimum order quantity.

---

## C3 – Register/login and submit order

Customers must be able to register and log in.

When submitting an order, the customer must provide:
- Event date
- Number of guests
- Delivery address
- Allergy notes per guest group
- Dietary notes per guest group

No online payment solution is required.

---

## C4 – My orders

A logged-in customer must be able to see their own orders.

Each order should show:
- Order information
- Current order status
- Current payment status

Customers must not be able to see other customers' orders.

---

## C5 – Questions

Customers must be able to:
- Ask a question about a specific order
- Read the answer from the administrator

---

# 4. Admin functionality

## A1 – Food items

Administrators must be able to:
- Add food items
- Edit food items
- Remove food items

A food item contains at least:
- Name
- Description
- Price in NOK
- Minimum order quantity
- Event categories
- Allergens
- Dietary labels
- Published/unpublished status

---

## A2 – Images

Administrators must be able to provide an image for a food item.

The assignment allows:
- Uploading a picture
- Writing an instruction for an AI/image service to create or modify an image

The administrator should be able to preview the image before saving it.

For the first version, a simple image upload/placeholder implementation is acceptable if it satisfies the mandatory functionality without requiring an external AI API.

---

## A3 – Orders

Administrators must be able to:
- See all customer orders
- Filter orders by status
- Filter orders by event date
- Open an individual order
- Change the order status
- Change the payment status

### Order status

Normal order flow:

`submitted → approved → in preparation → delivered`

The system must also support:

`rejected`

and/or

`cancelled`

### Payment status

Possible payment statuses:
- Not paid
- Deposit paid
- Invoiced
- Paid

---

## A4 – Questions

Administrators must be able to:
- See customer questions
- See which order a question belongs to
- Read the question
- Write an answer

Customers must then be able to see the answer.

---

# 5. Domain model

The first version should contain domain models similar to the following.

## User

Possible attributes:
- id
- name
- email
- password
- role

Roles:
- customer
- admin

## FoodItem

Possible attributes:
- id
- name
- description
- price
- minimum_quantity
- published
- image
- allergens
- dietary_labels
- event_categories

## Order

Possible attributes:
- id
- customer
- event_date
- number_of_guests
- delivery_address
- allergy_notes
- dietary_notes
- status
- payment_status

## OrderItem

Possible attributes:
- id
- order
- food_item
- quantity
- price

The price should be stored with the order item so that an old order does not change if the food item's current price changes.

## Question

Possible attributes:
- id
- order
- customer
- question
- answer
- created_at
- answered_at

### Main relationships

- A User can place many Orders.
- An Order contains one or more OrderItems.
- An OrderItem refers to a FoodItem.
- A User can ask Questions.
- A Question belongs to an Order.
- An Order can have multiple Questions.

---

# 6. Mandatory first version

The priority is to implement all mandatory functionality before optional extensions.

The minimum working application should therefore contain:

### Customer

- Browse menu
- Filter/group menu by event
- Add items to cart
- Change/remove cart items
- Validate minimum quantity
- Register
- Log in
- Submit order
- View own orders
- View order status
- View payment status
- Ask questions about orders
- Read administrator answers

### Admin

- Log in
- Create food items
- Edit food items
- Delete food items
- Publish/unpublish food items
- Add/preview images
- View all orders
- Filter orders
- View individual orders
- Change order status
- Change payment status
- View customer questions
- Answer questions

---

# 7. Optional extensions

These should only be considered after the mandatory functionality works.

Possible extensions include:

- Kitchen view showing allergies
- Kitchen capacity checking
- Company accounts
- Showing origin of food
- Norwegian/English language support

---

# 8. Security and data

- Use synthetic/test data only.
- Passwords must not be stored as plain text in the final application.
- Customer data must be separated between users.
- Customers must only access their own orders and questions.
- Admin functionality must require administrator access.
- No Claude API keys, passwords or other secrets may be committed to GitHub.

---

# 9. Development workflow

We should develop the application in small phases.

Before implementing a larger feature:
1. Enter Plan mode in Claude Code.
2. Claude proposes an implementation plan.
3. The group reviews the plan.
4. The agreed plan is saved under `docs/plans/`.
5. Implementation can then begin.

Do not implement the whole application in one large step.

Start with the simplest working foundation and gradually add functionality.

---

# 10. Lab 7 relationship

Lab 7 is used as guidance for the development process, requirements thinking and documentation.

The group did not complete Lab 7 and must not present reconstructed material as if it were work completed during Lab 7.

Relevant Lab 7 principles include:
- Use clear project requirements.
- Avoid inventing requirements.
- Keep an audit trail.
- Use plans before larger implementation tasks.
- Keep requirements and design traceable.
- Use Git for project history.
- Keep project documentation organized.

---

# 11. Assignment deliverables

The final project must include:

- Working Flask application
- MVC structure
- Customer site
- Admin panel
- GitHub repository
- `CLAUDE.md`
- README with installation, seed, run and test instructions
- Plans under `docs/plans/` for larger features
- Synthetic seed/test data
- Tests where appropriate

The final report must include:

1. Front page
   - Group members
   - GitHub repository URL
   - Assessed version/tag
   - Whether Neo4j is used

2. Features
   - Feature names
   - Short descriptions
   - Screenshots of required customer and admin functionality

3. Software design
   - Relevant diagrams/models
   - Explanation of the architecture and design

4. Reflection
   - A short paragraph explaining whether the design helped build the product and steer Claude Code.

---

# 12. Priority

Implementation priority:

1. Project foundation and MVC structure
2. Models and temporary storage
3. Customer menu
4. Shopping cart
5. Registration/login
6. Order submission
7. Customer order overview
8. Admin food management
9. Admin order management
10. Questions and answers
11. Images
12. Tests, seed data and documentation
13. Optional extensions only if time remains
