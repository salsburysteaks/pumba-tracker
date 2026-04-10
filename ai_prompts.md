# AI Prompts & Process — Pumba Tracker

All prompts were given to Claude (claude.ai) during the building of this project.

---

## Prompt 1 — Database Setup + Home Page

**Prompt:**
```
I'm building a Streamlit app called Pumba Tracker connected to a PostgreSQL database using psycopg2. The connection is stored in st.secrets["DB_URL"].

Please do the following two things:

1. Create the database tables by connecting to the database and running this SQL:

CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS expenses (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES categories(id),
    amount NUMERIC(10,2) NOT NULL,
    notes TEXT,
    expense_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS expense_tags (
    expense_id INTEGER REFERENCES expenses(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (expense_id, tag_id)
);

INSERT INTO categories (name, description) VALUES
('Food', 'Fresh food and treats'),
('Vet', 'Vet visits and medical bills'),
('Insurance', 'Monthly pet insurance'),
('Grooming', 'Grooming appointments'),
('Misc', 'Everything else')
ON CONFLICT (name) DO NOTHING;

INSERT INTO tags (name) VALUES
('Recurring'),
('Emergency'),
('One-time'),
('Insurance-covered')
ON CONFLICT (name) DO NOTHING;

2. Write the content for streamlit_app.py — the home page dashboard that does the following:
- Uses psycopg2 to connect to the database via st.secrets["DB_URL"]
- Shows a title "🐾 Pumba Tracker" and a short description
- Displays 3 metrics using st.metric(): total expenses logged, total spent this month, and total spent this year
- Shows a table of the 10 most recent expenses with columns: date, category, amount, notes
- Uses parameterized queries (no f-strings in SQL)
- Includes user friendly error handling
```

**What worked:** Claude created the tables and wrote the full home page on the first try. The metrics and recent expenses table worked immediately after deploying.

**What I had to fix:** Nothing on this page needed manual fixes.

---

## Prompt 2 — Log Expense Page

**Prompt:**
```
I'm building a Streamlit app called Pumba Tracker connected to a PostgreSQL database using psycopg2. The connection is stored in st.secrets["DB_URL"].

Please create a Streamlit page called pages/1_Log_Expense.py that does the following:

1. Title "🐾 Log an Expense" at the top
2. A form with these fields:
   - Amount (number input, required, must be greater than 0)
   - Category (dropdown pulled from the categories table, required)
   - Expense date (date input, defaults to today, cannot be a future date)
   - Tags (multiselect pulled from the tags table, optional)
   - Notes (text area, optional)
3. Validate all required fields before inserting.
4. On successful submit, insert into the expenses table and then insert any selected tags into expense_tags using parameterized queries.
5. Show a success message after saving.
6. Use st.form() for the form.
7. Use psycopg2 with parameterized queries throughout. No f-strings in SQL.
```

**What worked:** The form, validation, and database inserts all worked correctly on the first try.

**What I had to fix:** Claude placed the file in the wrong directory (.streamlit/pages instead of pages/). Had to manually move it to the correct location.

---

## Prompt 3 — Expense History Page

**Prompt:**
```
Please create a Streamlit page called pages/2_Expense_History.py that does the following:

1. Title "📋 Expense History" at the top
2. Filter section with a text search box, category dropdown, and date range filter
3. Display all expenses in a table with edit and delete buttons on each row
4. Edit functionality — clicking Edit opens a pre-filled form with current values
5. Delete functionality — clicking Delete shows a confirmation message
6. Use parameterized queries throughout. No f-strings in SQL.
7. All dropdowns pull from database tables.
```

**What worked:** The search, filter, edit, and delete all worked correctly on the first try.

**What I had to fix:** Same directory issue as before — had to move the file into the pages/ folder.

---

## Prompt 4 — Manage Categories and Tags Pages

**Prompt:**
```
Please create TWO Streamlit pages:

PAGE 1: pages/3_Manage_Categories.py
- Form to add a new category with name and description
- Table showing all categories with Edit and Delete buttons
- Edit and Delete functionality with confirmation
- Handle case where category is referenced by expenses

PAGE 2: pages/4_Manage_Tags.py
- Form to add a new tag
- Table showing all tags with Edit and Delete buttons
- Edit and Delete functionality with confirmation
```

**What worked:** Both pages worked correctly on the first try including the foreign key protection on category deletes.

**What I had to fix:** Same directory issue — had to move both files into pages/.

---

## General Notes

- Claude Code in VS Code was used to generate all code directly into project files
- The biggest recurring issue was Claude placing new page files at the wrong directory level. Every new page had to be manually moved into the pages/ folder on GitHub.
- All SQL uses parameterized queries — no f-strings were used anywhere in the codebase
- The planning documents written before coding made the prompts very specific which resulted in working code on the first try for every page
