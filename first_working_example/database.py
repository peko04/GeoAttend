import sqlite3
from pathlib import Path
from contextlib import closing
from datetime import date, timedelta

DATABASE = Path(__file__).with_name('database.sqlite')


def connect():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    return db


def read(sql, values=()):
    with closing(connect()) as db:
        return db.execute(sql, values).fetchall()


def get_students():
    return read('''SELECT s.student_id, u.full_name FROM students s
                   JOIN users u USING(user_id) WHERE u.account_status = 'ACTIVE' ''')


def get_lecturers():
    return read('''SELECT l.lecturer_id, u.full_name FROM lecturers l
                   JOIN users u USING(user_id) WHERE u.account_status = 'ACTIVE' ''')


def student_subjects(student_id):
    return read('''SELECT cs.section_id AS subject_id, c.course_code AS code, c.course_name AS name
                   FROM enrolments e JOIN class_sections cs USING(section_id)
                   JOIN courses c USING(course_id)
                   WHERE e.student_id = ? AND e.enrolment_status = 'ACTIVE'
                     AND cs.section_status = 'ACTIVE' ''', (student_id,))


def teacher_subjects(teacher_id):
    return read('''SELECT cs.section_id AS subject_id, c.course_code AS code, c.course_name AS name
                   FROM class_sections cs JOIN courses c USING(course_id)
                   WHERE cs.lecturer_id = ? AND cs.section_status = 'ACTIVE' ''', (teacher_id,))


def class_students(subject_id):
    return read('''SELECT s.student_id, u.full_name FROM enrolments e
                   JOIN students s USING(student_id) JOIN users u USING(user_id)
                   WHERE e.section_id = ? AND e.enrolment_status = 'ACTIVE' ''', (subject_id,))


# Existing dates are weekly. The earliest session for each class is Week 1.
# Calculate weeks in Python; do not add a column to the database.
def first_week(subject_id):
    rows = read('SELECT MIN(session_date) AS first_date FROM attendance_sessions WHERE section_id = ?', (subject_id,))
    return date.fromisoformat(rows[0]['first_date']) if rows[0]['first_date'] else date.today()


def attendance_grid(subject_id):
    start = first_week(subject_id)
    rows = read('''SELECT a.student_id, a.final_status, s.session_date FROM attendance_records a
                   JOIN attendance_sessions s USING(session_id) WHERE s.section_id = ?''', (subject_id,))
    grid = {}
    for row in rows:
        week = (date.fromisoformat(row['session_date']) - start).days // 7 + 1
        grid[(row['student_id'], week)] = row['final_status'] or ''
    return grid


def start_session(subject_id, week, token):
    session_date = (first_week(subject_id) + timedelta(weeks=week - 1)).isoformat()
    with closing(connect()) as db, db:
        db.execute("UPDATE attendance_sessions SET session_status = 'CLOSED' WHERE section_id = ?", (subject_id,))
        existing = db.execute('SELECT session_id FROM attendance_sessions WHERE section_id = ? AND session_date = ?',
                              (subject_id, session_date)).fetchone()
        if existing:
            session_id = existing['session_id']
            db.execute("UPDATE attendance_sessions SET session_status = 'ACTIVE', ended_at = NULL WHERE session_id = ?", (session_id,))
        else:
            # The original schema requires these timing fields. No timing rules in this MVP.
            cursor = db.execute('''INSERT INTO attendance_sessions
                (section_id, created_by_lecturer_id, session_date, opened_at,
                 on_time_cutoff, late_cutoff, clock_out_opens_at, clock_out_closes_at)
                SELECT section_id, lecturer_id, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                       CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                FROM class_sections WHERE section_id = ?''', (session_date, subject_id))
            session_id = cursor.lastrowid
        db.execute("UPDATE qr_tokens SET token_status = 'REVOKED' WHERE session_id = ?", (session_id,))
        db.execute('''INSERT INTO qr_tokens(session_id, token_value, expires_at)
                      VALUES (?, ?, '9999-12-31 23:59:59')''', (session_id, token))


def check_in(student_id, token):
    with closing(connect()) as db, db:
        db.execute('BEGIN IMMEDIATE')
        session = db.execute('''SELECT s.session_id, s.section_id FROM qr_tokens q
            JOIN attendance_sessions s USING(session_id)
            WHERE q.token_value = ? AND q.token_status = 'ACTIVE'
              AND q.token_type = 'CLOCK_IN' AND s.session_status = 'ACTIVE' ''', (token,)).fetchone()
        if session is None:
            return False, 'Invalid QR code.'
        enrolled = db.execute("SELECT enrolment_id FROM enrolments WHERE student_id = ? AND section_id = ? AND enrolment_status = 'ACTIVE'",
                              (student_id, session['section_id'])).fetchone()
        if enrolled is None:
            return False, 'You are not enrolled in this subject.'
        existing = db.execute('SELECT attendance_id FROM attendance_records WHERE session_id = ? AND student_id = ?',
                              (session['session_id'], student_id)).fetchone()
        if existing:
            return False, 'Attendance already recorded.'
        db.execute('''INSERT INTO attendance_records(session_id, student_id, clock_in_time,
                      system_status, final_status, completion_status)
                      VALUES (?, ?, CURRENT_TIMESTAMP, 'PRESENT', 'PRESENT', 'COMPLETE')''',
                   (session['session_id'], student_id))
        return True, 'Attendance saved: PRESENT.'
