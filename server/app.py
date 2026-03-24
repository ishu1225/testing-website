import csv
import hashlib
import io
import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import closing
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Flask, g, jsonify, make_response, request, send_file
from flask_cors import CORS
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": os.getenv("CORS_ORIGIN", "*")}})


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def migrate_if_needed(conn):
    test_cols = [row["name"] for row in conn.execute("PRAGMA table_info(tests)").fetchall()]
    if "admin_id" not in test_cols:
        conn.execute("ALTER TABLE tests ADD COLUMN admin_id INTEGER")
    if "expires_at" not in test_cols:
        conn.execute("ALTER TABLE tests ADD COLUMN expires_at TEXT")


def init_db():
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                duration INTEGER NOT NULL,
                admin_id INTEGER,
                expires_at TEXT,
                FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE SET NULL
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                option_a TEXT NOT NULL,
                option_b TEXT NOT NULL,
                option_c TEXT NOT NULL,
                option_d TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id INTEGER NOT NULL,
                student_name TEXT NOT NULL,
                reg_number TEXT NOT NULL,
                section TEXT NOT NULL,
                answers TEXT NOT NULL,
                score INTEGER NOT NULL,
                tab_switch_count INTEGER NOT NULL DEFAULT 0,
                time_taken INTEGER NOT NULL,
                submitted_at TEXT NOT NULL,
                attempt_key TEXT NOT NULL UNIQUE,
                FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                token TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE CASCADE
            );
            """
        )
        migrate_if_needed(conn)
        conn.commit()


def parse_questions(raw_text):
    blocks = re.split(r"\n\s*\n", raw_text.strip())
    parsed = []

    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 6:
            continue

        q_match = re.match(r"^Q\d+[\.\)]\s*(.+)$", lines[0], re.IGNORECASE)
        if not q_match:
            continue

        question_text = q_match.group(1).strip()
        options = {"A": "", "B": "", "C": "", "D": ""}
        answer = ""

        for line in lines[1:]:
            opt_match = re.match(r"^([ABCD])[\.\)]\s*(.+)$", line, re.IGNORECASE)
            if opt_match:
                options[opt_match.group(1).upper()] = opt_match.group(2).strip()
                continue

            ans_match = re.match(r"^Answer\s*:\s*([ABCD])$", line, re.IGNORECASE)
            if ans_match:
                answer = ans_match.group(1).upper()

        if all(options.values()) and answer in options:
            parsed.append(
                {
                    "question_text": question_text,
                    "option_a": options["A"],
                    "option_b": options["B"],
                    "option_c": options["C"],
                    "option_d": options["D"],
                    "correct_answer": answer,
                }
            )

    return parsed


def parse_iso_datetime(value):
    if not value:
        return None
    try:
        clean = value.replace("Z", "+00:00") if isinstance(value, str) else value
        parsed = datetime.fromisoformat(clean)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except ValueError:
        return None


def now_utc_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def normalize_utc_string(value):
    if not value:
        return value
    if isinstance(value, str) and value.endswith("Z"):
        return value
    if isinstance(value, str) and ("+" in value[10:] or value.endswith("00:00")):
        return value
    return f"{value}Z"


def get_admin_from_token():
    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "", 1).strip()
    if not token:
        token = (request.args.get("token") or "").strip()
    if not token:
        return None

    with closing(get_db_connection()) as conn:
        row = conn.execute(
            """
            SELECT a.id, a.user_id, a.email
            FROM admin_sessions s
            JOIN admins a ON a.id = s.admin_id
            WHERE s.token = ?
            """,
            (token,),
        ).fetchone()
    return row


def admin_required(handler):
    @wraps(handler)
    def wrapped(*args, **kwargs):
        admin = get_admin_from_token()
        if not admin:
            return jsonify({"error": "Admin authentication required"}), 401
        g.admin = admin
        return handler(*args, **kwargs)

    return wrapped


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "timestamp": int(time.time())})


@app.post("/api/admin/register")
def admin_register():
    data = request.get_json(force=True)
    user_id = (data.get("userId") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()

    if not user_id or not email or not password:
        return jsonify({"error": "User ID, email and password are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    try:
        with closing(get_db_connection()) as conn:
            conn.execute(
                """
                INSERT INTO admins (user_id, email, password_hash, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, email, hash_password(password), now_utc_iso()),
            )
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "User ID or email already exists"}), 409

    return jsonify({"message": "Admin account created"})


@app.post("/api/admin/login")
def admin_login():
    data = request.get_json(force=True)
    user_id = (data.get("userId") or "").strip()
    password = (data.get("password") or "").strip()
    if not user_id or not password:
        return jsonify({"error": "User ID and password are required"}), 400

    with closing(get_db_connection()) as conn:
        admin = conn.execute(
            "SELECT id, user_id, email, password_hash FROM admins WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not admin or admin["password_hash"] != hash_password(password):
            return jsonify({"error": "Invalid credentials"}), 401

        token = secrets.token_urlsafe(32)
        conn.execute(
            "INSERT INTO admin_sessions (admin_id, token, created_at) VALUES (?, ?, ?)",
            (admin["id"], token, now_utc_iso()),
        )
        conn.commit()

    return jsonify(
        {
            "token": token,
            "admin": {"id": admin["id"], "userId": admin["user_id"], "email": admin["email"]},
        }
    )


@app.post("/api/admin/forgot-password")
def admin_forgot_password():
    data = request.get_json(force=True)
    user_id = (data.get("userId") or "").strip()
    email = (data.get("email") or "").strip().lower()
    new_password = (data.get("newPassword") or "").strip()
    if not user_id or not email or not new_password:
        return jsonify({"error": "User ID, linked email and new password are required"}), 400
    if len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    with closing(get_db_connection()) as conn:
        updated = conn.execute(
            """
            UPDATE admins
            SET password_hash = ?
            WHERE user_id = ? AND email = ?
            """,
            (hash_password(new_password), user_id, email),
        )
        conn.commit()
        if updated.rowcount == 0:
            return jsonify({"error": "User ID and linked email do not match"}), 404

    return jsonify({"message": "Password reset successful"})


@app.post("/api/admin/change-password")
@admin_required
def admin_change_password():
    data = request.get_json(force=True)
    current_password = (data.get("currentPassword") or "").strip()
    new_password = (data.get("newPassword") or "").strip()
    if not current_password or not new_password:
        return jsonify({"error": "Current password and new password are required"}), 400
    if len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters"}), 400

    with closing(get_db_connection()) as conn:
        row = conn.execute(
            "SELECT password_hash FROM admins WHERE id = ?",
            (g.admin["id"],),
        ).fetchone()
        if not row or row["password_hash"] != hash_password(current_password):
            return jsonify({"error": "Current password is incorrect"}), 401

        conn.execute(
            "UPDATE admins SET password_hash = ? WHERE id = ?",
            (hash_password(new_password), g.admin["id"]),
        )
        conn.commit()

    return jsonify({"message": "Password changed successfully"})


@app.get("/api/admin/me")
@admin_required
def admin_me():
    return jsonify(
        {
            "id": g.admin["id"],
            "userId": g.admin["user_id"],
            "email": g.admin["email"],
        }
    )


@app.post("/api/tests")
@admin_required
def create_test():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    duration = data.get("duration")
    raw_questions = (data.get("rawQuestions") or "").strip()
    expiry_value = data.get("expiryValue")
    expiry_unit = (data.get("expiryUnit") or "").strip().lower()

    if not name:
        return jsonify({"error": "Test name is required"}), 400
    if not isinstance(duration, int) or duration <= 0:
        return jsonify({"error": "Duration must be a positive integer"}), 400
    if not raw_questions:
        return jsonify({"error": "Questions text is required"}), 400
    if not isinstance(expiry_value, int) or expiry_value <= 0:
        return jsonify({"error": "Expiry value must be a positive integer"}), 400
    if expiry_unit not in {"hours", "days"}:
        return jsonify({"error": "Expiry unit must be hours or days"}), 400

    questions = parse_questions(raw_questions)
    if not questions:
        return jsonify({"error": "Could not parse questions. Check format."}), 400

    delta = timedelta(hours=expiry_value) if expiry_unit == "hours" else timedelta(days=expiry_value)
    expires_at = now_utc_iso() if delta.total_seconds() == 0 else (datetime.utcnow() + delta).replace(microsecond=0).isoformat() + "Z"

    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tests (name, duration, admin_id, expires_at) VALUES (?, ?, ?, ?)",
            (name, duration, g.admin["id"], expires_at),
        )
        test_id = cursor.lastrowid

        cursor.executemany(
            """
            INSERT INTO questions (
                test_id, question_text, option_a, option_b, option_c, option_d, correct_answer
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    test_id,
                    q["question_text"],
                    q["option_a"],
                    q["option_b"],
                    q["option_c"],
                    q["option_d"],
                    q["correct_answer"],
                )
                for q in questions
            ],
        )
        conn.commit()

    return jsonify(
        {
            "id": test_id,
            "name": name,
            "duration": duration,
            "questionCount": len(questions),
            "testLink": f"/test/{test_id}",
            "expiresAt": normalize_utc_string(expires_at),
        }
    ), 201


@app.get("/api/tests")
@admin_required
def list_tests():
    with closing(get_db_connection()) as conn:
        rows = conn.execute(
            """
            SELECT t.id, t.name, t.duration, COUNT(q.id) as question_count
                 , t.expires_at
            FROM tests t
            LEFT JOIN questions q ON q.test_id = t.id
            WHERE t.admin_id = ?
            GROUP BY t.id
            ORDER BY t.id DESC
            """,
            (g.admin["id"],),
        ).fetchall()

    tests = [
        {
            "id": row["id"],
            "name": row["name"],
            "duration": row["duration"],
            "questionCount": row["question_count"],
            "testLink": f"/test/{row['id']}",
            "expiresAt": normalize_utc_string(row["expires_at"]),
            "isExpired": bool(parse_iso_datetime(row["expires_at"]) and datetime.utcnow() > parse_iso_datetime(row["expires_at"])),
        }
        for row in rows
    ]
    return jsonify(tests)


@app.get("/api/tests/<int:test_id>")
def get_test(test_id):
    with closing(get_db_connection()) as conn:
        test = conn.execute(
            "SELECT id, name, duration, expires_at FROM tests WHERE id = ?",
            (test_id,),
        ).fetchone()
        if not test:
            return jsonify({"error": "Test not found"}), 404
        expires_at = parse_iso_datetime(test["expires_at"])
        if expires_at and datetime.utcnow() > expires_at:
            return jsonify({"error": "This test link has expired"}), 410

        questions = conn.execute(
            """
            SELECT id, question_text, option_a, option_b, option_c, option_d
            FROM questions WHERE test_id = ? ORDER BY id ASC
            """,
            (test_id,),
        ).fetchall()

    return jsonify(
        {
            "id": test["id"],
            "name": test["name"],
            "duration": test["duration"],
            "expiresAt": normalize_utc_string(test["expires_at"]),
            "questions": [
                {
                    "id": q["id"],
                    "questionText": q["question_text"],
                    "optionA": q["option_a"],
                    "optionB": q["option_b"],
                    "optionC": q["option_c"],
                    "optionD": q["option_d"],
                }
                for q in questions
            ],
        }
    )


@app.post("/api/tests/<int:test_id>/submit")
def submit_test(test_id):
    data = request.get_json(force=True)
    student_name = (data.get("studentName") or "").strip()
    reg_number = (data.get("regNumber") or "").strip()
    section = (data.get("section") or "").strip()
    answers = data.get("answers") or {}
    tab_switch_count = data.get("tabSwitchCount", 0)
    time_taken = data.get("timeTaken", 0)

    if not student_name or not reg_number or not section:
        return jsonify({"error": "Student details are required"}), 400
    if not isinstance(answers, dict):
        return jsonify({"error": "Answers must be an object"}), 400
    if not isinstance(tab_switch_count, int) or tab_switch_count < 0:
        return jsonify({"error": "Invalid tab switch count"}), 400
    if not isinstance(time_taken, int) or time_taken < 0:
        return jsonify({"error": "Invalid time taken"}), 400

    with closing(get_db_connection()) as conn:
        test = conn.execute(
            "SELECT id, expires_at FROM tests WHERE id = ?",
            (test_id,),
        ).fetchone()
        if not test:
            return jsonify({"error": "Test not found"}), 404
        expires_at = parse_iso_datetime(test["expires_at"])
        if expires_at and datetime.utcnow() > expires_at:
            return jsonify({"error": "This test link has expired"}), 410

        attempt_key = f"{test_id}:{reg_number.upper()}"
        existing = conn.execute(
            "SELECT id FROM submissions WHERE attempt_key = ?",
            (attempt_key,),
        ).fetchone()
        if existing:
            return jsonify({"error": "You have already submitted this test"}), 409

        question_rows = conn.execute(
            "SELECT id, correct_answer FROM questions WHERE test_id = ?",
            (test_id,),
        ).fetchall()
        answer_map = {str(row["id"]): row["correct_answer"] for row in question_rows}

        score = 0
        for qid, correct in answer_map.items():
            selected = str(answers.get(qid, "")).upper()
            if selected == correct:
                score += 1

        submitted_at = now_utc_iso()
        conn.execute(
            """
            INSERT INTO submissions (
                test_id, student_name, reg_number, section, answers, score,
                tab_switch_count, time_taken, submitted_at, attempt_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                test_id,
                student_name,
                reg_number,
                section,
                json.dumps(answers),
                score,
                tab_switch_count,
                time_taken,
                submitted_at,
                attempt_key,
            ),
        )
        conn.commit()

    return jsonify({"message": "Submitted successfully", "score": score})


@app.get("/api/tests/<int:test_id>/results")
@admin_required
def get_results(test_id):
    with closing(get_db_connection()) as conn:
        owner = conn.execute(
            "SELECT id FROM tests WHERE id = ? AND admin_id = ?",
            (test_id, g.admin["id"]),
        ).fetchone()
        if not owner:
            return jsonify({"error": "Test not found"}), 404

        rows = conn.execute(
            """
            SELECT id, student_name, reg_number, section, score, tab_switch_count, time_taken, submitted_at
            FROM submissions
            WHERE test_id = ?
            ORDER BY submitted_at DESC
            """,
            (test_id,),
        ).fetchall()

    return jsonify(
        [
            {
                "id": row["id"],
                "studentName": row["student_name"],
                "regNumber": row["reg_number"],
                "section": row["section"],
                "score": row["score"],
                "tabSwitchCount": row["tab_switch_count"],
                "timeTaken": row["time_taken"],
                "submittedAt": normalize_utc_string(row["submitted_at"]),
            }
            for row in rows
        ]
    )


@app.get("/api/tests/<int:test_id>/results/export/csv")
@admin_required
def export_results_csv(test_id):
    with closing(get_db_connection()) as conn:
        owner = conn.execute(
            "SELECT id FROM tests WHERE id = ? AND admin_id = ?",
            (test_id, g.admin["id"]),
        ).fetchone()
        if not owner:
            return jsonify({"error": "Test not found"}), 404

        rows = conn.execute(
            """
            SELECT student_name, reg_number, section, score, tab_switch_count, time_taken, submitted_at
            FROM submissions
            WHERE test_id = ?
            ORDER BY submitted_at DESC
            """,
            (test_id,),
        ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Name",
            "Registration Number",
            "Section",
            "Score",
            "Tab Switch Count",
            "Time Taken (seconds)",
            "Submitted At (UTC)",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row["student_name"],
                row["reg_number"],
                row["section"],
                row["score"],
                row["tab_switch_count"],
                row["time_taken"],
                normalize_utc_string(row["submitted_at"]),
            ]
        )

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv"
    response.headers["Content-Disposition"] = f"attachment; filename=test_{test_id}_results.csv"
    return response


@app.get("/api/submissions/<int:submission_id>/pdf")
@admin_required
def export_submission_pdf(submission_id):
    with closing(get_db_connection()) as conn:
        row = conn.execute(
            """
            SELECT student_name, reg_number, section, score, tab_switch_count, time_taken, submitted_at
            FROM submissions s
            JOIN tests t ON t.id = s.test_id
            WHERE s.id = ? AND t.admin_id = ?
            """,
            (submission_id, g.admin["id"]),
        ).fetchone()

    if not row:
        return jsonify({"error": "Submission not found"}), 404

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    y = 800
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "Student Test Report")
    y -= 40
    pdf.setFont("Helvetica", 12)
    fields = [
        ("Name", row["student_name"]),
        ("Registration Number", row["reg_number"]),
        ("Section", row["section"]),
        ("Score", str(row["score"])),
        ("Tab Switch Count", str(row["tab_switch_count"])),
        ("Time Taken (seconds)", str(row["time_taken"])),
        ("Submitted At (UTC)", normalize_utc_string(row["submitted_at"])),
    ]
    for label, value in fields:
        pdf.drawString(50, y, f"{label}: {value}")
        y -= 24

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"submission_{submission_id}.pdf",
    )


@app.get("/api/tests/<int:test_id>/results/export/pdf")
@admin_required
def export_results_pdf(test_id):
    with closing(get_db_connection()) as conn:
        test = conn.execute(
            "SELECT id, name, duration, expires_at FROM tests WHERE id = ? AND admin_id = ?",
            (test_id, g.admin["id"]),
        ).fetchone()
        if not test:
            return jsonify({"error": "Test not found"}), 404

        rows = conn.execute(
            """
            SELECT student_name, reg_number, section, score, tab_switch_count, time_taken, submitted_at
            FROM submissions
            WHERE test_id = ?
            ORDER BY submitted_at DESC
            """,
            (test_id,),
        ).fetchall()

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setTitle(f"test_{test_id}_results_report")

    y = 810
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y, f"Test Results Report: {test['name']} (ID: {test_id})")
    y -= 20
    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, y, f"Duration: {test['duration']} minutes")
    y -= 14
    pdf.drawString(40, y, f"Expires At (UTC): {normalize_utc_string(test['expires_at']) or '-'}")
    y -= 20
    pdf.drawString(40, y, f"Total Submissions: {len(rows)}")
    if rows:
        avg_score = round(sum(row["score"] for row in rows) / len(rows), 2)
        avg_switch = round(sum(row["tab_switch_count"] for row in rows) / len(rows), 2)
        pdf.drawString(220, y, f"Average Score: {avg_score}")
        pdf.drawString(390, y, f"Avg Tab Switch: {avg_switch}")
    y -= 20

    pdf.setFont("Helvetica-Bold", 9)
    headers = ["Name", "Reg No.", "Sec", "Score", "Switch", "Time(s)", "Submitted At"]
    x_positions = [40, 130, 210, 250, 290, 335, 390]
    for i, header in enumerate(headers):
        pdf.drawString(x_positions[i], y, header)
    y -= 12
    pdf.line(40, y, 560, y)
    y -= 12

    pdf.setFont("Helvetica", 8)
    for row in rows:
        if y < 40:
            pdf.showPage()
            y = 810
            pdf.setFont("Helvetica-Bold", 9)
            for i, header in enumerate(headers):
                pdf.drawString(x_positions[i], y, header)
            y -= 12
            pdf.line(40, y, 560, y)
            y -= 12
            pdf.setFont("Helvetica", 8)

        values = [
            row["student_name"][:16],
            row["reg_number"][:12],
            row["section"][:6],
            str(row["score"]),
            str(row["tab_switch_count"]),
            str(row["time_taken"]),
            normalize_utc_string(row["submitted_at"])[:19].replace("T", " "),
        ]
        for i, value in enumerate(values):
            pdf.drawString(x_positions[i], y, value)
        y -= 11

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"test_{test_id}_results_report.pdf",
    )


@app.delete("/api/tests/<int:test_id>")
@admin_required
def delete_test(test_id):
    with closing(get_db_connection()) as conn:
        deleted = conn.execute(
            "DELETE FROM tests WHERE id = ? AND admin_id = ?",
            (test_id, g.admin["id"]),
        )
        conn.commit()
        if deleted.rowcount == 0:
            return jsonify({"error": "Test not found"}), 404
    return jsonify({"message": "Test and related submissions deleted"})


if __name__ == "__main__":
    init_db()
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
else:
    init_db()
