from flask import Flask, render_template, request, redirect, session
import psycopg2
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from psycopg2 import IntegrityError

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

        if not db_url:
            print("DATABASE_URL not set")
            return None

        # Render PostgreSQL fix
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)

        conn = psycopg2.connect(db_url)
        return conn

    except Exception as e:
        print("DB Connection Error:", e)
        return None


# ---------------- INIT DATABASE ----------------
def init_db():
    conn = get_db_connection()

    if not conn:
        print("Database not available")
        return

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


def safe_init_db():
    try:
        init_db()
    except Exception as e:
        print("Database initialization skipped:", e)


# ---------------- HOME ----------------
@app.route('/')
def home():
    return render_template("login.html")


# ---------------- REGISTER ----------------
@app.route('/register_user', methods=['POST'])
def register_user():

    email = request.form['email'].strip()
    password = request.form['password']

    hashed_password = generate_password_hash(password)

    conn = get_db_connection()

    if not conn:
        return "DB not available"

    c = conn.cursor()

    try:
        c.execute(
            "INSERT INTO users(email,password) VALUES(%s,%s)",
            (email, hashed_password)
        )

        conn.commit()

    except IntegrityError:
        conn.rollback()
        conn.close()
        return "Email already registered."

    except Exception as e:
        conn.rollback()
        conn.close()
        return f"Registration Error: {e}"

    conn.close()

    return redirect('/')
@app.route('/register')
def register():
    return render_template('register.html')


# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == "GET":
        return render_template("login.html")

    email = request.form['email'].strip()
    password = request.form['password']

    conn = get_db_connection()

    if not conn:
        return "DB not available"

    c = conn.cursor()

    c.execute(
        "SELECT id,email,password FROM users WHERE email=%s",
        (email,)
    )

    user = c.fetchone()

    conn.close()

    if user is None:
        return "Invalid email or password"

    stored_password = user[2]

    if check_password_hash(stored_password, password):
        session['user'] = email
        return redirect('/dashboard')

    return "Invalid email or password"

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():

    if 'user' not in session:
        return redirect('/')

    conn = get_db_connection()

    if not conn:
        return "DB not available"

    c = conn.cursor()

    c.execute("SELECT * FROM students ORDER BY id DESC")
    students = c.fetchall()

    conn.close()

    current_date = datetime.now().strftime("%d-%m-%Y")

    return render_template(
        "dashboard.html",
        students=students,
        current_date=current_date
    )


# ---------------- ADD STUDENT ----------------
@app.route('/add_student', methods=['POST'])
def add_student():

    if 'user' not in session:
        return redirect('/')

    try:
        name = request.form['name']
        age = int(request.form['age'])
        department = request.form['department']
        cgpa = float(request.form['cgpa'])
        attendance = float(request.form['attendance'])

        conn = get_db_connection()

        if not conn:
            return "DB not available"

        c = conn.cursor()

        c.execute(
            """
            INSERT INTO students
            (name, age, department, cgpa, attendance)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (name, age, department, cgpa, attendance)
        )

        conn.commit()
        conn.close()

        return redirect('/dashboard')

    except Exception as e:
        return f"Error adding student: {e}"


# ---------------- PREDICT ----------------
@app.route('/predict/<int:id>')
def predict(id):

    if 'user' not in session:
        return redirect('/')

    conn = get_db_connection()

    if not conn:
        return "DB not available"

    c = conn.cursor()

    c.execute(
        "SELECT * FROM students WHERE id=%s",
        (id,)
    )

    student = c.fetchone()

    if student is None:
        conn.close()
        return "Student not found"

    attendance = float(student[5])
    cgpa = float(student[4])

    if attendance < 75 or cgpa < 6:
        risk = "High Risk"

    elif attendance < 85 or cgpa < 7:
        risk = "Medium Risk"

    else:
        risk = "Low Risk"

    c.execute(
        """
        INSERT INTO predictions
        (student_id, risk_level, prediction_date)
        VALUES (%s, %s, %s)
        """,
        (
            id,
            risk,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )

    conn.commit()
    conn.close()

    return render_template(
        "prediction.html",
        student=student,
        risk=risk
    )

# ---------------- COUNSELLING ----------------
@app.route('/counselling/<risk>')
def counselling(risk):

    if 'user' not in session:
        return redirect('/')

    if risk == "High Risk":
        advice = "Immediate counselling required. Weekly monitoring and parental guidance."

    elif risk == "Medium Risk":
        advice = "Monthly counselling and additional academic support."

    else:
        advice = "Continue regular progress monitoring and encourage consistency."

    return render_template(
        "counselling.html",
        risk=risk,
        advice=advice
    )


# ---------------- HISTORY ----------------
@app.route('/history')
def history():

    if 'user' not in session:
        return redirect('/')

    conn = get_db_connection()

    if not conn:
        return "DB not available"

    c = conn.cursor()

    c.execute("""
        SELECT
            students.name,
            predictions.risk_level,
            predictions.prediction_date
        FROM predictions
        JOIN students
            ON students.id = predictions.student_id
        ORDER BY predictions.id DESC
    """)

    records = c.fetchall()

    conn.close()

    return render_template(
        "history.html",
        records=records
    )


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')


# ---------------- ADMIN DASHBOARD ----------------
@app.route('/admin')
def admin():

    if 'user' not in session:
        return redirect('/')

    conn = get_db_connection()

    if not conn:
        return "DB not available"

    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM students")
    total_students = c.fetchone()[0]

    c.execute(
        "SELECT COUNT(*) FROM predictions WHERE risk_level=%s",
        ("High Risk",)
    )
    high_risk = c.fetchone()[0]

    c.execute(
        "SELECT COUNT(*) FROM predictions WHERE risk_level=%s",
        ("Medium Risk",)
    )
    medium_risk = c.fetchone()[0]

    c.execute(
        "SELECT COUNT(*) FROM predictions WHERE risk_level=%s",
        ("Low Risk",)
    )
    low_risk = c.fetchone()[0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_students=total_students,
        high_risk=high_risk,
        medium_risk=medium_risk,
        low_risk=low_risk
    )
# ---------------- INITIALIZE DATABASE ----------------
safe_init_db()

# ---------------- RUN APP ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


