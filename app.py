from flask import Flask, render_template, request, redirect, flash, session, send_file
import mysql.connector
import pandas as pd
from fpdf import FPDF
import io
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'timetable_secret_key'
app.permanent_session_lifetime = timedelta(hours=24)

# ---------- DATABASE CONNECTION ----------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="sunnyspl8",
        database="timetable_db"
    )

# ---------- AUTO SESSION SETUP ----------
@app.before_request
def make_session_permanent():
    if 'remember' in session and session['remember']:
        session.permanent = True
    else:
        session.permanent = False

# ---------- LOGIN REQUIRED ----------
def login_required(route_function):
    def wrapper(*args, **kwargs):
        if 'logged_in' not in session:
            flash('⚠️ Please login first!', 'warning')
            return redirect('/login')
        return route_function(*args, **kwargs)
    wrapper.__name__ = route_function.__name__
    return wrapper

# ---------- LOGIN ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = 'remember' in request.form

        if username == 'admin' and password == '1234':
            session['logged_in'] = True
            session['remember'] = remember
            flash('✅ Login successful!', 'success')
            return redirect('/')
        else:
            flash('❌ Invalid credentials!', 'danger')
    return render_template('login.html')

# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    flash('👋 Logged out successfully!', 'info')
    return redirect('/login')

# ---------- DASHBOARD ----------
@app.route('/')
@login_required
def home():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT COUNT(*) AS total FROM faculty")
    total_faculty = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) AS total FROM course")
    total_courses = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) AS total FROM timetable")
    total_timetables = cur.fetchone()['total']

    conn.close()
    return render_template('index.html',
                           total_faculty=total_faculty,
                           total_courses=total_courses,
                           total_timetables=total_timetables)

# ---------- ADD FACULTY ----------
@app.route('/add_faculty', methods=['GET', 'POST'])
@login_required
def add_faculty():
    conn = get_db_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        dept = request.form['dept']
        cur.execute("INSERT INTO faculty (name, dept) VALUES (%s, %s)", (name, dept))
        conn.commit()
        flash('✅ Faculty added successfully!', 'success')
        return redirect('/add_faculty')
    conn.close()
    return render_template('add_faculty.html')

# ---------- ADD COURSE ----------
@app.route('/add_course', methods=['GET', 'POST'])
@login_required
def add_course():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    if request.method == 'POST':
        course_name = request.form['course_name']
        faculty_id = request.form['faculty_id']
        cur.execute("INSERT INTO course (course_name, faculty_id) VALUES (%s, %s)", (course_name, faculty_id))
        conn.commit()
        flash('✅ Course added successfully!', 'success')
        return redirect('/add_course')

    cur.execute("SELECT faculty_id, name FROM faculty")
    faculty_list = cur.fetchall()
    conn.close()
    return render_template('add_course.html', faculty_list=faculty_list)

# ---------- ADD TIMETABLE ----------
@app.route('/add_timetable', methods=['GET', 'POST'])
@login_required
def add_timetable():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    if request.method == 'POST':
        course_id = request.form['course_id']
        faculty_id = request.form['faculty_id']
        day = request.form['day']
        start_time = request.form['start_time']
        end_time = request.form['end_time']

        cur.execute("""
            INSERT INTO timetable (course_id, day, start_time, end_time)
            VALUES (%s, %s, %s, %s)
        """, (course_id, day, start_time, end_time))

        cur.execute("UPDATE course SET faculty_id = %s WHERE course_id = %s", (faculty_id, course_id))
        conn.commit()
        conn.close()
        flash('✅ Timetable entry added successfully!', 'success')
        return redirect('/add_timetable')

    cur.execute("SELECT course_id, course_name, faculty_id FROM course")
    course_list = cur.fetchall()
    cur.execute("SELECT faculty_id, name FROM faculty")
    faculty_list = cur.fetchall()
    conn.close()
    return render_template('add_timetable.html', course_list=course_list, faculty_list=faculty_list)

# ---------- EDIT TIMETABLE ----------
@app.route('/edit_timetable/<int:tt_id>', methods=['GET', 'POST'])
@login_required
def edit_timetable(tt_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    if request.method == 'POST':
        course_id = request.form['course_id']
        faculty_id = request.form['faculty_id']
        day = request.form['day']
        start_time = request.form['start_time']
        end_time = request.form['end_time']

        cur.execute("""
            UPDATE timetable 
            SET course_id = %s, day = %s, start_time = %s, end_time = %s
            WHERE tt_id = %s
        """, (course_id, day, start_time, end_time, tt_id))
        cur.execute("UPDATE course SET faculty_id = %s WHERE course_id = %s", (faculty_id, course_id))

        conn.commit()
        conn.close()
        flash("✏️ Timetable updated successfully!", "success")
        return redirect('/view_timetable')

    cur.execute("SELECT * FROM timetable WHERE tt_id = %s", (tt_id,))
    timetable = cur.fetchone()
    cur.execute("SELECT course_id, course_name, faculty_id FROM course")
    courses = cur.fetchall()
    cur.execute("SELECT faculty_id, name FROM faculty")
    faculties = cur.fetchall()
    conn.close()
    return render_template('edit_timetable.html', timetable=timetable, courses=courses, faculties=faculties)

# ---------- VIEW DATABASE ----------
@app.route('/view_database')
@login_required
def view_database():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM faculty")
    faculty_data = cur.fetchall()
    cur.execute("SELECT * FROM course")
    course_data = cur.fetchall()
    cur.execute("SELECT * FROM timetable")
    timetable_data = cur.fetchall()
    conn.close()
    return render_template('view_database.html',
                           faculty_data=faculty_data,
                           course_data=course_data,
                           timetable_data=timetable_data)


# ---------- SIMPLE REDIRECTS FOR DASHBOARD CARDS ----------
@app.route('/faculty_list')
@login_required
def faculty_list():
    # re-use view_database which contains the faculty section
    return redirect('/view_database')


@app.route('/course_list')
@login_required
def course_list():
    return redirect('/view_database')


@app.route('/timetable_list')
@login_required
def timetable_list():
    return redirect('/view_timetable')


# ---------- DELETE HANDLERS ----------
@app.route('/delete_faculty/<int:faculty_id>')
@login_required
def delete_faculty(faculty_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Optional: unset faculty_id from courses to avoid FK errors
        cur.execute("UPDATE course SET faculty_id = NULL WHERE faculty_id = %s", (faculty_id,))
        cur.execute("DELETE FROM faculty WHERE faculty_id = %s", (faculty_id,))
        conn.commit()
        flash('🗑️ Faculty deleted successfully', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'❌ Error deleting faculty: {e}', 'danger')
    finally:
        conn.close()
    return redirect('/view_database')


@app.route('/delete_course/<int:course_id>')
@login_required
def delete_course(course_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # remove related timetable entries first
        cur.execute("DELETE FROM timetable WHERE course_id = %s", (course_id,))
        cur.execute("DELETE FROM course WHERE course_id = %s", (course_id,))
        conn.commit()
        flash('🗑️ Course and related timetable entries deleted', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'❌ Error deleting course: {e}', 'danger')
    finally:
        conn.close()
    return redirect('/view_database')


@app.route('/delete_timetable/<int:tt_id>')
@login_required
def delete_timetable(tt_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM timetable WHERE tt_id = %s", (tt_id,))
        conn.commit()
        flash('🗑️ Timetable entry deleted', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'❌ Error deleting timetable entry: {e}', 'danger')
    finally:
        conn.close()
    return redirect('/view_database')

# ---------- VIEW TIMETABLE ----------
@app.route('/view_timetable')
@login_required
def view_timetable():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT timetable.tt_id, course.course_name, faculty.name, faculty.dept,
               timetable.day, timetable.start_time, timetable.end_time
        FROM timetable
        INNER JOIN course ON timetable.course_id = course.course_id
        INNER JOIN faculty ON course.faculty_id = faculty.faculty_id
        ORDER BY FIELD(timetable.day, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'),
                 timetable.start_time
    """)
    data = cur.fetchall()
    conn.close()
    return render_template('view_timetable.html', data=data)

# ---------- EXPORT TIMETABLE TO PDF ----------
@app.route('/export_timetable_pdf')
@login_required
def export_timetable_pdf():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT timetable.tt_id, course.course_name, faculty.name AS faculty_name, timetable.day, timetable.start_time, timetable.end_time
        FROM timetable
        JOIN course ON timetable.course_id = course.course_id
        JOIN faculty ON course.faculty_id = faculty.faculty_id
    """)
    data = cur.fetchall()
    conn.close()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Timetable Report", ln=True, align='C')
    pdf.ln(8)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(10, 10, "ID", 1)
    pdf.cell(45, 10, "Course", 1)
    pdf.cell(45, 10, "Faculty", 1)
    pdf.cell(25, 10, "Day", 1)
    pdf.cell(30, 10, "Start", 1)
    pdf.cell(30, 10, "End", 1)
    pdf.ln()

    pdf.set_font("Arial", '', 10)
    for row in data:
        pdf.cell(10, 8, str(row['tt_id']), 1)
        pdf.cell(45, 8, row['course_name'], 1)
        pdf.cell(45, 8, row['faculty_name'], 1)
        pdf.cell(25, 8, row['day'], 1)
        pdf.cell(30, 8, str(row['start_time']), 1)
        pdf.cell(30, 8, str(row['end_time']), 1)
        pdf.ln()

    output = io.BytesIO()
    pdf.output(output)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="Timetable_Report.pdf", mimetype="application/pdf")


# Backwards-compatible route used by some templates
@app.route('/export_pdf')
@login_required
def export_pdf_redirect():
    return redirect('/export_timetable_pdf')


# Export timetable to Excel
@app.route('/export_excel')
@login_required
def export_excel():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT timetable.tt_id, course.course_name AS Course, faculty.name AS Faculty, timetable.day AS Day,
               timetable.start_time AS Start, timetable.end_time AS End
        FROM timetable
        JOIN course ON timetable.course_id = course.course_id
        LEFT JOIN faculty ON course.faculty_id = faculty.faculty_id
    """)
    data = cur.fetchall()
    conn.close()

    # Convert to DataFrame
    df = pd.DataFrame(data)

    # Try writing Excel using available engines, fallback to CSV if none available
    last_error = None
    for engine in ('xlsxwriter', 'openpyxl', None):
        try:
            output = io.BytesIO()
            if engine:
                with pd.ExcelWriter(output, engine=engine) as writer:
                    df.to_excel(writer, index=False, sheet_name='Timetable')
            else:
                # Let pandas choose an engine (may still fail if no engine installed)
                df.to_excel(output, index=False, sheet_name='Timetable')
            output.seek(0)
            return send_file(output, as_attachment=True, download_name='Timetable.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        except Exception as e:
            last_error = e
            # try next engine

    # If Excel export failed, fallback to CSV
    try:
        output = io.BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return send_file(output, as_attachment=True, download_name='Timetable.csv', mimetype='text/csv')
    except Exception as e:
        # If even CSV fails, return a user-friendly message
        flash(f'❌ Export failed: {last_error or e}', 'danger')
        return redirect('/view_timetable')


# Export courses list to PDF
@app.route('/export_course_pdf')
@login_required
def export_course_pdf():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT course_id, course_name, faculty_id FROM course")
    data = cur.fetchall()
    conn.close()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Courses Report', ln=True, align='C')
    pdf.ln(6)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(20, 8, 'ID', 1)
    pdf.cell(100, 8, 'Course Name', 1)
    pdf.cell(40, 8, 'Faculty ID', 1)
    pdf.ln()
    pdf.set_font('Arial', '', 10)
    for row in data:
        pdf.cell(20, 8, str(row.get('course_id', '')), 1)
        pdf.cell(100, 8, str(row.get('course_name', '')), 1)
        pdf.cell(40, 8, str(row.get('faculty_id', '')), 1)
        pdf.ln()
    output = io.BytesIO()
    pdf.output(output)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name='Courses_Report.pdf', mimetype='application/pdf')


# Export faculty list to PDF
@app.route('/export_faculty_pdf')
@login_required
def export_faculty_pdf():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT faculty_id, name, dept FROM faculty")
    data = cur.fetchall()
    conn.close()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Faculty Report', ln=True, align='C')
    pdf.ln(6)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(25, 8, 'ID', 1)
    pdf.cell(80, 8, 'Name', 1)
    pdf.cell(60, 8, 'Department', 1)
    pdf.ln()
    pdf.set_font('Arial', '', 10)
    for row in data:
        pdf.cell(25, 8, str(row.get('faculty_id', '')), 1)
        pdf.cell(80, 8, str(row.get('name', '')), 1)
        pdf.cell(60, 8, str(row.get('dept', '')), 1)
        pdf.ln()
    output = io.BytesIO()
    pdf.output(output)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name='Faculty_Report.pdf', mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
