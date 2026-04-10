import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor


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


def insert_category(name, description):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO categories (name, description) VALUES (%s, %s) RETURNING id",
                (name, description or None),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
        return new_id
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise ValueError(f"A category named \"{name}\" already exists.")
    except Exception:
        conn.rollback()
        raise


def update_category(category_id, name, description):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE categories SET name = %s, description = %s WHERE id = %s",
                (name, description or None, category_id),
            )
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise ValueError(f"A category named \"{name}\" already exists.")
    except Exception:
        conn.rollback()
        raise


def delete_category(category_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM categories WHERE id = %s", (category_id,))
        conn.commit()
    except psycopg2.errors.ForeignKeyViolation:
        conn.rollback()
        raise ValueError(
            "This category has expenses linked to it and cannot be deleted. "
            "Re-assign or delete those expenses first."
        )
    except Exception:
        conn.rollback()
        raise


# ── Session state defaults ────────────────────────────────────────────────────

if "cat_editing_id" not in st.session_state:
    st.session_state["cat_editing_id"] = None
if "cat_confirm_delete_id" not in st.session_state:
    st.session_state["cat_confirm_delete_id"] = None


# ── Page ──────────────────────────────────────────────────────────────────────

st.title("🗂️ Manage Categories")

# ── Add category form ─────────────────────────────────────────────────────────

st.subheader("Add New Category")

with st.form("add_category_form", clear_on_submit=True):
    new_name = st.text_input("Name", max_chars=100, placeholder="e.g. Toys")
    new_desc = st.text_input("Description (optional)", max_chars=255)
    add_submitted = st.form_submit_button("Add Category")

if add_submitted:
    if not new_name.strip():
        st.error("Category name is required.")
    else:
        try:
            insert_category(new_name.strip(), new_desc.strip() if new_desc else None)
            st.success(f'Category "{new_name.strip()}" added.')
            st.rerun()
        except ValueError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Failed to add category.\n\n`{e}`")

st.divider()

# ── Categories table ──────────────────────────────────────────────────────────

st.subheader("All Categories")

try:
    categories = fetch_all(
        "SELECT id, name, description FROM categories ORDER BY name"
    )
except Exception as e:
    st.error(f"Failed to load categories.\n\n`{e}`")
    st.stop()

if not categories:
    st.info("No categories yet. Add one above.")
else:
    header = st.columns([2, 3, 1, 1])
    for col, label in zip(header, ["Name", "Description", "", ""]):
        col.markdown(f"**{label}**")
    st.divider()

    for row in categories:
        cat_id = row["id"]
        cols = st.columns([2, 3, 1, 1])
        cols[0].write(row["name"])
        cols[1].write(row["description"] or "—")

        if cols[2].button("Edit", key=f"cat_edit_{cat_id}"):
            st.session_state["cat_editing_id"] = cat_id
            st.session_state["cat_confirm_delete_id"] = None
            st.rerun()

        if cols[3].button("Delete", key=f"cat_delete_{cat_id}"):
            st.session_state["cat_confirm_delete_id"] = cat_id
            st.session_state["cat_editing_id"] = None
            st.rerun()

# ── Delete confirmation ───────────────────────────────────────────────────────

confirm_id = st.session_state["cat_confirm_delete_id"]
if confirm_id is not None:
    try:
        target = fetch_one("SELECT name FROM categories WHERE id = %s", (confirm_id,))
    except Exception as e:
        st.error(f"Could not load category.\n\n`{e}`")
        target = None

    if target:
        st.divider()
        st.warning(f'Are you sure you want to delete **"{target["name"]}"**? This cannot be undone.')
        c1, c2 = st.columns([1, 5])
        if c1.button("Yes, delete", type="primary"):
            try:
                delete_category(confirm_id)
                st.session_state["cat_confirm_delete_id"] = None
                st.success(f'Category "{target["name"]}" deleted.')
                st.rerun()
            except ValueError as e:
                st.error(str(e))
                st.session_state["cat_confirm_delete_id"] = None
            except Exception as e:
                st.error(f"Failed to delete category.\n\n`{e}`")
                st.session_state["cat_confirm_delete_id"] = None
        if c2.button("Cancel"):
            st.session_state["cat_confirm_delete_id"] = None
            st.rerun()

# ── Edit form ─────────────────────────────────────────────────────────────────

editing_id = st.session_state["cat_editing_id"]
if editing_id is not None:
    try:
        current = fetch_one(
            "SELECT id, name, description FROM categories WHERE id = %s", (editing_id,)
        )
    except Exception as e:
        st.error(f"Could not load category details.\n\n`{e}`")
        st.stop()

    if current is None:
        st.error(f"Category not found.")
        st.session_state["cat_editing_id"] = None
        st.stop()

    st.divider()
    st.subheader(f'Edit "{current["name"]}"')

    with st.form("edit_category_form"):
        edit_name = st.text_input("Name", value=current["name"], max_chars=100)
        edit_desc = st.text_input(
            "Description (optional)",
            value=current["description"] or "",
            max_chars=255,
        )
        s_col, c_col = st.columns([1, 5])
        save_clicked = s_col.form_submit_button("Save Changes", type="primary")
        cancel_clicked = c_col.form_submit_button("Cancel")

    if cancel_clicked:
        st.session_state["cat_editing_id"] = None
        st.rerun()

    if save_clicked:
        if not edit_name.strip():
            st.error("Category name is required.")
        else:
            try:
                update_category(
                    editing_id,
                    edit_name.strip(),
                    edit_desc.strip() if edit_desc else None,
                )
                st.session_state["cat_editing_id"] = None
                st.success(f'Category updated to "{edit_name.strip()}".')
                st.rerun()
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Failed to update category.\n\n`{e}`")
