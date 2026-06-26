import csv
from flask import Flask, render_template, request, redirect, session, Response
from datetime import datetime
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DB CONNECTION ----------------
def get_db():
    return sqlite3.connect("complaints.db")


# ---------------- INIT DB ----------------
def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # USERS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    # COMPLAINTS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        mobile TEXT,
        location TEXT,
        category TEXT,
        issue TEXT,
        status TEXT,
        created_at TEXT
    )
    """)

    # INSERT ADMIN (SAFE)
    cursor.execute("SELECT * FROM users WHERE username=?", ("admin123@gmail.com",))
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO users(username,password,role) VALUES (?,?,?)",
            ("admin123@gmail.com", generate_password_hash("admin123"), "admin")
        )

    conn.commit()
    conn.close()


# ---------------- HOME ----------------
@app.route('/')
def home():
    return render_template("login.html")


# ---------------- LOGIN ----------------
@app.route('/login', methods=['POST'])
def login():

    username = request.form['username']
    password = request.form['password']
    role = request.form['role']

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE username=? AND role=?",
        (username, role)
    )

    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user[2], password):
        session['user'] = username
        session['role'] = role

        if role == "admin":
            return redirect('/admin_dashboard')
        else:
            return redirect('/report')

    return "Invalid Login ❌"


# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']

        hashed = generate_password_hash(password)

        conn = get_db()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users(username,password,role) VALUES (?,?,?)",
                (username, hashed, "user")
            )
            conn.commit()
        except:
            return "User already exists ❌"

        conn.close()
        return redirect('/')

    return render_template("register.html")


# ---------------- REPORT ----------------
@app.route('/report', methods=['GET', 'POST'])
def report():

    if request.method == "POST":

        name = request.form.get('name')
        mobile = request.form.get('mobile')
        location = request.form.get('location')
        category = request.form.get('category')
        issue = request.form.get('issue')

        if not name or not mobile or not location or not issue:
            return render_template("report.html", error="All fields required ❌")

        if len(mobile) != 10 or not mobile.isdigit():
            return render_template("report.html", error="Invalid mobile ❌")

        if len(issue) < 10:
            return render_template("report.html", error="Issue too short ❌")

        created_at = datetime.now().strftime("%Y-%m-%d")

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO complaints
        (name, mobile, location, category, issue, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, mobile, location, category, issue, "Pending", created_at))

        conn.commit()
        conn.close()

        return redirect("/dashboard")

    return render_template("report.html")


# ---------------- USER DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM complaints")
    data = cursor.fetchall()

    conn.close()

    return render_template("dashboard.html", data=data)


# ---------------- ADMIN DASHBOARD ----------------
@app.route('/admin_dashboard')
def admin_dashboard():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM complaints")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending'")
    pending = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'")
    resolved = cursor.fetchone()[0]

    today_date = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE created_at=?", (today_date,))
    today = cursor.fetchone()[0]

    cursor.execute("SELECT location, COUNT(*) FROM complaints GROUP BY location")
    village_data = cursor.fetchall()

    villages = [v[0] for v in village_data]
    counts = [v[1] for v in village_data]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total=total,
        pending=pending,
        resolved=resolved,
        today=today,
        villages=villages,
        counts=counts
    )


# ---------------- UPDATE STATUS ----------------
@app.route('/update_status/<int:id>/<string:new_status>')
def update_status(id, new_status):

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("UPDATE complaints SET status=? WHERE id=?", (new_status, id))

    conn.commit()
    conn.close()

    return redirect('/dashboard')


# ---------------- EXPORT CSV ----------------
@app.route('/export')
def export():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM complaints")
    data = cursor.fetchall()
    conn.close()

    def generate():
        yield "ID,Name,Mobile,Location,Category,Issue,Status,Date\n"
        for row in data:
            yield ",".join(map(str, row)) + "\n"

    return Response(generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=complaints.csv"})


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ---------------- RUN ----------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)