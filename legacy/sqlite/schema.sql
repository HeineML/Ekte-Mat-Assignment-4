DROP TABLE IF EXISTS questions;
DROP TABLE IF EXISTS guest_groups;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS food_item_categories;
DROP TABLE IF EXISTS food_items;
DROP TABLE IF EXISTS event_categories;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL
);

CREATE TABLE event_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE food_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    price_nok INTEGER NOT NULL CHECK (price_nok >= 0),
    minimum_quantity INTEGER NOT NULL CHECK (minimum_quantity >= 1),
    published INTEGER NOT NULL DEFAULT 0,
    image TEXT,
    allergens TEXT NOT NULL DEFAULT '[]',       -- JSON list of strings
    dietary_labels TEXT NOT NULL DEFAULT '[]'   -- JSON list of strings
);

CREATE TABLE food_item_categories (
    food_item_id INTEGER NOT NULL REFERENCES food_items (id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES event_categories (id) ON DELETE CASCADE,
    PRIMARY KEY (food_item_id, category_id)
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES users (id),
    event_date TEXT NOT NULL,          -- ISO date
    number_of_guests INTEGER NOT NULL CHECK (number_of_guests >= 1),
    delivery_address TEXT NOT NULL,
    status TEXT NOT NULL,
    payment_status TEXT NOT NULL,
    created_at TEXT NOT NULL           -- ISO datetime
);

CREATE TABLE order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
    -- SET NULL keeps old orders intact when a food item is deleted.
    food_item_id INTEGER REFERENCES food_items (id) ON DELETE SET NULL,
    food_name TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity >= 1),
    unit_price_nok INTEGER NOT NULL
);

CREATE TABLE guest_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    size INTEGER NOT NULL CHECK (size >= 1),
    allergy_notes TEXT NOT NULL DEFAULT '',
    dietary_notes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
    customer_id INTEGER NOT NULL REFERENCES users (id),
    question TEXT NOT NULL,
    answer TEXT,
    created_at TEXT NOT NULL,
    answered_at TEXT
);
