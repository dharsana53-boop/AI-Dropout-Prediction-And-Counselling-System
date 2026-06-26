from flask import Flask, render_template, request, redirect, session
import psycopg2
import os
from datetime import datetime

app = Flask(
    __name__,
    template_folder="src/templates",
    static_folder="src/static"
 )
app.secret_key = "dropout_project_key"


# ---------------- DB CONNECTION ----------------
def get_db_connection():
    try:
        db_url = os.environ.get("DATABASE_URL")

        print("DATABASE_URL exists:", bool(db_url))

        if not db_url:
            raise Exception("DATABASE_URL not set in Render")

        return psycopg2.connect(db_url)

    except Exception as e:
        print(f"DB Connection Error: {repr(e)}")
        return None

# ---------------- INIT DB ----------------
def init_db():
     conn = get_db_connection()

     if not conn:
        return "DB not available"

     c = conn.cursor()

     c.execute("""
    CREATE TABLE IF NOT EXISTS students(
        id SERIAL PRIMARY KEY,
        name TEXT,
        age INTEGER,
        department TEXT,
        cgpa REAL,
        attendance REAL
    )
    """)

     c.execute("""
    CREATE TABLE IF NOT EXISTS predictions(
        id SERIAL PRIMARY KEY,
        student_id INTEGER,
        risk_level TEXT,
        prediction_date TEXT
    )
    """)

     c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

     conn.commit()
     conn.close()


# Run DB init once
def safe_init_db():
    try:
        init_db()
    except Exception as e:
        print("Database init skipped:", e)


# -------- REGISTER USER --------
@app.route('/register_user', methods=['POST'])
def register_user():
    email = request.form['email']
    password = request.form['password']

    conn = get_db_connection()

    if not conn:
        return "DB not available"

    c = conn.cursor()

    c.execute(
        "INSERT INTO users (email, password) VALUES (%s, %s)",
        (email, password)
    )

    conn.commit()
    conn.close()

    return redirect('/')
# ---------------- ROUTES ----------------

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    conn = get_db_connection()

    if not conn:
        return "DB not available"

    c = conn.cursor()

    c.execute(
        "SELECT * FROM users WHERE email=%s AND password=%s",
        (email, password)
    )

    user = c.fetchone()

    conn.close()

    if user:
        session['user'] = email
        return redirect('/dashboard')
    else:
        return "Invalid email or password"

# -------- DASHBOARD --------
@app.route('/dashboard')
def dashboard():
    conn = get_db_connection()

    if not conn:
       return "DB not available"
 
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


# -------- ADD STUDENT --------
@app.route('/add_student', methods=['POST'])
def add_student():
    name = request.form['name']
    age = request.form['age']
    department = request.form['department']
    cgpa = float(request.form['cgpa'])
    attendance = float(request.form['attendance'])

    conn = get_db_connection()

    if not conn:
        return "DB not available"

    c = conn.cursor() 

    c.execute(
        "INSERT INTO students(name, age, department, cgpa, attendance) VALUES(%s,%s,%s,%s,%s)",
        (name, age, department, cgpa, attendance)
    )

    conn.commit()
    conn.close()

    return redirect('/dashboard')


# -------- PREDICT --------
@app.route('/predict/<int:id>')
def predict(id):
    conn = get_db_connection()

    if not conn:
     return "DB not available"

    c = conn.cursor()

    c.execute("SELECT * FROM students WHERE id=%s", (id,))
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
        "INSERT INTO predictions(student_id, risk_level, prediction_date) VALUES(%s,%s,%s)",
        (id, risk, str(datetime.now()))
    )

    conn.commit()
    conn.close()

    return render_template("prediction.html", student=student, risk=risk)


# -------- COUNSELLING --------
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


# -------- HISTORY --------
@app.route('/history')
def history():
    conn = get_db_connection()

    if not conn:
       return "DB not available"

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


# -------- LOGOUT --------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# -------- ADMIN DASHBOARD --------
@app.route('/admin')
def admin():
    conn = get_db_connection()

    if not conn:
       return "DB not available"

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


# ---------------- RUN ----------------

# Initialize database tables
safe_init_db()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)