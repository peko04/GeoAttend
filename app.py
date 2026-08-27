from flask import Flask, render_template, request, jsonify

# Database functions
from database import (
    get_user_by_email,
    get_classes_for_teacher,
    get_classes_for_student,
    get_students_in_class,
    get_session_by_qr,
    create_attendance_session,
    enrol_student,
    record_attendance,
    get_attendance_for_session
)

app = Flask(
    __name__,
    template_folder="website",
    static_folder="website_assets"
)


# =========================================================
# AMANIEL - PROJECT / BACKEND INTEGRATION
# =========================================================

@app.route("/")
def home():
    return render_template("login.html")


# =========================================================
# NATHAN - LOGIN / USER AUTHENTICATION
# =========================================================

@app.route("/login", methods=["POST"])
def login():

    email = request.form.get("email")
    password = request.form.get("password")
    portal = request.form.get("portal")

    user = get_user_by_email(email)

    if user is None:
        return "Incorrect email or password", 401

    if not check_password_hash(user["password_hash"], password):
        return "Incorrect email or password", 401

    if user["role"] != portal:
        return "You are using the wrong login portal", 403

    session["user_id"] = user["user_id"]
    session["name"] = user["name"]
    session["role"] = user["role"]

    if user["role"] == "student":
        return redirect(url_for("student_page"))

    if user["role"] == "teacher":
        return redirect(url_for("teacher_page"))

    return "Invalid account role", 403

# =========================================================
# STUDENT DASHBOARD
# Frontend + backend integration
# =========================================================

@app.route("/student/<int:student_id>")
def student_dashboard(student_id):

    # Gets classes belonging to the logged-in student
    classes = get_classes_for_student(student_id)

    # Frontend can use this data later
    return jsonify([
        dict(classroom) for classroom in classes
    ])


# =========================================================
# TEACHER DASHBOARD
# =========================================================

@app.route("/teacher/<int:teacher_id>")
def teacher_dashboard(teacher_id):

    classes = get_classes_for_teacher(teacher_id)

    return jsonify([
        dict(classroom) for classroom in classes
    ])


@app.route("/class/<int:class_id>/students")
def class_students(class_id):

    students = get_students_in_class(class_id)

    return jsonify([
        dict(student) for student in students
    ])


# =========================================================
# TOM - QR CODE SYSTEM
# =========================================================

@app.route("/qr/validate", methods=["POST"])
def validate_qr():

    # Tom:
    # Frontend QR scanner sends something like:
    #
    # {
    #     "qr_token": "ABC123"
    # }
    #
    # Use get_session_by_qr() to check it

    data = request.get_json()

    qr_token = data.get("qr_token")

    session = get_session_by_qr(qr_token)

    if session:
        return jsonify({
            "valid": True,
            "session_id": session["session_id"]
        })

    return jsonify({
        "valid": False
    })


# =========================================================
# AVASH - LOCATION / GPS VALIDATION
# =========================================================

@app.route("/location/validate", methods=["POST"])
def validate_location():

    # Avash:
    # Frontend sends student GPS:
    #
    # {
    #     "latitude": ...,
    #     "longitude": ...,
    #     "session_id": ...
    # }
    #
    # Python should compare student location
    # against the expected session location.

    return jsonify({
        "message": "Location validation not implemented yet"
    })


# =========================================================
# TOM + TEACHER SYSTEM
# CREATE ATTENDANCE SESSION
# =========================================================

@app.route("/attendance/session", methods=["POST"])
def start_attendance_session():

    # Later:
    # Teacher chooses class
    # QR token gets generated
    # GPS location gets stored
    # Session gets created using:
    #
    # create_attendance_session(...)

    return jsonify({
        "message": "Attendance session creation not implemented yet"
    })


# =========================================================
# AMANIEL / INTEGRATION
# ATTENDANCE RECORDING
# =========================================================

@app.route("/attendance", methods=["POST"])
def attendance():

    # Final integration route
    #
    # This will eventually receive:
    #
    # QR token
    # student location
    # logged-in student
    #
    # Then:
    #
    # 1. Validate QR
    # 2. Validate GPS
    # 3. Check time
    # 4. Decide present / late / rejected
    # 5. Call record_attendance()

    return jsonify({
        "message": "Attendance integration not implemented yet"
    })


# =========================================================
# TEACHER - VIEW ATTENDANCE
# =========================================================

@app.route("/attendance/session/<int:session_id>")
def view_attendance(session_id):

    records = get_attendance_for_session(session_id)

    return jsonify([
        dict(record) for record in records
    ])


# =========================================================
# ADMIN - STUDENT ENROLMENT
# =========================================================

@app.route("/admin/enrol", methods=["POST"])
def admin_enrol():

    # Admin frontend should send:
    #
    # {
    #     "student_id": 3,
    #     "class_id": 1
    # }

    data = request.get_json()

    student_id = data.get("student_id")
    class_id = data.get("class_id")

    enrol_student(student_id, class_id)

    return jsonify({
        "message": "Student enrolled successfully"
    })


# =========================================================
# RUN GEOATTEND
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)