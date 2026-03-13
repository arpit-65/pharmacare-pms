"""
==========================================================
 Cloud MySQL Setup for PharmaCare
 
 HOW TO USE:
 1. Sign up FREE at: https://www.freesqldatabase.com
 2. Copy your credentials from the dashboard
 3. Paste them into the variables below (lines 20-24)
 4. Run: python connect_mysql_cloud.py
==========================================================
"""
import sys, os, hashlib

# ══════════════════════════════════════════════════════════
#   STEP 1: PASTE YOUR CREDENTIALS HERE
#   Get them from: https://www.freesqldatabase.com
# ══════════════════════════════════════════════════════════

MYSQL_HOST     = "sql12.freesqldatabase.com"
MYSQL_PORT     = 3306
MYSQL_USER     = "sql12819794"
MYSQL_PASSWORD = "P7ZdU9fXph"
MYSQL_DATABASE = "sql12819794"

# ══════════════════════════════════════════════════════════
#   STEP 2: SAVE THIS FILE then run:
#   python connect_mysql_cloud.py
# ══════════════════════════════════════════════════════════


# ── Validation ────────────────────────────────────────────
if not MYSQL_HOST or not MYSQL_USER or not MYSQL_PASSWORD or not MYSQL_DATABASE:
    print("=" * 55)
    print("  ⚠️  Please fill in your credentials above first!")
    print("=" * 55)
    print()
    print("  1. Open: https://www.freesqldatabase.com")
    print("  2. Sign up for free")
    print("  3. Copy the Host, Username, Password, Database")
    print("  4. Paste them into this file (lines 20-24)")
    print("  5. Save the file")
    print("  6. Run: python connect_mysql_cloud.py")
    print()
    sys.exit(0)

# ── Connect & Setup ───────────────────────────────────────
import pymysql

print("=" * 55)
print("  PharmaCare - Cloud MySQL Setup")
print("=" * 55)
print(f"\nConnecting to {MYSQL_HOST}...")

try:
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        connect_timeout=10
    )
    print("Connected successfully!\n")

    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       INT PRIMARY KEY AUTO_INCREMENT,
            username VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            role     VARCHAR(20)  NOT NULL DEFAULT 'Pharmacist'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id             INT PRIMARY KEY AUTO_INCREMENT,
            med_name       VARCHAR(200)  NOT NULL,
            category       VARCHAR(100)  NOT NULL,
            batch_id       VARCHAR(100)  NOT NULL,
            expiry_date    VARCHAR(20)   NOT NULL,
            quantity       INT           NOT NULL DEFAULT 0,
            price_per_unit DECIMAL(10,2) NOT NULL DEFAULT 0.00
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id            INT PRIMARY KEY AUTO_INCREMENT,
            med_id        INT           NOT NULL,
            qty_sold      INT           NOT NULL,
            total_amount  DECIMAL(10,2) NOT NULL,
            customer_name VARCHAR(200)  NOT NULL DEFAULT 'Walk-in',
            timestamp     VARCHAR(30)   NOT NULL
        )
    """)

    # Seed admin user
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        pwd = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
            ("admin", pwd, "Admin")
        )
        print("Admin user created: username=admin  password=admin123")

    conn.commit()
    cursor.close()
    conn.close()

    print("All tables created!")

    # Update Flask db_manager.py automatically
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "db_manager.py")
    if os.path.exists(db_path):
        with open(db_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace('MYSQL_HOST = "localhost"',        f'MYSQL_HOST = "{MYSQL_HOST}"')
        content = content.replace('MYSQL_USER = "root"',             f'MYSQL_USER = "{MYSQL_USER}"')
        content = content.replace('MYSQL_PASSWORD = ""',             f'MYSQL_PASSWORD = "{MYSQL_PASSWORD}"')
        content = content.replace('MYSQL_DATABASE = "pharmacy_db"',  f'MYSQL_DATABASE = "{MYSQL_DATABASE}"')
        with open(db_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Flask app updated (web/db_manager.py)")

    print()
    print("=" * 55)
    print("  STREAMLIT CLOUD SECRETS")
    print("  Copy & paste into:")
    print("  share.streamlit.io → App → Settings → Secrets")
    print("=" * 55)
    print()
    print("[mysql]")
    print(f'host     = "{MYSQL_HOST}"')
    print(f'port     = {MYSQL_PORT}')
    print(f'user     = "{MYSQL_USER}"')
    print(f'password = "{MYSQL_PASSWORD}"')
    print(f'database = "{MYSQL_DATABASE}"')
    print()
    print("=" * 55)
    print("ALL DONE! Restart Flask: python web/app.py")
    print("   You will see: MySQL connected")
    print("=" * 55)

except Exception as e:
    print(f"\nConnection failed: {e}")
    print()
    print("Check:")
    print("  • MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE")
    print("    in the top of this file are filled in correctly")
    print("  • You signed up at https://www.freesqldatabase.com")
    print("  • Copy the credentials exactly from the dashboard")
