import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date, timedelta


# ── DB helpers ────────────────────────────────────────────────────────────────

@st.cache_resource
def get_connection():
    return psycopg2.connect(st.secrets["DB_URL"])


def fetch_all(query, params=None):
    conn = get_connection()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        return cur.fetchall()


def fetch_one(query, params=None):
    conn = get_connection()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        return cur.fetchone()


def update_expense(expense_id, amount, category_id, expense_date, notes, tag_ids):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE expenses
                SET amount = %s, category_id = %s, expense_date = %s, notes = %s
                WHERE id = %s
                """,
                (amount, category_id, expense_date, notes or None, expense_id),
            )
            cur.execute(
                "DELETE FROM expense_tags WHERE expense_id = %s",
                (expense_id,),
            )
            if tag_ids:
                cur.executemany(
                    "INSERT INTO expense_tags (expense_id, tag_id) VALUES (%s, %s)",
                    [(expense_id, tid) for tid in tag_ids],
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def delete_expense(expense_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# ── Session state defaults ────────────────────────────────────────────────────

if "editing_id" not in st.session_state:
    st.session_state["editing_id"] = None
if "confirm_delete_id" not in st.session_state:
    st.session_state["confirm_delete_id"] = None


# ── Page ──────────────────────────────────────────────────────────────────────

st.title("📋 Expense History")

try:
    categories = fetch_all("SELECT id, name FROM categories ORDER BY name")
    tags = fetch_all("SELECT id, name FROM tags ORDER BY name")
except Exception as e:
    st.error(f"Could not load data from the database.\n\n`{e}`")
    st.stop()

category_map = {row["name"]: row["id"] for row in categories}
tag_map = {row["name"]: row["id"] for row in tags}
category_id_to_name = {row["id"]: row["name"] for row in categories}

# ── Filters ───────────────────────────────────────────────────────────────────

with st.expander("Filters", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        search_notes = st.text_input("Search notes", placeholder="e.g. vet visit")
        category_filter = st.selectbox(
            "Category",
            options=["All Categories"] + list(category_map.keys()),
        )
    with col2:
        start_date = st.date_input("From", value=date.today() - timedelta(days=365))
        end_date = st.date_input("To", value=date.today())

if start_date > end_date:
    st.warning("Start date must be on or before end date.")
    st.stop()

# ── Build filtered query ──────────────────────────────────────────────────────

conditions = ["e.expense_date >= %s", "e.expense_date <= %s"]
params = [start_date, end_date]

if search_notes.strip():
    conditions.append("e.notes ILIKE %s")
    params.append(f"%{search_notes.strip()}%")

if category_filter != "All Categories":
    conditions.append("e.category_id = %s")
    params.append(category_map[category_filter])

where_clause = "WHERE " + " AND ".join(conditions)

try:
    expenses = fetch_all(
        """
        SELECT
            e.id,
            e.expense_date,
            e.category_id,
            c.name  AS category,
            e.amount,
            e.notes
        FROM expenses e
        LEFT JOIN categories c ON e.category_id = c.id
        """
        + where_clause
        + " ORDER BY e.expense_date DESC",
        params,
    )
except Exception as e:
    st.error(f"Failed to load expenses.\n\n`{e}`")
    st.stop()

# ── Results table ─────────────────────────────────────────────────────────────

st.divider()

if not expenses:
    st.info("No expenses found. Try adjusting the filters.")
else:
    st.caption(f"{len(expenses)} expense{'s' if len(expenses) != 1 else ''} found")

    header = st.columns([2, 2, 1.5, 3, 1, 1])
    for col, label in zip(header, ["Date", "Category", "Amount", "Notes", "", ""]):
        col.markdown(f"**{label}**")
    st.divider()

    for row in expenses:
        exp_id = row["id"]
        cols = st.columns([2, 2, 1.5, 3, 1, 1])
        cols[0].write(row["expense_date"].strftime("%Y-%m-%d") if row["expense_date"] else "—")
        cols[1].write(row["category"] or "—")
        cols[2].write(f"${float(row['amount']):,.2f}")
        cols[3].write(row["notes"] or "")

        if cols[4].button("Edit", key=f"edit_{exp_id}"):
            st.session_state["editing_id"] = exp_id
            st.session_state["confirm_delete_id"] = None
            st.rerun()

        if cols[5].button("Delete", key=f"delete_{exp_id}"):
            st.session_state["confirm_delete_id"] = exp_id
            st.session_state["editing_id"] = None
            st.rerun()

# ── Delete confirmation ───────────────────────────────────────────────────────

confirm_id = st.session_state["confirm_delete_id"]
if confirm_id is not None:
    st.divider()
    st.warning(f"Are you sure you want to delete expense #{confirm_id}? This cannot be undone.")
    conf_col1, conf_col2 = st.columns([1, 5])
    if conf_col1.button("Yes, delete", type="primary"):
        try:
            delete_expense(confirm_id)
            st.session_state["confirm_delete_id"] = None
            st.success(f"Expense #{confirm_id} deleted.")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to delete expense.\n\n`{e}`")
    if conf_col2.button("Cancel"):
        st.session_state["confirm_delete_id"] = None
        st.rerun()

# ── Edit form ─────────────────────────────────────────────────────────────────

editing_id = st.session_state["editing_id"]
if editing_id is not None:
    st.divider()
    st.subheader(f"Edit Expense #{editing_id}")

    try:
        current = fetch_one(
            "SELECT id, amount, category_id, expense_date, notes FROM expenses WHERE id = %s",
            (editing_id,),
        )
        current_tag_rows = fetch_all(
            """
            SELECT t.name FROM tags t
            JOIN expense_tags et ON et.tag_id = t.id
            WHERE et.expense_id = %s
            """,
            (editing_id,),
        )
    except Exception as e:
        st.error(f"Could not load expense details.\n\n`{e}`")
        st.stop()

    if current is None:
        st.error(f"Expense #{editing_id} not found.")
        st.session_state["editing_id"] = None
        st.stop()

    current_tag_names = [r["name"] for r in current_tag_rows]
    current_category_name = category_id_to_name.get(current["category_id"], "— select —")
    current_expense_date = (
        current["expense_date"].date()
        if hasattr(current["expense_date"], "date")
        else current["expense_date"]
    )

    with st.form("edit_expense_form"):
        edit_amount = st.number_input(
            "Amount ($)",
            min_value=0.0,
            step=0.01,
            format="%.2f",
            value=float(current["amount"]),
        )
        edit_category = st.selectbox(
            "Category",
            options=["— select —"] + list(category_map.keys()),
            index=(["— select —"] + list(category_map.keys())).index(current_category_name)
            if current_category_name in category_map
            else 0,
        )
        edit_date = st.date_input("Expense Date", value=current_expense_date)
        edit_tags = st.multiselect(
            "Tags (optional)",
            options=list(tag_map.keys()),
            default=current_tag_names,
        )
        edit_notes = st.text_area(
            "Notes (optional)",
            value=current["notes"] or "",
            max_chars=500,
        )

        save_col, cancel_col = st.columns([1, 5])
        submitted = save_col.form_submit_button("Save Changes", type="primary")
        cancelled = cancel_col.form_submit_button("Cancel")

    if cancelled:
        st.session_state["editing_id"] = None
        st.rerun()

    if submitted:
        errors = []
        if edit_amount <= 0:
            errors.append("Amount must be greater than $0.00.")
        if edit_category == "— select —":
            errors.append("Please select a category.")
        if edit_date > date.today():
            errors.append("Expense date cannot be in the future.")

        if errors:
            for err in errors:
                st.error(err)
        else:
            try:
                update_expense(
                    expense_id=editing_id,
                    amount=edit_amount,
                    category_id=category_map[edit_category],
                    expense_date=edit_date,
                    notes=edit_notes.strip() if edit_notes else None,
                    tag_ids=[tag_map[t] for t in edit_tags],
                )
                st.session_state["editing_id"] = None
                st.success(f"Expense #{editing_id} updated.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to update expense.\n\n`{e}`")
