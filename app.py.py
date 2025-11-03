from flask import Flask, render_template, request, redirect, session, g
import sqlite3, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "citibank2025"
DB_NAME = "banking.db"

# ---------- DATABASE SETUP ----------
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_NAME)
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    if not os.path.exists(DB_NAME):
        db = get_db()
        db.execute('''CREATE TABLE users(
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        password TEXT,
                        balance REAL DEFAULT 1000)''')
        db.execute('''CREATE TABLE transactions(
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sender TEXT,
                        receiver TEXT,
                        amount REAL,
                        timestamp TEXT)''')
        db.commit()

# ---------- ROUTES ----------
@app.route('/')
def home():
    if 'user' in session:
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password) VALUES (?,?)", (username, password))
            db.commit()
            return redirect('/login')
        except:
            return "Username already exists. Try again."
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password)).fetchone()
        if user:
            session['user'] = username
            return redirect('/dashboard')
        return "Invalid credentials!"
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    db = get_db()
    user = db.execute("SELECT balance FROM users WHERE username=?", (session['user'],)).fetchone()
    transactions = db.execute(
        "SELECT * FROM transactions WHERE sender=? OR receiver=? ORDER BY id DESC",
        (session['user'], session['user'])
    ).fetchall()
    return render_template('dashboard.html', user=session['user'], balance=user[0], transactions=transactions)

@app.route('/transfer', methods=['GET', 'POST'])
def transfer():
    if 'user' not in session:
        return redirect('/login')
    if request.method == 'POST':
        receiver = request.form['receiver']
        amount = float(request.form['amount'])
        db = get_db()
        sender_data = db.execute("SELECT balance FROM users WHERE username=?", (session['user'],)).fetchone()
        receiver_data = db.execute("SELECT balance FROM users WHERE username=?", (receiver,)).fetchone()

        if not receiver_data:
            return "Receiver not found!"
        if sender_data[0] < amount:
            return "Insufficient funds!"
        
        # Update balances
        db.execute("UPDATE users SET balance = balance - ? WHERE username=?", (amount, session['user']))
        db.execute("UPDATE users SET balance = balance + ? WHERE username=?", (amount, receiver))
        db.execute("INSERT INTO transactions (sender, receiver, amount, timestamp) VALUES (?,?,?,?)",
                   (session['user'], receiver, amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        db.commit()
        return redirect('/dashboard')
    return render_template('transfer.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)
