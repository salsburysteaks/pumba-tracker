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


def insert_tag(name):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tags (name) VALUES (%s) RETURNING id",
                (name,),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
        return new_id
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise ValueError(f"A tag named \"{name}\" already exists.")
    except Exception:
        conn.rollback()
        raise


def update_tag(tag_id, name):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE tags SET name = %s WHERE id = %s",
                (name, tag_id),
            )
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise ValueError(f"A tag named \"{name}\" already exists.")
    except Exception:
        conn.rollback()
        raise


def delete_tag(tag_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tags WHERE id = %s", (tag_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# ── Session state defaults ────────────────────────────────────────────────────

if "tag_editing_id" not in st.session_state:
    st.session_state["tag_editing_id"] = None
if "tag_confirm_delete_id" not in st.session_state:
    st.session_state["tag_confirm_delete_id"] = None


# ── Page ──────────────────────────────────────────────────────────────────────

st.title("🏷️ Manage Tags")

# ── Add tag form ──────────────────────────────────────────────────────────────

st.subheader("Add New Tag")

with st.form("add_tag_form", clear_on_submit=True):
    new_name = st.text_input("Tag Name", max_chars=100, placeholder="e.g. Seasonal")
    add_submitted = st.form_submit_button("Add Tag")

if add_submitted:
    if not new_name.strip():
        st.error("Tag name is required.")
    else:
        try:
            insert_tag(new_name.strip())
            st.success(f'Tag "{new_name.strip()}" added.')
            st.rerun()
        except ValueError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Failed to add tag.\n\n`{e}`")

st.divider()

# ── Tags table ────────────────────────────────────────────────────────────────

st.subheader("All Tags")

try:
    tags = fetch_all("SELECT id, name FROM tags ORDER BY name")
except Exception as e:
    st.error(f"Failed to load tags.\n\n`{e}`")
    st.stop()

if not tags:
    st.info("No tags yet. Add one above.")
else:
    header = st.columns([4, 1, 1])
    for col, label in zip(header, ["Name", "", ""]):
        col.markdown(f"**{label}**")
    st.divider()

    for row in tags:
        tag_id = row["id"]
        cols = st.columns([4, 1, 1])
        cols[0].write(row["name"])

        if cols[1].button("Edit", key=f"tag_edit_{tag_id}"):
            st.session_state["tag_editing_id"] = tag_id
            st.session_state["tag_confirm_delete_id"] = None
            st.rerun()

        if cols[2].button("Delete", key=f"tag_delete_{tag_id}"):
            st.session_state["tag_confirm_delete_id"] = tag_id
            st.session_state["tag_editing_id"] = None
            st.rerun()

# ── Delete confirmation ───────────────────────────────────────────────────────

confirm_id = st.session_state["tag_confirm_delete_id"]
if confirm_id is not None:
    try:
        target = fetch_one("SELECT name FROM tags WHERE id = %s", (confirm_id,))
    except Exception as e:
        st.error(f"Could not load tag.\n\n`{e}`")
        target = None

    if target:
        st.divider()
        st.warning(f'Are you sure you want to delete **"{target["name"]}"**? This cannot be undone.')
        c1, c2 = st.columns([1, 5])
        if c1.button("Yes, delete", type="primary"):
            try:
                delete_tag(confirm_id)
                st.session_state["tag_confirm_delete_id"] = None
                st.success(f'Tag "{target["name"]}" deleted.')
                st.rerun()
            except Exception as e:
                st.error(f"Failed to delete tag.\n\n`{e}`")
                st.session_state["tag_confirm_delete_id"] = None
        if c2.button("Cancel"):
            st.session_state["tag_confirm_delete_id"] = None
            st.rerun()

# ── Edit form ─────────────────────────────────────────────────────────────────

editing_id = st.session_state["tag_editing_id"]
if editing_id is not None:
    try:
        current = fetch_one("SELECT id, name FROM tags WHERE id = %s", (editing_id,))
    except Exception as e:
        st.error(f"Could not load tag details.\n\n`{e}`")
        st.stop()

    if current is None:
        st.error("Tag not found.")
        st.session_state["tag_editing_id"] = None
        st.stop()

    st.divider()
    st.subheader(f'Edit "{current["name"]}"')

    with st.form("edit_tag_form"):
        edit_name = st.text_input("Tag Name", value=current["name"], max_chars=100)
        s_col, c_col = st.columns([1, 5])
        save_clicked = s_col.form_submit_button("Save Changes", type="primary")
        cancel_clicked = c_col.form_submit_button("Cancel")

    if cancel_clicked:
        st.session_state["tag_editing_id"] = None
        st.rerun()

    if save_clicked:
        if not edit_name.strip():
            st.error("Tag name is required.")
        else:
            try:
                update_tag(editing_id, edit_name.strip())
                st.session_state["tag_editing_id"] = None
                st.success(f'Tag updated to "{edit_name.strip()}".')
                st.rerun()
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Failed to update tag.\n\n`{e}`")
