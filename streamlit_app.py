"""
=============================================================================
 STREAMLIT PHARMACY MANAGEMENT SYSTEM
=============================================================================
 Database: MySQL (via Streamlit Secrets) or SQLite (local fallback)
 Deploy for FREE on Streamlit Community Cloud.

 To use MySQL on cloud, add this to Streamlit Cloud → Settings → Secrets:
   [mysql]
   host     = "your-mysql-host"
   port     = 3306
   user     = "your-user"
   password = "your-password"
   database = "pharmacy_db"
=============================================================================
"""

import streamlit as st
import hashlib
import pandas as pd
import os
from datetime import datetime, timedelta

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="💊 PharmaCare — Management System",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pharmacy.db")

# ─── Database Engine Detection ───────────────────────────────────────────────
_USE_MYSQL = False
try:
    if "mysql" in st.secrets:
        import mysql.connector
        _USE_MYSQL = True
except Exception:
    pass

import sqlite3   # always available as fallback


# ─── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Premium dark theme overrides for Streamlit */
[data-testid="stSidebar"] { background: #0e1119 !important; }
[data-testid="stSidebar"] h1 { color: #3b82f6; }
.metric-card {
    background: #141822;
    border: 1px solid #1e2538;
    border-radius: 12px;
    padding: 18px 20px;
    text-align: center;
}
.alert-orange {
    background: rgba(249,115,22,0.12);
    border-left: 3px solid #f97316;
    padding: 10px 14px;
    border-radius: 6px;
    color: #fdba74;
    margin: 4px 0;
}
.alert-red {
    background: rgba(239,68,68,0.10);
    border-left: 3px solid #ef4444;
    padding: 10px 14px;
    border-radius: 6px;
    color: #fca5a5;
    margin: 4px 0;
}
</style>
""", unsafe_allow_html=True)


# ─── Database Helpers ────────────────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_pwd(pwd): return hashlib.sha256(pwd.encode()).hexdigest()


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        med_name TEXT NOT NULL,
        category TEXT NOT NULL,
        batch_id TEXT NOT NULL,
        expiry_date TEXT NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 0,
        price_per_unit REAL NOT NULL DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        med_id INTEGER NOT NULL,
        qty_sold INTEGER NOT NULL,
        total_amount REAL NOT NULL,
        customer_name TEXT NOT NULL DEFAULT 'Walk-in',
        timestamp TEXT NOT NULL,
        FOREIGN KEY (med_id) REFERENCES inventory(id))""")
    # Seed admin
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)",
                  ("admin", hash_pwd("admin123"), "Admin"))
    conn.commit(); conn.close()


init_db()


# ─── SESSION STATE SETUP ─────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username  = ""
    st.session_state.role      = ""
    st.session_state.cart      = []


# ═══════════════════════════════════════════════════════════════════════════════
#  LOGIN PAGE
# ═══════════════════════════════════════════════════════════════════════════════
def login_page():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("## 💊 PharmaCare")
        st.markdown("#### Sign in to your account")
        st.divider()

        tab_login, tab_signup = st.tabs(["Sign In", "Create Account"])

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="admin")
                password = st.text_input("Password", type="password", placeholder="admin123")
                submitted = st.form_submit_button("Sign In", use_container_width=True)
                if submitted:
                    conn = get_conn()
                    c = conn.cursor()
                    c.execute("SELECT id,username,role FROM users WHERE username=? AND password=?",
                              (username, hash_pwd(password)))
                    user = c.fetchone(); conn.close()
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.username  = user[1]
                        st.session_state.role      = user[2]
                        st.success(f"Welcome, {user[1]}!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

        with tab_signup:
            with st.form("signup_form"):
                new_user = st.text_input("Username")
                new_pwd  = st.text_input("Password", type="password")
                conf_pwd = st.text_input("Confirm Password", type="password")
                role     = st.selectbox("Role", ["Pharmacist", "Admin"])
                submitted2 = st.form_submit_button("Create Account", use_container_width=True)
                if submitted2:
                    if len(new_user) < 3 or len(new_pwd) < 4:
                        st.warning("Username ≥ 3 chars, password ≥ 4 chars.")
                    elif new_pwd != conf_pwd:
                        st.error("Passwords do not match.")
                    else:
                        try:
                            conn = get_conn()
                            conn.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)",
                                         (new_user, hash_pwd(new_pwd), role))
                            conn.commit(); conn.close()
                            st.success(f"Account '{new_user}' created! Sign in now.")
                        except Exception:
                            st.error("Username already exists.")


# ═══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR NAVIGATION (when logged in)
# ═══════════════════════════════════════════════════════════════════════════════
def sidebar():
    with st.sidebar:
        st.markdown("### 💊 PharmaCare")
        st.markdown(f"**{st.session_state.username}** · *{st.session_state.role}*")
        st.divider()

        pages = ["📊 Dashboard", "📦 Inventory", "🛒 Sales / POS", "📋 Reports"]
        if st.session_state.role == "Admin":
            pages.append("👥 Users")

        page = st.radio("Navigate", pages, label_visibility="collapsed")
        st.divider()

        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.role = ""
            st.session_state.cart = []
            st.rerun()

    return page


# ═══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
def show_dashboard():
    st.title("📊 Dashboard")
    conn = get_conn(); c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM inventory")
    total_meds = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(quantity),0) FROM inventory")
    total_stock = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM inventory WHERE quantity < 10")
    low_stock = c.fetchone()[0]
    today = datetime.now().strftime("%Y-%m-%d")
    thirty = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM inventory WHERE expiry_date BETWEEN ? AND ?", (today, thirty))
    exp_soon = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(total_amount),0) FROM transactions")
    total_rev = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(total_amount),0) FROM transactions WHERE timestamp LIKE ?",
              (today+"%",))
    today_sales = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM transactions")
    total_tx = c.fetchone()[0]
    conn.close()

    # Metrics row 1
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💊 Medicines", total_meds)
    c2.metric("📦 Total Stock", f"{total_stock:,}")
    c3.metric("⚠️ Low Stock", low_stock, delta=f"-{low_stock}" if low_stock else None,
              delta_color="inverse")
    c4.metric("⏰ Expiring Soon", exp_soon, delta=f"≤30 days" if exp_soon else None,
              delta_color="inverse")

    # Metrics row 2
    c5, c6, c7 = st.columns(3)
    c5.metric("💰 Total Revenue", f"₹{total_rev:,.2f}")
    c6.metric("📈 Today's Sales", f"₹{today_sales:,.2f}")
    c7.metric("🧾 Transactions", total_tx)

    # Backup button (admin)
    if st.session_state.role == "Admin":
        st.divider()
        st.subheader("☁️ Offline-First Cloud Backup")
        st.info("Data is stored locally in SQLite. Download a backup ZIP and upload to Google Drive / Dropbox.")
        if os.path.exists(DB_PATH):
            with open(DB_PATH, "rb") as f:
                db_bytes = f.read()
            st.download_button("💾 Download Database Backup",
                               data=db_bytes,
                               file_name=f"pharmacy_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
                               mime="application/octet-stream")

    # Alerts
    st.divider()
    st.subheader("🔔 Alerts")
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT med_name, expiry_date, quantity FROM inventory")
    items = c.fetchall(); conn.close()

    alerts_shown = 0
    today_dt = datetime.now()
    for med_name, exp_str, qty in items:
        if qty < 10:
            st.markdown(f'<div class="alert-red">⚠️ <strong>{med_name}</strong> — Low stock ({qty} units)</div>',
                        unsafe_allow_html=True)
            alerts_shown += 1
        try:
            exp_dt = datetime.strptime(exp_str, "%Y-%m-%d")
            days = (exp_dt - today_dt).days
            if days < 0:
                st.markdown(f'<div class="alert-red">🔴 <strong>{med_name}</strong> — EXPIRED on {exp_str}</div>',
                            unsafe_allow_html=True)
                alerts_shown += 1
            elif days <= 30:
                st.markdown(f'<div class="alert-red">🔴 <strong>{med_name}</strong> — Expires in {days} days</div>',
                            unsafe_allow_html=True)
                alerts_shown += 1
            elif days <= 60:
                st.markdown(f'<div class="alert-orange">🟠 <strong>{med_name}</strong> — Expires in {days} days</div>',
                            unsafe_allow_html=True)
                alerts_shown += 1
        except ValueError:
            pass
    if alerts_shown == 0:
        st.success("✅ All clear — no alerts.")


# ═══════════════════════════════════════════════════════════════════════════════
#  INVENTORY
# ═══════════════════════════════════════════════════════════════════════════════
def show_inventory():
    st.title("📦 Inventory Management")

    # Barcode / keyword search
    search = st.text_input("🔍 Search or scan barcode here...", placeholder="Type or scan barcode")

    conn = get_conn(); c = conn.cursor()
    if search:
        c.execute("""SELECT id,med_name,category,batch_id,expiry_date,quantity,price_per_unit
                     FROM inventory WHERE med_name LIKE ? OR category LIKE ?""",
                  (f"%{search}%", f"%{search}%"))
    else:
        c.execute("SELECT id,med_name,category,batch_id,expiry_date,quantity,price_per_unit FROM inventory ORDER BY med_name")
    rows = c.fetchall()
    conn.close()

    # Build DataFrame with expiry countdown
    today_dt = datetime.now()
    records = []
    for r in rows:
        try:
            days_left = (datetime.strptime(r[4], "%Y-%m-%d") - today_dt).days
        except ValueError:
            days_left = None
        records.append({
            "ID": r[0], "Medicine": r[1], "Category": r[2], "Batch": r[3],
            "Expiry": r[4], "Days Left": days_left, "Qty": r[5], "Price (₹)": r[6],
        })
    df = pd.DataFrame(records)

    # Colour highlights via pandas Styler
    def colour_row(row):
        dl = row["Days Left"]
        qty = row["Qty"]
        if qty < 10 or (dl is not None and dl <= 30):
            return ['background-color: rgba(239,68,68,0.12); color: #fca5a5'] * len(row)
        elif dl is not None and dl <= 60:
            return ['background-color: rgba(249,115,22,0.10); color: #fdba74'] * len(row)
        return [''] * len(row)

    styled_df = df.style.apply(colour_row, axis=1)
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    st.divider()
    col_add, col_edit, col_del = st.columns(3)

    # ── Add Medicine
    with col_add:
        with st.expander("➕ Add Medicine"):
            with st.form("add_med_form", clear_on_submit=True):
                name    = st.text_input("Medicine Name")
                cat     = st.text_input("Category")
                batch   = st.text_input("Batch ID")
                expiry  = st.date_input("Expiry Date", min_value=datetime.today())
                qty     = st.number_input("Quantity", min_value=0, step=1)
                price   = st.number_input("Price per Unit (₹)", min_value=0.0, step=0.5)
                if st.form_submit_button("💾 Add", use_container_width=True):
                    conn = get_conn()
                    conn.execute("INSERT INTO inventory (med_name,category,batch_id,expiry_date,quantity,price_per_unit) VALUES (?,?,?,?,?,?)",
                                 (name, cat, batch, str(expiry), int(qty), float(price)))
                    conn.commit(); conn.close()
                    st.success("Medicine added!"); st.rerun()

    # ── Edit Medicine
    with col_edit:
        with st.expander("✏️ Edit Medicine"):
            conn = get_conn(); c = conn.cursor()
            c.execute("SELECT id, med_name FROM inventory ORDER BY med_name")
            meds = c.fetchall(); conn.close()
            if meds:
                sel = st.selectbox("Select", [f"{m[0]} — {m[1]}" for m in meds], key="edit_sel")
                med_id = int(sel.split("—")[0].strip())
                conn = get_conn(); c = conn.cursor()
                c.execute("SELECT * FROM inventory WHERE id=?", (med_id,))
                m = c.fetchone(); conn.close()
                if m:
                    with st.form("edit_med_form"):
                        en = st.text_input("Name", value=m[1])
                        ec = st.text_input("Category", value=m[2])
                        eb = st.text_input("Batch", value=m[3])
                        try: ed_default = datetime.strptime(m[4], "%Y-%m-%d").date()
                        except: ed_default = datetime.today().date()
                        ed = st.date_input("Expiry", value=ed_default)
                        eq = st.number_input("Quantity", value=m[5], min_value=0)
                        ep = st.number_input("Price", value=float(m[6]), min_value=0.0, step=0.5)
                        if st.form_submit_button("💾 Update", use_container_width=True):
                            conn = get_conn()
                            conn.execute("UPDATE inventory SET med_name=?,category=?,batch_id=?,expiry_date=?,quantity=?,price_per_unit=? WHERE id=?",
                                         (en, ec, eb, str(ed), int(eq), float(ep), med_id))
                            conn.commit(); conn.close()
                            st.success("Updated!"); st.rerun()

    # ── Delete Medicine
    with col_del:
        with st.expander("🗑️ Delete Medicine"):
            conn = get_conn(); c = conn.cursor()
            c.execute("SELECT id, med_name FROM inventory ORDER BY med_name")
            meds2 = c.fetchall(); conn.close()
            if meds2:
                sel2 = st.selectbox("Select to delete", [f"{m[0]} — {m[1]}" for m in meds2], key="del_sel")
                med_id2 = int(sel2.split("—")[0].strip())
                if st.button("🗑️ Confirm Delete", type="primary", use_container_width=True):
                    conn = get_conn()
                    conn.execute("DELETE FROM inventory WHERE id=?", (med_id2,))
                    conn.commit(); conn.close()
                    st.warning("Deleted."); st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
#  POINT OF SALE
# ═══════════════════════════════════════════════════════════════════════════════
def show_sales():
    st.title("🛒 Point of Sale")

    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT id,med_name,quantity,price_per_unit FROM inventory WHERE quantity > 0 ORDER BY med_name")
    meds = c.fetchall(); conn.close()

    if not meds:
        st.warning("No medicines in stock."); return

    col_left, col_right = st.columns([1, 1.2])

    with col_left:
        st.subheader("Select Medicine")
        customer     = st.text_input("Customer Name", value="Walk-in")
        customer_email = st.text_input("Customer Email (for receipt)", placeholder="optional@email.com")
        med_opts     = {f"{m[1]} (Stock: {m[2]}) — ₹{m[3]:.2f}": m for m in meds}
        chosen_label = st.selectbox("Medicine", list(med_opts.keys()))
        chosen       = med_opts[chosen_label]
        qty          = st.number_input("Quantity", min_value=1, max_value=int(chosen[2]), step=1)

        if st.button("🛒 Add to Cart", use_container_width=True):
            existing = [i for i in st.session_state.cart if i["med_id"] == chosen[0]]
            cart_qty = sum(i["qty"] for i in existing)
            if cart_qty + qty > chosen[2]:
                st.error(f"Not enough stock! Available: {chosen[2]}, in cart: {cart_qty}")
            else:
                st.session_state.cart.append({
                    "med_id": chosen[0], "name": chosen[1],
                    "qty": qty, "price": float(chosen[3]),
                    "subtotal": qty * float(chosen[3]),
                })
                st.success(f"Added {qty}× {chosen[1]}")
                st.rerun()

        if st.button("🗑️ Clear Cart"):
            st.session_state.cart = []
            st.rerun()

    with col_right:
        st.subheader("🧾 Cart")
        if not st.session_state.cart:
            st.info("Cart is empty.")
        else:
            cart_df = pd.DataFrame(st.session_state.cart)[["name","qty","price","subtotal"]]
            cart_df.columns = ["Medicine","Qty","Unit Price (₹)","Subtotal (₹)"]
            st.dataframe(cart_df, use_container_width=True, hide_index=True)

            subtotal = sum(i["subtotal"] for i in st.session_state.cart)
            tax      = subtotal * 0.05
            total    = subtotal + tax

            st.markdown(f"""
            | | |
            |---|---|
            | Subtotal | ₹{subtotal:.2f} |
            | Tax (5%) | ₹{tax:.2f} |
            | **TOTAL** | **₹{total:.2f}** |
            """)

            if st.button("💳 Generate Bill", use_container_width=True, type="primary"):
                # Validate + deduct stock
                conn = get_conn()
                errors = []
                for item in st.session_state.cart:
                    c = conn.cursor()
                    c.execute("SELECT quantity FROM inventory WHERE id=?", (item["med_id"],))
                    row = c.fetchone()
                    if not row or item["qty"] > row[0]:
                        errors.append(f"Insufficient stock for {item['name']}")
                if errors:
                    conn.close()
                    for e in errors: st.error(e)
                else:
                    for item in st.session_state.cart:
                        conn.execute("UPDATE inventory SET quantity=quantity-? WHERE id=?",
                                     (item["qty"], item["med_id"]))
                        conn.execute("INSERT INTO transactions (med_id,qty_sold,total_amount,customer_name,timestamp) VALUES (?,?,?,?,?)",
                                     (item["med_id"], item["qty"],
                                      item["subtotal"]*(1.05), customer,
                                      datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit(); conn.close()
                    st.success(f"✅ Sale complete! Total: ₹{total:.2f}")
                    if customer_email:
                        st.info(f"📧 To send email receipt, configure SMTP in receipt_utils.py")
                    st.session_state.cart = []
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
#  REPORTS
# ═══════════════════════════════════════════════════════════════════════════════
def show_reports():
    st.title("📋 Sales Reports")

    col1, col2, col3 = st.columns([1, 1, 1.5])
    with col1:
        start = st.date_input("From", value=(datetime.now()-timedelta(days=30)).date())
    with col2:
        end   = st.date_input("To", value=datetime.now().date())
    with col3:
        show_all = st.checkbox("Show all transactions")

    conn = get_conn(); c = conn.cursor()
    if show_all:
        c.execute("""SELECT t.id, i.med_name, t.qty_sold, t.total_amount,
                            t.customer_name, t.timestamp
                     FROM transactions t JOIN inventory i ON t.med_id=i.id
                     ORDER BY t.timestamp DESC""")
    else:
        c.execute("""SELECT t.id, i.med_name, t.qty_sold, t.total_amount,
                            t.customer_name, t.timestamp
                     FROM transactions t JOIN inventory i ON t.med_id=i.id
                     WHERE t.timestamp >= ? AND t.timestamp <= ?
                     ORDER BY t.timestamp DESC""",
                  (str(start), str(end) + " 23:59:59"))
    rows = c.fetchall(); conn.close()

    df = pd.DataFrame(rows, columns=["ID","Medicine","Qty","Total (₹)","Customer","Timestamp"])

    # Summary metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("🧾 Transactions", len(df))
    c2.metric("💰 Revenue", f"₹{df['Total (₹)'].sum():.2f}" if not df.empty else "₹0.00")
    c3.metric("📦 Units Sold", int(df["Qty"].sum()) if not df.empty else 0)

    st.dataframe(df, use_container_width=True, hide_index=True)

    # Bar chart — sales per medicine
    if not df.empty:
        st.subheader("📊 Revenue by Medicine")
        chart_data = df.groupby("Medicine")["Total (₹)"].sum().reset_index()
        chart_data = chart_data.sort_values("Total (₹)", ascending=False).head(15)
        st.bar_chart(chart_data.set_index("Medicine"))

    # Export
    if not df.empty:
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Export CSV", data=csv,
                           file_name=f"report_{datetime.now().strftime('%Y%m%d')}.csv",
                           mime="text/csv")


# ═══════════════════════════════════════════════════════════════════════════════
#  USER MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════
def show_users():
    st.title("👥 User Management")
    st.warning("🔒 Admin Only")

    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT id,username,role FROM users")
    users = c.fetchall(); conn.close()

    df_users = pd.DataFrame(users, columns=["ID","Username","Role"])
    st.dataframe(df_users, use_container_width=True, hide_index=True)

    st.divider()
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("➕ Add User")
        with st.form("add_user_form", clear_on_submit=True):
            un = st.text_input("Username")
            pw = st.text_input("Password", type="password")
            rl = st.selectbox("Role", ["Pharmacist","Admin"])
            if st.form_submit_button("Create", use_container_width=True):
                try:
                    conn = get_conn()
                    conn.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)",
                                 (un, hash_pwd(pw), rl))
                    conn.commit(); conn.close()
                    st.success(f"User '{un}' created."); st.rerun()
                except Exception:
                    st.error("Username already exists.")

    with col_b:
        st.subheader("🗑️ Delete User")
        if users:
            del_sel = st.selectbox("Select", [f"{u[0]} — {u[1]}" for u in users])
            del_id  = int(del_sel.split("—")[0].strip())
            if st.button("Confirm Delete", type="primary"):
                conn = get_conn()
                conn.execute("DELETE FROM users WHERE id=?", (del_id,))
                conn.commit(); conn.close()
                st.warning("User deleted."); st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN ROUTER
# ═══════════════════════════════════════════════════════════════════════════════
if not st.session_state.logged_in:
    login_page()
else:
    page = sidebar()
    if page == "📊 Dashboard":
        show_dashboard()
    elif page == "📦 Inventory":
        show_inventory()
    elif page == "🛒 Sales / POS":
        show_sales()
    elif page == "📋 Reports":
        show_reports()
    elif page == "👥 Users":
        show_users()
