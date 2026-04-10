import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date


@st.cache_resource
def get_connection():
    return psycopg2.connect(st.secrets["DB_URL"])


def fetch_all(query, params=None):
    conn = get_connection()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        return cur.fetchall()


def insert_expense(amount, category_id, expense_date, notes, tag_ids):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO expenses (amount, category_id, expense_date, notes)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (amount, category_id, expense_date, notes or None),
            )
            expense_id = cur.fetchone()[0]

            if tag_ids:
                cur.executemany(
                    "INSERT INTO expense_tags (expense_id, tag_id) VALUES (%s, %s)",
                    [(expense_id, tid) for tid in tag_ids],
                )

        conn.commit()
        return expense_id
    except Exception:
        conn.rollback()
        raise


# ── Page ──────────────────────────────────────────────────────────────────────

st.title("🐾 Log an Expense")

try:
    categories = fetch_all("SELECT id, name FROM categories ORDER BY name")
    tags = fetch_all("SELECT id, name FROM tags ORDER BY name")
except Exception as e:
    st.error(f"Could not load form data from the database.\n\n`{e}`")
    st.stop()

category_map = {row["name"]: row["id"] for row in categories}
tag_map = {row["name"]: row["id"] for row in tags}

with st.form("log_expense_form", clear_on_submit=True):
    amount = st.number_input("Amount ($)", min_value=0.0, step=0.01, format="%.2f")

    category_name = st.selectbox(
        "Category",
        options=["— select —"] + list(category_map.keys()),
    )

    expense_date = st.date_input("Expense Date", value=date.today())

    selected_tag_names = st.multiselect("Tags (optional)", options=list(tag_map.keys()))

    notes = st.text_area("Notes (optional)", max_chars=500)

    submitted = st.form_submit_button("Save Expense")

if submitted:
    errors = []

    if amount <= 0:
        errors.append("Amount must be greater than $0.00.")

    if category_name == "— select —":
        errors.append("Please select a category.")

    if expense_date > date.today():
        errors.append("Expense date cannot be in the future.")

    if errors:
        for err in errors:
            st.error(err)
    else:
        try:
            expense_id = insert_expense(
                amount=amount,
                category_id=category_map[category_name],
                expense_date=expense_date,
                notes=notes.strip() if notes else None,
                tag_ids=[tag_map[t] for t in selected_tag_names],
            )
            st.success(
                f"Expense saved! (ID #{expense_id}) — "
                f"**${amount:,.2f}** under **{category_name}** on {expense_date}."
            )
        except Exception as e:
            st.error(f"Something went wrong while saving the expense.\n\n`{e}`")
