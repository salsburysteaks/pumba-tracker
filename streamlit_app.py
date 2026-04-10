import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime


@st.cache_resource
def get_connection():
    return psycopg2.connect(st.secrets["DB_URL"])


def fetch_one(query, params=None):
    conn = get_connection()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        return cur.fetchone()


def fetch_all(query, params=None):
    conn = get_connection()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        return cur.fetchall()


st.title("🐾 Pumba Tracker")
st.caption("Track every treat, vet visit, and tail wag — all in one place.")

try:
    get_connection()
except Exception as e:
    st.error(f"Could not connect to the database. Please check your connection settings.\n\n`{e}`")
    st.stop()

try:
    total_row = fetch_one("SELECT COUNT(*) AS total FROM expenses")
    total_count = total_row["total"] if total_row else 0

    now = datetime.now()
    monthly_row = fetch_one(
        """
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM expenses
        WHERE EXTRACT(YEAR FROM expense_date) = %s
          AND EXTRACT(MONTH FROM expense_date) = %s
        """,
        (now.year, now.month),
    )
    monthly_total = float(monthly_row["total"]) if monthly_row else 0.0

    yearly_row = fetch_one(
        """
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM expenses
        WHERE EXTRACT(YEAR FROM expense_date) = %s
        """,
        (now.year,),
    )
    yearly_total = float(yearly_row["total"]) if yearly_row else 0.0

    col1, col2, col3 = st.columns(3)
    col1.metric("Expenses Logged", total_count)
    col2.metric("Spent This Month", f"${monthly_total:,.2f}")
    col3.metric("Spent This Year", f"${yearly_total:,.2f}")

except Exception as e:
    st.error(f"Failed to load summary metrics.\n\n`{e}`")

st.divider()
st.subheader("Recent Expenses")

try:
    rows = fetch_all(
        """
        SELECT
            e.expense_date AS date,
            c.name         AS category,
            e.amount,
            e.notes
        FROM expenses e
        LEFT JOIN categories c ON e.category_id = c.id
        ORDER BY e.expense_date DESC
        LIMIT 10
        """
    )

    if rows:
        display = [
            {
                "Date": row["date"].strftime("%Y-%m-%d %H:%M") if row["date"] else "—",
                "Category": row["category"] or "—",
                "Amount": f"${float(row['amount']):,.2f}",
                "Notes": row["notes"] or "",
            }
            for row in rows
        ]
        st.table(display)
    else:
        st.info("No expenses logged yet. Add your first one to get started!")

except Exception as e:
    st.error(f"Failed to load recent expenses.\n\n`{e}`")
