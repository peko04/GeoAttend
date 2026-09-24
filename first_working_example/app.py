from flask import Flask, render_template, request, redirect, url_for, jsonify
import secrets
import database as db

app = Flask(__name__)


@app.route('/')
def select_user_page():
    return render_template(
        'login.html',
        students=db.get_students(),
        lecturers=db.get_lecturers()
    )


# ==================== STUDENT ====================

@app.route('/select-student', methods=['POST'])
def select_student():
    student_id = request.form.get('student_id', type=int)

    if student_id is None:
        return 'Please select a student.', 400

    return redirect(url_for('student_login_page', student_id=student_id))


@app.route('/student-login')
def student_login_page():
    student_id = request.args.get('student_id', type=int)

    if student_id is None:
        return redirect(url_for('select_user_page'))

    return render_template('student-login.html', student_id=student_id)


@app.route('/student-login-submit', methods=['POST'])
def student_login_submit():
    student_id = request.form.get('student_id', type=int)
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')

    if student_id is None or not email or not password:
        return 'Please enter your email and password.', 400

    # Temporary page-flow test. Real account checking is not connected.
    return redirect(url_for('student_page', student_id=student_id))


@app.route('/student/<int:student_id>')
def student_page(student_id):
    subjects = db.student_subjects(student_id)

    grids = {}
    for subject in subjects:
        subject_id = subject['subject_id']
        grids[subject_id] = db.attendance_grid(subject_id)

    return render_template(
        'student.html',
        student_id=student_id,
        subjects=subjects,
        grids=grids
    )


@app.route('/student/<int:student_id>/scan', methods=['POST'])
def scan(student_id):
    data = request.get_json(silent=True)
    token = data.get('token') if isinstance(data, dict) else None

    if not isinstance(token, str) or not token:
        return jsonify(success=False, message='Missing QR code.'), 400

    success, message = db.check_in(student_id, token)
    return jsonify(success=success, message=message)


# ==================== TEACHER ====================

@app.route('/select-teacher', methods=['POST'])
def select_teacher():
    teacher_id = request.form.get('lecturer_id', type=int)

    if teacher_id is None:
        return 'Please select a teacher.', 400

    return redirect(url_for('teacher_login_page', teacher_id=teacher_id))


@app.route('/teacher-login')
def teacher_login_page():
    teacher_id = request.args.get('teacher_id', type=int)

    if teacher_id is None:
        return redirect(url_for('select_user_page'))

    return render_template('teacher-login.html', teacher_id=teacher_id)


@app.route('/teacher-login-submit', methods=['POST'])
def teacher_login_submit():
    teacher_id = request.form.get('teacher_id', type=int)
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')

    if teacher_id is None or not email or not password:
        return 'Please enter your email and password.', 400

    # Temporary page-flow test. Real account checking is not connected.
    return redirect(url_for('teacher_page', teacher_id=teacher_id))


@app.route('/teacher/<int:teacher_id>', methods=['GET', 'POST'])
def teacher_page(teacher_id):
    subjects = db.teacher_subjects(teacher_id)

    token = None
    selected_subject = request.form.get('subject_id', type=int)
    selected_week = request.form.get('week', default=1, type=int)
    session_subject = None

    if request.method == 'POST':
        subject_id = request.form.get('subject_id', type=int)
        week = request.form.get('week', type=int)

        if (
            subject_id not in [subject['subject_id'] for subject in subjects]
            or week not in range(1, 14)
        ):
            return 'Invalid subject or week', 400

        token = secrets.token_urlsafe(16)
        db.start_session(subject_id, week, token)

        session_subject = next(
            subject for subject in subjects
            if subject['subject_id'] == subject_id
        )

    grids = {}
    students = {}

    for subject in subjects:
        subject_id = subject['subject_id']
        grids[subject_id] = db.attendance_grid(subject_id)
        students[subject_id] = db.class_students(subject_id)

    return render_template(
        'teacher.html',
        subjects=subjects,
        grids=grids,
        students=students,
        token=token,
        selected_subject=selected_subject,
        selected_week=selected_week,
        session_subject=session_subject
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5007, debug=False)