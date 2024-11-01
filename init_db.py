''' 
Database Setup
We use SQLite for simplicity. The database will handle user authentication, bookmarks, search history, and analytics.

Only run this once!
''' 

# init_db.py
import sqlite3
import bcrypt
import pandas as pd

# Connect to SQLite database
conn = sqlite3.connect('database/ketomed.db')
cursor = conn.cursor()

# Create Users table
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
''')

# Create Bookmarks table
cursor.execute('''
CREATE TABLE IF NOT EXISTS bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    drug_id INTEGER,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
''')

# Create Search History table
cursor.execute('''
CREATE TABLE IF NOT EXISTS search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    search_term TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
''')

# Create Analytics table
cursor.execute('''
CREATE TABLE IF NOT EXISTS analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT,
    drug_id INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
''')

conn.commit()

# Add initial users from users.csv
users_df = pd.read_csv('database/users.csv')

for index, row in users_df.iterrows():
    username = row['username']
    password = row['password']
    # Hash the password
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    try:
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed))
    except sqlite3.IntegrityError:
        print(f"User {username} already exists.")

conn.commit()
conn.close()
