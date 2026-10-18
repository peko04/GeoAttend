"""Small admin dashboard for GeoAttend's existing SQLite schema."""

import hmac
import re
import secrets
import sqlite3
from contextlib import closing
from functools import wraps

from flask import (Blueprint, abort, flash, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import database as db

admin_bp = Blueprint('geo_admin', __name__, url_prefix='/admin')
EMAIL_PATTERN = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
DAYS = ('MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY')


def connect():
    conn = sqlite3.connect(db.DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def setup_admin_table():
    with closing(connect()) as conn, conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS admin_accounts (
                admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                account_status TEXT NOT NULL DEFAULT 'ACTIVE'
                    CHECK (account_status IN ('ACTIVE', 'INACTIVE')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        ''')


def verify_password(stored, entered):
    """Support new hashed users and legacy demo accounts without breaking them."""
    if not isinstance(stored, str) or not isinstance(entered, str):
        return False
    if stored.startswith(('scrypt:', 'pbkdf2:')):
        try:
            return check_password_hash(stored, entered)
        except ValueError:
            return False
    return hmac.compare_digest(stored, entered)


def _email(text):
    return bool(EMAIL_PATTERN.fullmatch(text)) and len(text) <= 254


def _flash_error(exc):
    if isinstance(exc, sqlite3.IntegrityError):
        flash('Database rejected that change. Check for duplicate emails, numbers, or invalid selections.', 'error')
    else:
        flash(str(exc), 'error')


def _read(sql, args=()):
    with closing(connect()) as conn:
        return conn.execute(sql, args).fetchall()


def _csrf():
    if 'admin_csrf' not in session:
        session['admin_csrf'] = secrets.token_urlsafe(32)
    return session['admin_csrf']


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        admin_id = session.get('admin_id')
        if session.get('role') != 'ADMIN' or not isinstance(admin_id, int):
            return redirect(url_for('login'))
        active = _read('''SELECT admin_id FROM admin_accounts
                          WHERE admin_id = ? AND account_status = 'ACTIVE' ''', (admin_id,))
        if not active:
            session.clear()
            return redirect(url_for('login'))
        if request.method == 'POST':
            supplied = request.form.get('csrf_token', '')
            if not hmac.compare_digest(supplied, session.get('admin_csrf', '')):
                abort(400, 'Invalid form token. Reload the admin page and try again.')
        return view(*args, **kwargs)
    return wrapped


def register_admin(app):
    """Register routes and intercept admin logins on the existing / form."""
    setup_admin_table()
    app.register_blueprint(admin_bp)

    @app.before_request
    def admin_login_from_main_page():
        if request.endpoint != 'login' or request.method != 'POST':
            return None
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        matches = _read('SELECT * FROM admin_accounts WHERE email = ? LIMIT 1', (email,))
        if not matches:
            return None   # Regular students/lecturers continue to normal Flask login.
        account = matches[0]
        if account['account_status'] != 'ACTIVE' or not verify_password(account['password_hash'], password):
            return render_template('login.html', error='Invalid email or password.'), 401
        session.clear()
        session['admin_id'] = account['admin_id']
        session['role'] = 'ADMIN'
        _csrf()
        return redirect(url_for('geo_admin.dashboard'))


@admin_bp.get('/')
@admin_required
def dashboard():
    students = _read('''
        SELECT s.student_id, s.student_number, u.user_id, u.full_name,
               u.email, u.account_status
        FROM students s JOIN users u ON u.user_id = s.user_id
        ORDER BY u.full_name
    ''')
    lecturers = _read('''
        SELECT l.lecturer_id, l.staff_number, u.user_id, u.full_name,
               u.email, u.account_status
        FROM lecturers l JOIN users u ON u.user_id = l.user_id
        ORDER BY u.full_name
    ''')
    courses = _read('SELECT * FROM courses ORDER BY course_code')
    rooms = _read('SELECT * FROM rooms ORDER BY room_name')
    sections = _read('''
        SELECT cs.*, c.course_code, c.course_name,
               u.full_name AS lecturer_name, r.room_name
        FROM class_sections cs
        JOIN courses c ON c.course_id = cs.course_id
        JOIN lecturers l ON l.lecturer_id = cs.lecturer_id
        JOIN users u ON u.user_id = l.user_id
        JOIN rooms r ON r.room_id = cs.room_id
        ORDER BY cs.academic_year DESC, c.course_code
    ''')
    enrolments = _read('''
        SELECT e.enrolment_id, e.enrolment_status,
               u.full_name AS student_name, c.course_code,
               cs.section_id
        FROM enrolments e
        JOIN students s ON s.student_id = e.student_id
        JOIN users u ON u.user_id = s.user_id
        JOIN class_sections cs ON cs.section_id = e.section_id
        JOIN courses c ON c.course_id = cs.course_id
        ORDER BY u.full_name, c.course_code
    ''')
    return render_template('admin.html', students=students, lecturers=lecturers,
                           courses=courses, rooms=rooms, sections=sections,
                           enrolments=enrolments, days=DAYS, csrf_token=_csrf())


@admin_bp.post('/logout')
@admin_required
def logout():
    session.clear()
    return redirect(url_for('login'))


def _new_user(kind):
    name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    number = request.form.get('number', '').strip()
    if not (1 <= len(name) <= 120) or not _email(email) or not (1 <= len(number) <= 40):
        raise ValueError('Enter a name, valid email, and student/staff number.')
    if len(password) < 10:
        raise ValueError('New account passwords must be at least 10 characters.')
    with closing(connect()) as conn, conn:
        if conn.execute('SELECT 1 FROM admin_accounts WHERE email = ?', (email,)).fetchone():
            raise ValueError('That email already belongs to an administrator.')
        cursor = conn.execute('''INSERT INTO users
                (full_name, email, password_hash, role, account_status)
                VALUES (?, ?, ?, ?, 'ACTIVE')''',
                (name, email, generate_password_hash(password), kind))
        if kind == 'STUDENT':
            conn.execute('INSERT INTO students(user_id, student_number) VALUES (?, ?)',
                         (cursor.lastrowid, number))
        else:
            conn.execute('INSERT INTO lecturers(user_id, staff_number) VALUES (?, ?)',
                         (cursor.lastrowid, number))


@admin_bp.post('/students/add')
@admin_required
def add_student():
    try:
        _new_user('STUDENT')
        flash('Student created.', 'success')
    except (ValueError, sqlite3.IntegrityError) as exc:
        _flash_error(exc)
    return redirect(url_for('geo_admin.dashboard') + '#students')


@admin_bp.post('/lecturers/add')
@admin_required
def add_lecturer():
    try:
        _new_user('LECTURER')
        flash('Lecturer created.', 'success')
    except (ValueError, sqlite3.IntegrityError) as exc:
        _flash_error(exc)
    return redirect(url_for('geo_admin.dashboard') + '#lecturers')


@admin_bp.post('/users/<int:user_id>/edit')
@admin_required
def edit_user(user_id):
    name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip().lower()
    status = request.form.get('status', '')
    password = request.form.get('password', '')
    if not (1 <= len(name) <= 120) or not _email(email) or status not in ('ACTIVE', 'INACTIVE'):
        flash('Invalid name, email, or account status.', 'error')
        return redirect(url_for('geo_admin.dashboard') + '#students')
    if password and len(password) < 10:
        flash('New passwords must have at least 10 characters.', 'error')
        return redirect(url_for('geo_admin.dashboard') + '#students')
    try:
        with closing(connect()) as conn, conn:
            if password:
                cursor = conn.execute('''UPDATE users SET full_name=?, email=?,
                    account_status=?, password_hash=?, updated_at=CURRENT_TIMESTAMP
                    WHERE user_id=?''',
                    (name, email, status, generate_password_hash(password), user_id))
            else:
                cursor = conn.execute('''UPDATE users SET full_name=?, email=?,
                    account_status=?, updated_at=CURRENT_TIMESTAMP WHERE user_id=?''',
                    (name, email, status, user_id))
            if cursor.rowcount == 0:
                raise ValueError('User not found.')
        flash('Account updated.', 'success')
    except (ValueError, sqlite3.IntegrityError) as exc:
        _flash_error(exc)
    return redirect(url_for('geo_admin.dashboard') + '#students')


@admin_bp.post('/courses/add')
@admin_required
def add_course():
    code = request.form.get('course_code', '').strip().upper()
    name = request.form.get('course_name', '').strip()
    if not (1 <= len(code) <= 30) or not (1 <= len(name) <= 150):
        flash('Provide a course code and name.', 'error')
    else:
        try:
            with closing(connect()) as conn, conn:
                conn.execute('INSERT INTO courses(course_code,course_name) VALUES (?,?)', (code, name))
            flash('Course created.', 'success')
        except sqlite3.IntegrityError as exc:
            _flash_error(exc)
    return redirect(url_for('geo_admin.dashboard') + '#classes')


@admin_bp.post('/classes/add')
@admin_required
def add_class():
    try:
        course_id = int(request.form.get('course_id', ''))
        lecturer_id = int(request.form.get('lecturer_id', ''))
        room_id = int(request.form.get('room_id', ''))
        semester = request.form.get('semester', '').strip()
        year = request.form.get('academic_year', '').strip()
        day = request.form.get('day_of_week', '').strip()
        start = request.form.get('start_time', '').strip()
        end = request.form.get('end_time', '').strip()
        if (not semester or len(semester) > 40 or not re.fullmatch(r'\d{4}', year)
                or day not in DAYS or not re.fullmatch(r'\d\d:\d\d', start)
                or not re.fullmatch(r'\d\d:\d\d', end) or start >= end):
            raise ValueError('Invalid class details. Check semester, year, day, and times.')
        with closing(connect()) as conn, conn:
            conn.execute('''INSERT INTO class_sections
                (course_id,lecturer_id,room_id,semester,academic_year,day_of_week,start_time,end_time)
                VALUES (?,?,?,?,?,?,?,?)''',
                (course_id, lecturer_id, room_id, semester, year, day, start, end))
        flash('Class section created.', 'success')
    except (TypeError, ValueError, sqlite3.IntegrityError) as exc:
        _flash_error(exc)
    return redirect(url_for('geo_admin.dashboard') + '#classes')


@admin_bp.post('/enrolments/add')
@admin_required
def add_enrolment():
    try:
        student_id = int(request.form.get('student_id', ''))
        section_id = int(request.form.get('section_id', ''))
        with closing(connect()) as conn, conn:
            conn.execute('''INSERT INTO enrolments(student_id,section_id,enrolment_status)
                VALUES (?,?,'ACTIVE') ON CONFLICT(student_id,section_id)
                DO UPDATE SET enrolment_status='ACTIVE' ''', (student_id, section_id))
        flash('Student enrolled.', 'success')
    except (ValueError, sqlite3.IntegrityError) as exc:
        _flash_error(exc)
    return redirect(url_for('geo_admin.dashboard') + '#enrolments')


@admin_bp.post('/enrolments/<int:enrolment_id>/status')
@admin_required
def enrolment_status(enrolment_id):
    status = request.form.get('status')
    if status not in ('ACTIVE', 'DROPPED'):
        abort(400)
    with closing(connect()) as conn, conn:
        conn.execute('UPDATE enrolments SET enrolment_status=? WHERE enrolment_id=?',
                     (status, enrolment_id))
    flash('Enrolment updated.', 'success')
    return redirect(url_for('geo_admin.dashboard') + '#enrolments')
