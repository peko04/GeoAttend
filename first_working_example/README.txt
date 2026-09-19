BARE BONES GEOATTEND

1. Open this folder in PyCharm.
2. In its terminal: python -m pip install flask
3. Run app.py and open http://127.0.0.1:5007

Files: app.py, database.py, database.sqlite, and three HTML templates.
No CSS. QR JavaScript is inside the student and teacher HTML pages.
The selection page has its original controls; it is not password authentication.

Teacher: select subject and week, then Start QR session.
Student: start camera and scan. A match saves PRESENT and UTC time.
Refresh teacher attendance using the link. Blank weeks stay blank.
Existing PRESENT/LATE/ABSENT/etc. results were copied from your database.
Starting another session for the same subject replaces its active token.
Existing attendance is kept and duplicate check-ins fail.
No GPS, late calculations, expiry, clock-out or manual editing.

The included database.sqlite is an exact copy of your original uploaded database.
No tables, columns, records, or other database contents were changed during packaging.
The app reads your existing tables. Using Start Session or scanning successfully
will naturally add/update QR sessions and attendance in those existing tables.

Weeks are calculated from dates: the earliest session per class is Week 1,
seven days later is Week 2, etc. Your existing dates follow this pattern.
Choosing Week 13 creates a session with that week's scheduled date, while the
actual check-in time is stored separately in UTC. There are no timing checks.
This assumes one session per class per week. Empty cells remain blank.

The QR libraries need internet. Use a computer camera on localhost, displaying
the teacher QR on another screen or paper. Camera use on a phone requires HTTPS
and a reachable server; this version runs locally only.

Code guide:
app.py handles forms, renders pages and receives scanned tokens.
database.py runs SELECT/INSERT/UPDATE queries with ? parameters.
attendance_grid maps (student ID, week) to its status for the tables.
"with closing(connect()) as db, db" closes the connection and commits successful
writes (or rolls them back on errors). Token matching happens inside check_in.
