
import os
import re
import secrets
from urllib.parse import urlparse

from flask import (
    Flask, jsonify, redirect, render_template,
    render_template_string, request, session, url_for
)

import database as db
from admin import register_admin, verify_password


app = Flask(__name__)

app.secret_key = (
    os.environ.get('FLASK_SECRET_KEY')
    or secrets.token_hex(32)
)

app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = (
    os.environ.get('FLASK_SECURE_COOKIES') == '1'
)

register_admin(app)


# QR TOKEN

def extract_token(value):
    if not isinstance(value, str):
        return None

    value = value.strip()

    if value.startswith(('https://', 'http://')):
        value = urlparse(value).path

        if not value.startswith('/attendance/'):
            return None

        value = value[len('/attendance/'):].strip('/')

    if not re.fullmatch(r'[A-Za-z0-9_-]{10,128}', value):
        return None

    return value


def student_logged_in(student_id=None):
    if session.get('role') != 'STUDENT':
        return False

    return (
        student_id is None
        or session.get('student_id') == student_id
    )


def lecturer_logged_in(teacher_id=None):
    if session.get('role') != 'LECTURER':
        return False

    return (
        teacher_id is None
        or session.get('lecturer_id') == teacher_id
    )


# LOGIN

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            error = 'Please enter your email and password.'

        else:
            user = db.get_user_by_email(email)

            if user is None:
                error = 'Invalid email or password.'

            elif not verify_password(
                user['password_hash'], password
            ):
                error = 'Invalid email or password.'

            elif user['account_status'] != 'ACTIVE':
                error = 'This account is not active.'

            elif (
                user['role'] == 'STUDENT'
                and user['student_id'] is not None
            ):
                pending = session.get('pending_attendance')

                session.clear()
                session['user_id'] = user['user_id']
                session['role'] = 'STUDENT'
                session['student_id'] = user['student_id']

                if pending:
                    return redirect(
                        url_for('attendance_page', token=pending)
                    )

                return redirect(
                    url_for(
                        'student_page',
                        student_id=user['student_id']
                    )
                )

            elif (
                user['role'] == 'LECTURER'
                and user['lecturer_id'] is not None
            ):
                session.clear()
                session['user_id'] = user['user_id']
                session['role'] = 'LECTURER'
                session['lecturer_id'] = user['lecturer_id']

                return redirect(
                    url_for(
                        'teacher_page',
                        teacher_id=user['lecturer_id']
                    )
                )

            else:
                error = 'This account is not configured correctly.'

    return render_template('login.html', error=error)


# LOGOUT

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# STUDENT DASHBOARD

@app.route('/student/<int:student_id>')
def student_page(student_id):
    if not student_logged_in(student_id):
        return redirect(url_for('login'))

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


# QR CHECK-IN

@app.route(
    '/student/<int:student_id>/scan',
    methods=['POST']
)
def scan(student_id):
    if not student_logged_in(student_id):
        return jsonify(
            success=False,
            message='Please log in as this student.'
        ), 403

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(
            success=False,
            message='Invalid request.'
        ), 400

    token = extract_token(data.get('token'))

    if token is None:
        return jsonify(
            success=False,
            message='Invalid QR code.'
        ), 400

    try:
        latitude = float(data.get('latitude'))
        longitude = float(data.get('longitude'))

    except (TypeError, ValueError):
        return jsonify(
            success=False,
            message='Could not get your location.'
        ), 400

    if not (
        -90 <= latitude <= 90
        and -180 <= longitude <= 180
    ):
        return jsonify(
            success=False,
            message='Invalid location.'
        ), 400

    success, message = db.check_in(
        student_id,
        token,
        latitude,
        longitude
    )

    return jsonify(
        success=success,
        message=message
    )


# QR LINK PAGE

ATTENDANCE_HTML = '''
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport"
          content="width=device-width, initial-scale=1">

    <title>Record Attendance | GeoAttend</title>

    <link rel="stylesheet"
          href="{{ url_for('static', filename='CSS/style.css') }}">
</head>

<body class="login-body">

    <main class="login-wrapper">

        <header class="login-brand">
            <h1>GeoAttend</h1>
            <p>QR Attendance</p>
        </header>

        <section class="login-card"
                 style="display:block;max-width:600px;margin:auto;padding:32px;">

            <h2>Confirm your attendance</h2>

            <p>
                Tap the button below and allow
                location access to record attendance.
            </p>

            <button class="login-button"
                    id="checkin"
                    type="button">
                Confirm attendance
            </button>

            <p id="status"
               role="status"
               aria-live="polite"></p>

            <p>
                <a href="{{ url_for('student_page', student_id=student_id) }}">
                    Back to student dashboard
                </a>
            </p>

        </section>

    </main>

    <script>
        document.getElementById('checkin')
            .addEventListener('click', function () {

            const button = this;
            const status = document.getElementById('status');

            button.disabled = true;
            status.textContent = 'Checking location...';

            if (!navigator.geolocation) {
                status.textContent =
                    'Your browser does not support location.';

                button.disabled = false;
                return;
            }

            navigator.geolocation.getCurrentPosition(

                async function (position) {

                    try {
                        const response = await fetch(
                            {{ url_for('scan', student_id=student_id)|tojson }},
                            {
                                method: 'POST',

                                headers: {
                                    'Content-Type': 'application/json'
                                },

                                body: JSON.stringify({
                                    token: {{ token|tojson }},
                                    latitude: position.coords.latitude,
                                    longitude: position.coords.longitude
                                })
                            }
                        );

                        const data = await response.json();

                        status.textContent =
                            data.message || 'Attendance request failed.';

                        if (!data.success) {
                            button.disabled = false;
                        }

                    } catch (error) {

                        status.textContent =
                            'Could not contact GeoAttend. Try again.';

                        button.disabled = false;
                    }
                },

                function (error) {

                    status.textContent =
                        'Location unavailable. Allow location permission and try again.';

                    button.disabled = false;
                },

                {
                    enableHighAccuracy: true,
                    timeout: 15000,
                    maximumAge: 0
                }
            );
        });
    </script>

</body>
</html>
'''


@app.route('/attendance/<token>')
def attendance_page(token):
    token = extract_token(token)

    if token is None:
        return 'Invalid QR code.', 404

    if not student_logged_in():
        session['pending_attendance'] = token
        return redirect(url_for('login'))

    return render_template_string(
        ATTENDANCE_HTML,
        token=token,
        student_id=session['student_id']
    )


# LECTURER DASHBOARD

@app.route(
    '/teacher/<int:teacher_id>',
    methods=['GET', 'POST']
)
def teacher_page(teacher_id):
    if not lecturer_logged_in(teacher_id):
        return redirect(url_for('login'))

    subjects = db.teacher_subjects(teacher_id)

    token = None
    attendance_url = None
    session_subject = None

    selected_subject = request.form.get(
        'subject_id',
        type=int
    )

    selected_week = request.form.get(
        'week',
        default=1,
        type=int
    )

    if request.method == 'POST':

        subject_id = request.form.get(
            'subject_id',
            type=int
        )

        week = request.form.get(
            'week',
            type=int
        )

        valid_subject_ids = [
            subject['subject_id']
            for subject in subjects
        ]

        if (
            subject_id not in valid_subject_ids
            or week not in range(1, 14)
        ):
            return 'Invalid subject or week.', 400

        try:
            latitude = float(
                request.form.get('latitude')
            )

            longitude = float(
                request.form.get('longitude')
            )

        except (TypeError, ValueError):
            return (
                'Location is required to start attendance.',
                400
            )

        if not (
            -90 <= latitude <= 90
            and -180 <= longitude <= 180
        ):
            return 'Invalid teacher location.', 400

        token = secrets.token_urlsafe(16)

        db.start_session(
            subject_id,
            week,
            token,
            latitude,
            longitude
        )

        public_url = os.environ.get(
            'GEOATTEND_PUBLIC_URL',
            'https://geoattend.site'
        ).rstrip('/')

        attendance_url = (
            public_url
            + url_for('attendance_page', token=token)
        )

        session_subject = next(
            subject
            for subject in subjects
            if subject['subject_id'] == subject_id
        )

    grids = {}
    students = {}

    for subject in subjects:

        subject_id = subject['subject_id']

        grids[subject_id] = db.attendance_grid(
            subject_id
        )

        students[subject_id] = db.class_students(
            subject_id
        )

    return render_template(
        'teacher.html',
        subjects=subjects,
        grids=grids,
        students=students,
        token=token,
        attendance_url=attendance_url,
        selected_subject=selected_subject,
        selected_week=selected_week,
        session_subject=session_subject
    )


# MANUAL ATTENDANCE

@app.route(
    '/attendance/update',
    methods=['POST']
)
def update_attendance():

    if not lecturer_logged_in():
        return jsonify(
            success=False,
            message='Lecturer login required.'
        ), 403

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(
            success=False,
            message='Invalid request.'
        ), 400

    try:
        student_id = int(data.get('student_id'))
        subject_id = int(data.get('subject_id'))
        week = int(data.get('week'))

    except (TypeError, ValueError):
        return jsonify(
            success=False,
            message='Invalid student, subject or week.'
        ), 400

    status = data.get('status', '')

    if week not in range(1, 14):
        return jsonify(
            success=False,
            message='Invalid week.'
        ), 400

    allowed_statuses = (
        '',
        'PRESENT',
        'ABSENT',
        'LATE'
    )

    if status not in allowed_statuses:
        return jsonify(
            success=False,
            message='Invalid attendance status.'
        ), 400

    lecturer_subjects = db.teacher_subjects(
        session['lecturer_id']
    )

    valid_subject_ids = [
        subject['subject_id']
        for subject in lecturer_subjects
    ]

    if subject_id not in valid_subject_ids:
        return jsonify(
            success=False,
            message='You do not teach this class.'
        ), 403

    success = db.update_attendance(
        student_id,
        subject_id,
        week,
        status
    )

    if not success:
        return jsonify(
            success=False,
            message='No attendance session exists for this week.'
        ), 400

    return jsonify(
        success=True,
        message='Attendance updated.'
    )


# RUN APPLICATION

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5007,
        debug=False
    )
