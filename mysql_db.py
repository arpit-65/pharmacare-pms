"""
=============================================================================
  mysql_db.py — MySQL Database Connection Module
  Pharmacy Management System
=============================================================================
  Author  : Senior Python Database Engineer
  Library : mysql-connector-python
  Database: pharma_db (auto-created on first run)

  Usage:
      from mysql_db import get_connection, initialize_database

      # Initialize once on app startup
      initialize_database()

      # Fetch rows as dicts anywhere in your code
      conn   = get_connection()
      cursor = conn.cursor(dictionary=True)
      cursor.execute("SELECT * FROM inventory")
      rows   = cursor.fetchall()          # → list of dicts
      conn.close()
=============================================================================
"""

import hashlib
from datetime import datetime
import mysql.connector
from mysql.connector import Error


# ─── Connection Parameters ───────────────────────────────────────────────────
# Change these to match your MySQL installation.
# Never hard-code passwords in production — use environment variables instead.

DB_CONFIG = {
    "host"     : "localhost",
    "port"     : 3306,
    "user"     : "root",
    "password" : "YOUR_PASSWORD",     # ← Replace with your MySQL root password
    "database" : "pharma_db",
    "charset"  : "utf8mb4",
    "collation": "utf8mb4_unicode_ci",
    "autocommit": False,
}


# ─── Reusable Connection Function ────────────────────────────────────────────

def get_connection() -> mysql.connector.MySQLConnection:
    """
    Create and return a MySQL connection using the global DB_CONFIG.

    Returns:
        mysql.connector.MySQLConnection — an open, verified connection.

    Raises:
        SystemExit — prints a clear error and exits if unable to connect,
                     so the calling GUI code never receives a broken object.
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)

        if conn.is_connected():
            return conn

    except Error as e:
        # ── Friendly, actionable error messages ──────────────────────────
        if e.errno == mysql.connector.errorcode.ER_ACCESS_DENIED_ERROR:
            print("❌ Access Denied — wrong username or password in DB_CONFIG.")
        elif e.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:
            # Database not yet created — handled by initialize_database()
            print("⚠️  Database 'pharma_db' does not exist yet. Run initialize_database() first.")
        elif "Can't connect" in str(e) or "Connection refused" in str(e):
            print("❌ Cannot reach MySQL server.")
            print("   Fix: Open Services (services.msc) → start 'MySQL80'")
            print("   OR:  Open PowerShell as Admin → run: net start MySQL80")
        else:
            print(f"❌ MySQL Error [{e.errno}]: {e.msg}")

        raise SystemExit(1)


def get_cursor(conn: mysql.connector.MySQLConnection,
               dictionary: bool = True,
               buffered: bool = True):
    """
    Return a cursor from an open connection.

    Args:
        conn       : An open MySQLConnection object.
        dictionary : If True (default), rows are fetched as dicts instead
                     of tuples — much easier to integrate with GUI table code.
        buffered   : Fetches all results server-side immediately, avoiding
                     'Unread result found' errors when reusing connections.

    Returns:
        mysql.connector.cursor.MySQLCursorDict (or Buffered variant)

    Example:
        cursor = get_cursor(conn)
        cursor.execute("SELECT * FROM inventory WHERE quantity < %s", (10,))
        low_stock_items = cursor.fetchall()
        # → [{"id": 1, "med_name": "Paracetamol", "quantity": 5, ...}, ...]
    """
    return conn.cursor(dictionary=dictionary, buffered=buffered)


# ─── Database & Table Initialization ─────────────────────────────────────────

def initialize_database() -> None:
    """
    One-time setup function — call this on application startup.

    Steps:
      1. Connects to MySQL *without* specifying a database (server-level).
      2. Creates the 'pharma_db' database if it does not already exist.
      3. Reconnects with 'pharma_db' selected.
      4. Creates all required tables if they don't already exist.
      5. Seeds the default admin user if the users table is empty.
    """

    # ── Step 1: Connect at server level (no database selected yet) ────────
    server_cfg = {k: v for k, v in DB_CONFIG.items()
                  if k not in ("database", "autocommit")}
    try:
        server_conn = mysql.connector.connect(**server_cfg)
    except Error as e:
        print(f"❌ Cannot connect to MySQL server: {e}")
        print("   Make sure MySQL is running (net start MySQL80 as Admin).")
        raise SystemExit(1)

    # ── Step 2: Create database if it doesn't exist ───────────────────────
    cursor = server_conn.cursor()
    try:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` "
            f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        server_conn.commit()
        print(f"✅ Database '{DB_CONFIG['database']}' is ready.")
    except Error as e:
        print(f"❌ Failed to create database: {e}")
        raise SystemExit(1)
    finally:
        cursor.close()
        server_conn.close()

    # ── Step 3: Connect with database selected ────────────────────────────
    conn = get_connection()
    cur  = get_cursor(conn, dictionary=False)  # DDL doesn't need dict rows

    # ── Step 4: Create tables ─────────────────────────────────────────────

    # -- users: login credentials & roles --
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INT          PRIMARY KEY AUTO_INCREMENT,
            username   VARCHAR(100) NOT NULL UNIQUE,
            password   VARCHAR(255) NOT NULL COMMENT 'SHA-256 hex digest',
            role       ENUM('Admin','Pharmacist') NOT NULL DEFAULT 'Pharmacist',
            created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # -- inventory: medicine stock --
    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id             INT           PRIMARY KEY AUTO_INCREMENT,
            med_name       VARCHAR(200)  NOT NULL,
            category       VARCHAR(100)  NOT NULL,
            batch_id       VARCHAR(100)  NOT NULL,
            expiry_date    DATE          NOT NULL,
            quantity       INT           NOT NULL DEFAULT 0,
            price_per_unit DECIMAL(10,2) NOT NULL DEFAULT 0.00,
            created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                                         ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_med_name (med_name),
            INDEX idx_expiry   (expiry_date),
            INDEX idx_category (category)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # -- transactions: sales ledger --
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id            INT           PRIMARY KEY AUTO_INCREMENT,
            med_id        INT           NOT NULL,
            qty_sold      INT           NOT NULL,
            total_amount  DECIMAL(10,2) NOT NULL,
            customer_name VARCHAR(200)  NOT NULL DEFAULT 'Walk-in',
            timestamp     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_med
                FOREIGN KEY (med_id) REFERENCES inventory(id)
                ON DELETE RESTRICT ON UPDATE CASCADE,
            INDEX idx_timestamp (timestamp),
            INDEX idx_med_id    (med_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # ── Step 5: Seed default admin (only if users table is empty) ─────────
    cur.execute("SELECT COUNT(*) AS cnt FROM users")
    count = cur.fetchone()[0]
    if count == 0:
        admin_hash = hashlib.sha256("admin123".encode("utf-8")).hexdigest()
        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
            ("admin", admin_hash, "Admin"),
        )
        print("✅ Default admin seeded  →  username: admin  |  password: admin123")

    conn.commit()
    cur.close()
    conn.close()
    print("✅ All tables initialized. Database setup complete.\n")


# ─── Convenience Helpers ──────────────────────────────────────────────────────

def execute_query(sql: str,
                  params: tuple = (),
                  fetch: str = "all") -> list | dict | None:
    """
    One-liner helper for simple SELECT queries.

    Args:
        sql    : SQL string with %s placeholders.
        params : Tuple of values to bind.
        fetch  : "all" → list of dicts,  "one" → single dict or None.

    Returns:
        list[dict] | dict | None

    Example:
        rows = execute_query(
            "SELECT * FROM inventory WHERE category = %s",
            ("Antibiotic",)
        )
        for row in rows:
            print(row["med_name"], row["quantity"])
    """
    conn   = get_connection()
    cursor = get_cursor(conn)
    try:
        cursor.execute(sql, params)
        return cursor.fetchall() if fetch == "all" else cursor.fetchone()
    except Error as e:
        print(f"❌ Query error: {e}\n   SQL: {sql}")
        return [] if fetch == "all" else None
    finally:
        cursor.close()
        conn.close()


def execute_write(sql: str, params: tuple = ()) -> int:
    """
    One-liner helper for INSERT / UPDATE / DELETE statements.

    Args:
        sql    : SQL string with %s placeholders.
        params : Tuple of values to bind.

    Returns:
        int — number of affected rows, or -1 on error.

    Example:
        rows_affected = execute_write(
            "UPDATE inventory SET quantity = %s WHERE id = %s",
            (50, 3)
        )
    """
    conn   = get_connection()
    cursor = get_cursor(conn)
    try:
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount
    except Error as e:
        conn.rollback()
        print(f"❌ Write error: {e}\n   SQL: {sql}")
        return -1
    finally:
        cursor.close()
        conn.close()


def hash_password(password: str) -> str:
    """SHA-256 hash for secure password storage."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# ─── Quick Test (run this file directly to verify connection) ─────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  💊 PharmaCare — MySQL Connection Test")
    print("=" * 55)

    # Test: initialize everything
    initialize_database()

    # Test: query with dictionary cursor
    conn   = get_connection()
    cursor = get_cursor(conn)   # dictionary=True by default

    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    print(f"\n📋 Tables in '{DB_CONFIG['database']}':")
    for t in tables:
        table_name = list(t.values())[0]
        print(f"   • {table_name}")

    # Test: execute_query helper
    users = execute_query("SELECT username, role FROM users")
    print(f"\n👥 Users:")
    for u in users:
        print(f"   • {u['username']}  [{u['role']}]")

    cursor.close()
    conn.close()
    print("\n✅ All tests passed — MySQL is connected and ready!\n")
