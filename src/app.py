from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "dropout_project_key"


def init_db():
    conn = sqlite3.connect("dropout.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        age INTEGER,
        department TEXT,
        cgpa REAL,
        attendance REAL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS predictions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        risk_level TEXT,
        prediction_date TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    conn.commit()
    conn.close()


init_db()


@app.route('/')
def home():
    return render_template('login.html')


@app.route('/register')
def register():
    return render_template('register.html')


@app.route('/register_user', methods=['POST'])
def register_user():
    email = request.form['email']
    password = request.form['password']

    conn = sqlite3.connect("dropout.db")
    c = conn.cursor()

    c.execute(
        "INSERT INTO users(email, password) VALUES(?, ?)",
        (email, password)
    )

    conn.commit()
    conn.close()

    return redirect('/')


@app.route('/login', methods=['POST'])
def login():

    email = request.form['username']
    password = request.form['password']

    conn = sqlite3.connect("dropout.db")
    c = conn.cursor()

    c.execute(
        "SELECT * FROM users WHERE email=? AND password=?",
        (email,password)
    )

    user = c.fetchone()

    conn.close()

    if user:
        session['user'] = email
        return redirect('/dashboard')

    return "Invalid Email or Password"

@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect("dropout.db")
    c = conn.cursor()

    c.execute("SELECT * FROM students")
    students = c.fetchall()

    conn.close()

    current_date = datetime.now().strftime("%d-%m-%Y")

    return render_template(
       "dashboard.html",
       students=students,
       current_date=current_date
)

@app.route('/add_student', methods=['POST'])
def add_student():
    name = request.form['name']
    age = request.form['age']
    department = request.form['department']
    cgpa = float(request.form['cgpa'])
    attendance = float(request.form['attendance'])

    conn = sqlite3.connect("dropout.db")
    c = conn.cursor()

    c.execute(
        "INSERT INTO students(name, age, department, cgpa, attendance) VALUES(?,?,?,?,?)",
        (name, age, department, cgpa, attendance)
    )

    conn.commit()
    conn.close()

    return redirect('/dashboard')


@app.route('/predict/<int:id>')
def predict(id):
    conn = sqlite3.connect("dropout.db")
    c = conn.cursor()

    c.execute("SELECT * FROM students WHERE id=?", (id,))
    student = c.fetchone()

    attendance = student[5]
    cgpa = student[4]

    if attendance < 75 or cgpa < 6:
        risk = "High Risk"
    elif attendance < 85 or cgpa < 7:
        risk = "Medium Risk"
    else:
        risk = "Low Risk"

    c.execute(
        "INSERT INTO predictions(student_id, risk_level, prediction_date) VALUES(?,?,?)",
        (id, risk, str(datetime.now()))
    )

    conn.commit()
    conn.close()

    return render_template("prediction.html", student=student, risk=risk)


@app.route('/counselling/<risk>')
def counselling(risk):
    if risk == "High Risk":
        advice = "Immediate counselling required. Weekly monitoring."
    elif risk == "Medium Risk":
        advice = "Monthly counselling and academic support."
    else:
        advice = "Continue regular progress tracking."

    return render_template(
        "counselling.html",
        risk=risk,
        advice=advice
    )


@app.route('/history')
def history():
    conn = sqlite3.connect("dropout.db")
    c = conn.cursor()

    c.execute("""
        SELECT students.name,
               predictions.risk_level,
               predictions.prediction_date
        FROM predictions
        JOIN students
        ON students.id = predictions.student_id
        ORDER BY predictions.id DESC
    """)

    records = c.fetchall()

    conn.close()

    return render_template("history.html", records=records)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@app.route('/admin')
def admin():
    conn = sqlite3.connect("dropout.db")
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM students")
    total_students = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM predictions WHERE risk_level='High Risk'")
    high_risk = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM predictions WHERE risk_level='Medium Risk'")
    medium_risk = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM predictions WHERE risk_level='Low Risk'")
    low_risk = c.fetchone()[0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_students=total_students,
        high_risk=high_risk,
        medium_risk=medium_risk,
        low_risk=low_risk
    )


if __name__ == '__main__':
    app.run(debug=True)