import sqlite3
from pathlib import Path

DATABASE = Path(__file__).parent / "GeoAttend.sqlite"


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def get_user_by_email(email):
    connection = get_connection()

    user = connection.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    ).fetchone()

    connection.close()
    return user


def get_classes_for_teacher(teacher_id):
    connection = get_connection()

    classes = connection.execute(
        "SELECT * FROM classes WHERE teacher_id = ?",
        (teacher_id,)
    ).fetchall()

    connection.close()
    return classes


def get_classes_for_student(student_id):
    connection = get_connection()

    classes = connection.execute("""
        SELECT classes.*
        FROM classes
        JOIN enrolments
            ON classes.class_id = enrolments.class_id
        WHERE enrolments.student_id = ?
    """, (student_id,)).fetchall()

    connection.close()
    return classes


def get_students_in_class(class_id):
    connection = get_connection()

    students = connection.execute("""
        SELECT users.*
        FROM users
        JOIN enrolments
            ON users.user_id = enrolments.student_id
        WHERE enrolments.class_id = ?
    """, (class_id,)).fetchall()

    connection.close()
    return students


def get_session_by_qr(qr_token):
    connection = get_connection()

    session = connection.execute(
        "SELECT * FROM attendance_sessions WHERE qr_token = ?",
        (qr_token,)
    ).fetchone()

    connection.close()
    return session


def create_attendance_session(
    class_id,
    created_by,
    qr_token,
    expected_latitude,
    expected_longitude,
    allowed_radius_m,
    start_time,
    late_after,
    end_time,
    status
):
    connection = get_connection()

    connection.execute("""
        INSERT INTO attendance_sessions (
            class_id,
            created_by,
            qr_token,
            expected_latitude,
            expected_longitude,
            allowed_radius_m,
            start_time,
            late_after,
            end_time,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        class_id,
        created_by,
        qr_token,
        expected_latitude,
        expected_longitude,
        allowed_radius_m,
        start_time,
        late_after,
        end_time,
        status
    ))

    connection.commit()
    connection.close()


def enrol_student(student_id, class_id):
    connection = get_connection()

    connection.execute("""
        INSERT INTO enrolments (
            student_id,
            class_id
        )
        VALUES (?, ?)
    """, (
        student_id,
        class_id
    ))

    connection.commit()
    connection.close()


def record_attendance(
    session_id,
    student_id,
    scanned_at,
    latitude,
    longitude,
    qr_valid,
    location_valid,
    status
):
    connection = get_connection()

    connection.execute("""
        INSERT INTO attendance_records (
            session_id,
            student_id,
            scanned_at,
            student_latitude,
            student_longitude,
            qr_valid,
            location_valid,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id,
        student_id,
        scanned_at,
        latitude,
        longitude,
        qr_valid,
        location_valid,
        status
    ))

    connection.commit()
    connection.close()


def get_attendance_for_session(session_id):
    connection = get_connection()

    records = connection.execute("""
        SELECT
            users.name,
            attendance_records.*
        FROM attendance_records
        JOIN users
            ON attendance_records.student_id = users.user_id
        WHERE attendance_records.session_id = ?
    """, (session_id,)).fetchall()

    connection.close()
    return records