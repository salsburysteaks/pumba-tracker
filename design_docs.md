# Pumba Tracker — Design Documents

---

## System Description

I built Pumba to help me keep track of how much I spend taking care of my French Bulldog, Pumba. French Bulldogs are expensive and I am always squeezing money to make sure he has everything he needs. Pumba eats fresh food because he cannot have kibble or cans and he also cannot eat chicken due to allergies, so his food bill alone is already pretty high. On top of that he needs frequent vet visits because there always seems to be something wrong with him, and my pet insurance for a French Bulldog is not cheap either. Between food, vet bills, insurance, grooming, and everything else it gets hard to keep track of where the money is going. This app lets me log expenses as they happen, organize them by category, and tag them so I can see exactly what Pumba costs me and where I might be able to cut back if I need to.

---

## Entity List with Attributes

**categories** — id (SERIAL PK), name (VARCHAR 100, NOT NULL, UNIQUE), description (VARCHAR 255), created_at (TIMESTAMP, DEFAULT NOW)

**expenses** — id (SERIAL PK), category_id (INTEGER FK → categories.id), amount (NUMERIC 10,2, NOT NULL), notes (TEXT), expense_date (TIMESTAMP, DEFAULT NOW), created_at (TIMESTAMP, DEFAULT NOW)

**tags** — id (SERIAL PK), name (VARCHAR 100, NOT NULL, UNIQUE)

**expense_tags** — expense_id (INTEGER FK → expenses.id, ON DELETE CASCADE), tag_id (INTEGER FK → tags.id, ON DELETE CASCADE), PRIMARY KEY (expense_id, tag_id)

---

## Relationships

One category has many expenses (one-to-many). One expense belongs to one category. Expenses and tags share a many-to-many relationship implemented through the expense_tags junction table — one expense can have multiple tags, and one tag can apply to many expenses.

---

## Page-by-Page Plan

**Dashboard (Home)** — Shows total expenses logged, total spent this month, and total spent this year using st.metric(). Displays a table of the 10 most recent expenses with date, category, amount, and notes.

**Log Expense** — Main form with fields for amount, category (dropdown from DB), expense date, tags (multiselect from DB), and notes. Validates required fields and submits to the database.

**Expense History** — Full searchable, filterable table of all expenses. Filter by notes text search, category dropdown, and date range. Each row has Edit and Delete buttons. Edit opens a pre-filled form. Delete requires confirmation.

**Manage Categories** — Form to add a new category with name and description. Table of existing categories with Edit and Delete. Categories cannot be deleted if expenses reference them.

**Manage Tags** — Form to add a new tag. Table of existing tags with Edit and Delete.

---

## Validation Rules

- Amount: required, must be a positive number greater than 0
- Category: required, must select from existing categories pulled from database
- Expense date: required, cannot be a future date
- Category name: required, cannot be blank, must be unique
- Tag name: required, cannot be blank, must be unique
- Notes: optional, no validation needed

---

## ERD

See erd.png in this repository.
