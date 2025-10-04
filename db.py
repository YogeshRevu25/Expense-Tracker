# db.py
import sqlite3
import pandas as pd
import os
from datetime import datetime, date

BASE_DIR = os.path.dirname(__file__)
DB_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DB_DIR, "expenses.db")

def _ensure_db_dir():
    os.makedirs(DB_DIR, exist_ok=True)

def get_conn(path=DB_PATH):
    _ensure_db_dir()
    conn = sqlite3.connect(path, check_same_thread=False)
    return conn

def init_db(path=DB_PATH):
    conn = get_conn(path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,           -- stored as 'YYYY-MM-DD'
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()

def add_expense(amount, category, date_str, notes=None, path=DB_PATH):
    """
    amount: float
    category: str
    date_str: 'YYYY-MM-DD' or a datetime/date object
    """
    if isinstance(date_str, (date, datetime)):
        date_str = date_str.strftime("%Y-%m-%d")
    conn = get_conn(path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expenses (amount, category, date, notes) VALUES (?, ?, ?, ?)",
        (float(amount), category, date_str, notes)
    )
    conn.commit()
    conn.close()

def fetch_expenses(path=DB_PATH):
    """
    Returns a pandas DataFrame with columns:
    id, amount, category, date (datetime64[ns]), notes, created_at
    """
    conn = get_conn(path)
    df = pd.read_sql_query("SELECT * FROM expenses ORDER BY date DESC, created_at DESC", conn)
    conn.close()
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
    return df

# Optional helper to add demo data (call manually)
def add_demo_data(path=DB_PATH):
    import random
    import pandas as pd
    init_db(path)
    categories = ["Housing", "Food", "Transportation", "Utilities", "Entertainment", "Healthcare", "Other"]
    today = datetime.today()
    for i in range(60):
        d = (today - pd.Timedelta(days=random.randint(0, 365))).date()
        add_expense(
            amount=round(random.uniform(5, 800), 2),
            category=random.choice(categories),
            date_str=d.strftime("%Y-%m-%d"),
            notes="Demo expense"
        )
