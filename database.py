import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "barber_management.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS customers(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT NOT NULL UNIQUE,
        email TEXT DEFAULT '', notes TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS services(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, description TEXT DEFAULT '',
        price REAL NOT NULL CHECK(price >= 0), duration_minutes INTEGER NOT NULL DEFAULT 30,
        active INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS staff(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT NOT NULL UNIQUE,
        role TEXT NOT NULL DEFAULT 'Barber', commission_percent REAL NOT NULL DEFAULT 0,
        active INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS appointments(
        id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER NOT NULL REFERENCES customers(id),
        service_id INTEGER NOT NULL REFERENCES services(id), staff_id INTEGER REFERENCES staff(id),
        appointment_date TEXT NOT NULL, appointment_time TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Booked', notes TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS inventory(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, quantity REAL NOT NULL DEFAULT 0,
        unit TEXT NOT NULL DEFAULT 'pcs', reorder_level REAL NOT NULL DEFAULT 5,
        unit_cost REAL NOT NULL DEFAULT 0, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS bills(
        id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER NOT NULL REFERENCES customers(id),
        subtotal REAL NOT NULL, discount_percent REAL NOT NULL DEFAULT 0, tax_percent REAL NOT NULL DEFAULT 0,
        tax_amount REAL NOT NULL DEFAULT 0, total REAL NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS bill_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT, bill_id INTEGER NOT NULL REFERENCES bills(id),
        service_id INTEGER NOT NULL REFERENCES services(id), description TEXT NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1, unit_price REAL NOT NULL, line_total REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS chat_logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_message TEXT NOT NULL, bot_reply TEXT NOT NULL,
        intent TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(appointment_date, appointment_time);
    CREATE INDEX IF NOT EXISTS idx_bills_created ON bills(created_at);
    """)
    if db.execute("SELECT COUNT(*) FROM services").fetchone()[0] == 0:
        db.executemany("INSERT INTO services(name,description,price,duration_minutes) VALUES(?,?,?,?)", [
            ("Haircut","Classic haircut",150,30), ("Beard Trim","Beard shaping and trim",80,15),
            ("Haircut + Beard","Haircut with beard trim",220,45), ("Hair Wash","Hair wash and styling",100,20),
            ("Facial","Basic facial service",350,45), ("Kids Haircut","Haircut for children",120,25)
        ])
    if db.execute("SELECT COUNT(*) FROM inventory").fetchone()[0] == 0:
        db.executemany("INSERT INTO inventory(name,quantity,unit,reorder_level,unit_cost) VALUES(?,?,?,?,?)", [
            ("Shampoo",8,"bottles",3,180), ("Hair gel",6,"jars",2,120), ("Disposable blades",25,"pcs",10,5)
        ])
    db.commit()
    db.close()
