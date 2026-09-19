from flask import Flask, render_template, request, redirect, url_for, jsonify
import secrets
import database as db

app = Flask(__name__)


@app.route('/')
def select_user_page():
    return render_template('login.html', students=db.get_students(), lecturers=db.get_lecturers())


@app.route('/select-student', methods=['POST'])
def select_student():
    return redirect(url_for('student_page', student_id=request.form['student_id']))


@app.route('/select-teacher', methods=['POST'])
def select_teacher():
    return redirect(url_for('teacher_page', teacher_id=request.form['lecturer_id']))


@app.route('/student/<int:student_id>')
def student_page(student_id):
    subjects = db.student_subjects(student_id)
    grids = {}
    for subject in subjects:
        grids[subject['subject_id']] = db.attendance_grid(subject['subject_id'])
    return render_template('student.html', student_id=student_id, subjects=subjects, grids=grids)


@app.route('/teacher/<int:teacher_id>', methods=['GET', 'POST'])
def teacher_page(teacher_id):
    subjects = db.teacher_subjects(teacher_id)
    token = None
    if request.method == 'POST':
        subject_id = request.form.get('subject_id', type=int)
        week = request.form.get('week', type=int)
        if subject_id not in [s['subject_id'] for s in subjects] or week not in range(1, 14):
            return 'Invalid subject or week', 400
        token = secrets.token_urlsafe(16)
        db.start_session(subject_id, week, token)
    grids = {}
    students = {}
    for subject in subjects:
        subject_id = subject['subject_id']
        grids[subject_id] = db.attendance_grid(subject_id)
        students[subject_id] = db.class_students(subject_id)
    return render_template('teacher.html', subjects=subjects, grids=grids, students=students, token=token)


@app.route('/student/<int:student_id>/scan', methods=['POST'])
def scan(student_id):
    data = request.get_json(silent=True)
    token = data.get('token') if isinstance(data, dict) else None
    if not isinstance(token, str) or not token:
        return jsonify(success=False, message='Missing QR code.'), 400
    success, message = db.check_in(student_id, token)
    return jsonify(success=success, message=message)


if __name__ == '__main__':
    app.run(debug=True, port=5007)
