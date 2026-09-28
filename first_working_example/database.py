import sqlite3
from pathlib import Path
from contextlib import closing
from datetime import date, timedelta


# =========================================================
# DATABASE CONNECTION
# =========================================================

DATABASE = Path(__file__).with_name('database.sqlite')


def connect():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    return db


def read(sql, values=()):
    with closing(connect()) as db:
        return db.execute(sql, values).fetchall()


# =========================================================
# USERS
# =========================================================

def get_students():
    return read(
        '''
        SELECT s.student_id, u.full_name
        FROM students s
        JOIN users u USING(user_id)
        WHERE u.account_status = 'ACTIVE'
        '''
    )


def get_lecturers():
    return read(
        '''
        SELECT l.lecturer_id, u.full_name
        FROM lecturers l
        JOIN users u USING(user_id)
        WHERE u.account_status = 'ACTIVE'
        '''
    )


# =========================================================
# STUDENT SUBJECTS
# =========================================================

def student_subjects(student_id):
    return read(
        '''
        SELECT
            cs.section_id AS subject_id,
            c.course_code AS code,
            c.course_name AS name

        FROM enrolments e

        JOIN class_sections cs USING(section_id)
        JOIN courses c USING(course_id)

        WHERE e.student_id = ?
          AND e.enrolment_status = 'ACTIVE'
          AND cs.section_status = 'ACTIVE'
        ''',
        (student_id,)
    )


# =========================================================
# TEACHER SUBJECTS
# =========================================================

def teacher_subjects(teacher_id):
    return read(
        '''
        SELECT
            cs.section_id AS subject_id,
            c.course_code AS code,
            c.course_name AS name

        FROM class_sections cs

        JOIN courses c USING(course_id)

        WHERE cs.lecturer_id = ?
          AND cs.section_status = 'ACTIVE'
        ''',
        (teacher_id,)
    )


# =========================================================
# STUDENTS IN A CLASS
# =========================================================

def class_students(subject_id):
    return read(
        '''
        SELECT
            s.student_id,
            u.full_name

        FROM enrolments e

        JOIN students s USING(student_id)
        JOIN users u USING(user_id)

        WHERE e.section_id = ?
          AND e.enrolment_status = 'ACTIVE'
        ''',
        (subject_id,)
    )


# =========================================================
# ATTENDANCE WEEK CALCULATION
# =========================================================

# Existing dates are weekly.
# The earliest attendance session for each class is Week 1.
#
# Weeks are calculated in Python instead of adding another
# column to the database.

def first_week(subject_id):

    rows = read(
        '''
        SELECT MIN(session_date) AS first_date
        FROM attendance_sessions
        WHERE section_id = ?
        ''',
        (subject_id,)
    )

    if rows[0]['first_date']:
        return date.fromisoformat(
            rows[0]['first_date']
        )

    return date.today()


# =========================================================
# ATTENDANCE GRID
# =========================================================

def attendance_grid(subject_id):

    start = first_week(subject_id)

    rows = read(
        '''
        SELECT
            a.student_id,
            a.final_status,
            s.session_date

        FROM attendance_records a

        JOIN attendance_sessions s USING(session_id)

        WHERE s.section_id = ?
        ''',
        (subject_id,)
    )

    grid = {}

    for row in rows:

        session_date = date.fromisoformat(
            row['session_date']
        )

        week = (
            (session_date - start).days // 7
        ) + 1

        grid[
            (
                row['student_id'],
                week
            )
        ] = row['final_status'] or ''

    return grid


# =========================================================
# START QR ATTENDANCE SESSION
# =========================================================

def start_session(subject_id, week, token):

    session_date = (
        first_week(subject_id)
        + timedelta(weeks=week - 1)
    ).isoformat()

    with closing(connect()) as db, db:

        # Close previous sessions for this subject

        db.execute(
            '''
            UPDATE attendance_sessions
            SET session_status = 'CLOSED'
            WHERE section_id = ?
            ''',
            (subject_id,)
        )


        # Check if a session already exists for this week

        existing = db.execute(
            '''
            SELECT session_id
            FROM attendance_sessions
            WHERE section_id = ?
              AND session_date = ?
            ''',
            (
                subject_id,
                session_date
            )
        ).fetchone()


        # -------------------------------------------------
        # SESSION ALREADY EXISTS
        # -------------------------------------------------

        if existing:

            session_id = existing['session_id']

            db.execute(
                '''
                UPDATE attendance_sessions
                SET session_status = 'ACTIVE',
                    ended_at = NULL
                WHERE session_id = ?
                ''',
                (session_id,)
            )


        # -------------------------------------------------
        # CREATE NEW SESSION
        # -------------------------------------------------

        else:

            # The original database schema requires
            # these timing fields.
            #
            # There are currently no timing rules in
            # this MVP.

            cursor = db.execute(
                '''
                INSERT INTO attendance_sessions
                (
                    section_id,
                    created_by_lecturer_id,
                    session_date,
                    opened_at,
                    on_time_cutoff,
                    late_cutoff,
                    clock_out_opens_at,
                    clock_out_closes_at
                )

                SELECT
                    section_id,
                    lecturer_id,
                    ?,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP

                FROM class_sections

                WHERE section_id = ?
                ''',
                (
                    session_date,
                    subject_id
                )
            )

            session_id = cursor.lastrowid


        # -------------------------------------------------
        # REVOKE OLD QR CODES
        # -------------------------------------------------

        db.execute(
            '''
            UPDATE qr_tokens
            SET token_status = 'REVOKED'
            WHERE session_id = ?
            ''',
            (session_id,)
        )


        # -------------------------------------------------
        # CREATE NEW QR TOKEN
        # -------------------------------------------------

        db.execute(
            '''
            INSERT INTO qr_tokens
            (
                session_id,
                token_value,
                expires_at
            )

            VALUES (
                ?,
                ?,
                '9999-12-31 23:59:59'
            )
            ''',
            (
                session_id,
                token
            )
        )


# =========================================================
# STUDENT QR CHECK-IN
# =========================================================

def check_in(student_id, token):

    with closing(connect()) as db, db:

        db.execute('BEGIN IMMEDIATE')


        # -------------------------------------------------
        # FIND ACTIVE QR SESSION
        # -------------------------------------------------

        session = db.execute(
            '''
            SELECT
                s.session_id,
                s.section_id

            FROM qr_tokens q

            JOIN attendance_sessions s USING(session_id)

            WHERE q.token_value = ?
              AND q.token_status = 'ACTIVE'
              AND q.token_type = 'CLOCK_IN'
              AND s.session_status = 'ACTIVE'
            ''',
            (token,)
        ).fetchone()


        if session is None:

            return (
                False,
                'Invalid QR code.'
            )


        # -------------------------------------------------
        # CHECK STUDENT ENROLMENT
        # -------------------------------------------------

        enrolled = db.execute(
            '''
            SELECT enrolment_id

            FROM enrolments

            WHERE student_id = ?
              AND section_id = ?
              AND enrolment_status = 'ACTIVE'
            ''',
            (
                student_id,
                session['section_id']
            )
        ).fetchone()


        if enrolled is None:

            return (
                False,
                'You are not enrolled in this subject.'
            )


        # -------------------------------------------------
        # CHECK EXISTING ATTENDANCE
        # -------------------------------------------------

        existing = db.execute(
            '''
            SELECT attendance_id

            FROM attendance_records

            WHERE session_id = ?
              AND student_id = ?
            ''',
            (
                session['session_id'],
                student_id
            )
        ).fetchone()


        if existing:

            return (
                False,
                'Attendance already recorded.'
            )


        # -------------------------------------------------
        # RECORD PRESENT ATTENDANCE
        # -------------------------------------------------

        db.execute(
            '''
            INSERT INTO attendance_records
            (
                session_id,
                student_id,
                clock_in_time,
                system_status,
                final_status,
                completion_status
            )

            VALUES
            (
                ?,
                ?,
                CURRENT_TIMESTAMP,
                'PRESENT',
                'PRESENT',
                'COMPLETE'
            )
            ''',
            (
                session['session_id'],
                student_id
            )
        )


        return (
            True,
            'Attendance saved: PRESENT.'
        )


# =========================================================
# MANUAL ATTENDANCE UPDATE
# =========================================================

def update_attendance(
    student_id,
    subject_id,
    week,
    status
):

    # -----------------------------------------------------
    # WORK OUT WHICH SESSION/WEEK IS BEING EDITED
    # -----------------------------------------------------

    session_date = (
        first_week(subject_id)
        + timedelta(weeks=week - 1)
    ).isoformat()


    with closing(connect()) as db, db:


        # -------------------------------------------------
        # FIND ATTENDANCE SESSION
        # -------------------------------------------------

        session = db.execute(
            '''
            SELECT session_id

            FROM attendance_sessions

            WHERE section_id = ?
              AND session_date = ?
            ''',
            (
                subject_id,
                session_date
            )
        ).fetchone()


        # There must already be an attendance session
        # for this week.

        if session is None:
            return False


        session_id = session['session_id']


        # -------------------------------------------------
        # CHECK WHETHER STUDENT ALREADY HAS A RECORD
        # -------------------------------------------------

        existing = db.execute(
            '''
            SELECT attendance_id

            FROM attendance_records

            WHERE session_id = ?
              AND student_id = ?
            ''',
            (
                session_id,
                student_id
            )
        ).fetchone()


        # -------------------------------------------------
        # TEACHER SELECTED "—"
        # -------------------------------------------------

        if status == '':

            # Remove the attendance record if one exists.

            if existing:

                db.execute(
                    '''
                    DELETE FROM attendance_records

                    WHERE attendance_id = ?
                    ''',
                    (
                        existing['attendance_id'],
                    )
                )

            return True


        # -------------------------------------------------
        # UPDATE EXISTING ATTENDANCE
        # -------------------------------------------------

        if existing:

            db.execute(
                '''
                UPDATE attendance_records

                SET final_status = ?,
                    completion_status = 'COMPLETE'

                WHERE attendance_id = ?
                ''',
                (
                    status,
                    existing['attendance_id']
                )
            )


        # -------------------------------------------------
        # CREATE MANUAL ATTENDANCE RECORD
        # -------------------------------------------------

        else:

            db.execute(
                '''
                INSERT INTO attendance_records
                (
                    session_id,
                    student_id,
                    system_status,
                    final_status,
                    completion_status
                )

                VALUES
                (
                    ?,
                    ?,
                    ?,
                    ?,
                    'COMPLETE'
                )
                ''',
                (
                    session_id,
                    student_id,
                    status,
                    status
                )
            )


        return True
