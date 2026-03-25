import csv
import hashlib
import bcrypt
import smtplib
import io
import json
import os
import re
import secrets
import sqlite3
import time
import textwrap
from contextlib import closing
from datetime import datetime, timedelta, timezone
from functools import wraps

import openpyxl
from email.mime.text import MIMEText
from flask import Flask, g, jsonify, make_response, request, send_file
from flask_cors import CORS
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from dotenv import load_dotenv


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
DB_PATH = os.path.join(BASE_DIR, "database.db")

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": os.getenv("CORS_ORIGIN", "*")}})


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def sha256_hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def normalize_answer_text(value):
    # Security answers are compared case-insensitively.
    # We normalize to lowercase + trim before hashing/comparing.
    if value is None:
        return ""
    return str(value).strip().lower()

def normalize_birth_date(value):
    """
    Expect DOB in strict calendar order as YYYY-MM-DD (from <input type="date">).
    We validate and normalize to the exact same string format.
    """
    v = (value or "").strip()
    if not v:
        return ""
    # Strict YYYY-MM-DD
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
        return ""
    return v

def hash_security_answer(normalized_value):
    # Store only hashes of normalized answers.
    return sha256_hash_password(normalized_value)


def hash_password(password):
    # bcrypt hashes include salt; verify must use checkpw.
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password, stored_hash):
    if not stored_hash:
        return False
    # bcrypt hashes start with $2b$ / $2a$ / $2y$
    if str(stored_hash).startswith("$2"):
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    # Backward compatibility: older admins stored sha256
    return sha256_hash_password(password) == stored_hash


def otp_code(length=6):
    # Generates a numeric OTP like 123456
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def otp_expires_utc(minutes=10):
    return (datetime.utcnow() + timedelta(minutes=minutes)).replace(microsecond=0).isoformat() + "Z"


def session_expires_utc(hours=8):
    return (datetime.utcnow() + timedelta(hours=hours)).replace(microsecond=0).isoformat() + "Z"


def otp_rate_limited(email, purpose, min_interval_seconds=60, max_requests=5, window_minutes=60):
    """
    Simple per-email/per-purpose OTP rate limit using SQLite timestamps.
    - min_interval_seconds: minimum seconds between consecutive OTP requests
    - max_requests: maximum OTPs allowed within window_minutes
    """
    email = (email or "").strip().lower()
    purpose = (purpose or "").strip().lower()
    if not email or not purpose:
        return False

    now = datetime.utcnow().replace(microsecond=0)
    window_start = (now - timedelta(minutes=window_minutes)).replace(microsecond=0)
    window_start_iso = window_start.isoformat() + "Z"

    with closing(get_db_connection()) as conn:
        last = conn.execute(
            "SELECT requested_at FROM otp_request_log WHERE email = ? AND purpose = ? ORDER BY requested_at DESC LIMIT 1",
            (email, purpose),
        ).fetchone()
        if last:
            last_dt = parse_iso_datetime(last["requested_at"])
            if last_dt and (now - last_dt) < timedelta(seconds=min_interval_seconds):
                return True

        row = conn.execute(
            "SELECT COUNT(*) as c FROM otp_request_log WHERE email = ? AND purpose = ? AND requested_at >= ?",
            (email, purpose, window_start_iso),
        ).fetchone()
        count = int(row["c"]) if row else 0
        return count >= int(max_requests)


def send_email_otp(to_email, subject, body):
    """
    Sends OTP using Gmail SMTP (or any SMTP).
    Requires env vars:
      SMTP_HOST, SMTP_PORT, SMTP_EMAIL, SMTP_PASSWORD, SMTP_USE_TLS
    """
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587").strip() or "587")
    smtp_email = os.getenv("SMTP_EMAIL", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
    smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes"}

    if not smtp_host or not smtp_email or not smtp_password:
        raise RuntimeError("SMTP is not configured (set SMTP_HOST/SMTP_EMAIL/SMTP_PASSWORD).")

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = smtp_email
    msg["To"] = to_email

    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
        if smtp_use_tls:
            server.starttls()
        server.login(smtp_email, smtp_password)
        server.sendmail(smtp_email, [to_email], msg.as_string())


def migrate_if_needed(conn):
    test_cols = [row["name"] for row in conn.execute("PRAGMA table_info(tests)").fetchall()]
    if "admin_id" not in test_cols:
        conn.execute("ALTER TABLE tests ADD COLUMN admin_id INTEGER")
    if "expires_at" not in test_cols:
        conn.execute("ALTER TABLE tests ADD COLUMN expires_at TEXT")

    admin_cols = [row["name"] for row in conn.execute("PRAGMA table_info(admins)").fetchall()]
    if "is_verified" not in admin_cols:
        conn.execute("ALTER TABLE admins ADD COLUMN is_verified INTEGER NOT NULL DEFAULT 0")
    if "verification_code" not in admin_cols:
        conn.execute("ALTER TABLE admins ADD COLUMN verification_code TEXT")
    if "verification_expires_at" not in admin_cols:
        conn.execute("ALTER TABLE admins ADD COLUMN verification_expires_at TEXT")
    if "reset_code" not in admin_cols:
        conn.execute("ALTER TABLE admins ADD COLUMN reset_code TEXT")
    if "reset_expires_at" not in admin_cols:
        conn.execute("ALTER TABLE admins ADD COLUMN reset_expires_at TEXT")

    # Security answers for password reset: DOB + city + school.
    # Stored as hashes (after normalization) for safer comparison.
    if "dob_answer_hash" not in admin_cols:
        conn.execute("ALTER TABLE admins ADD COLUMN dob_answer_hash TEXT")
    if "birth_city_answer_hash" not in admin_cols:
        conn.execute("ALTER TABLE admins ADD COLUMN birth_city_answer_hash TEXT")
    if "school_name_answer_hash" not in admin_cols:
        conn.execute("ALTER TABLE admins ADD COLUMN school_name_answer_hash TEXT")

    # Admin session expiry
    admin_session_cols = [row["name"] for row in conn.execute("PRAGMA table_info(admin_sessions)").fetchall()]
    if "expires_at" not in admin_session_cols:
        conn.execute("ALTER TABLE admin_sessions ADD COLUMN expires_at TEXT")

    # OTP abuse prevention (rate limiting per email+purpose)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS otp_request_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            purpose TEXT NOT NULL,
            requested_at TEXT NOT NULL
        )
        """
    )


def init_db():
    MASTER_ADMIN_USER_ID = "ISHU"
    MASTER_ADMIN_PASSWORD = "240204"

    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                is_verified INTEGER NOT NULL DEFAULT 0,
                verification_code TEXT,
                verification_expires_at TEXT,
                reset_code TEXT,
                reset_expires_at TEXT,
                dob_answer_hash TEXT,
                birth_city_answer_hash TEXT,
                school_name_answer_hash TEXT,
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
                expires_at TEXT,
                FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE CASCADE
            );
            """
        )
        migrate_if_needed(conn)

        # Ensure master admin always exists.
        # Master admin bypasses security-answers checks; password-only.
        master = conn.execute(
            "SELECT id FROM admins WHERE user_id = ?",
            (MASTER_ADMIN_USER_ID,),
        ).fetchone()
        if not master:
            placeholder_email = f"{MASTER_ADMIN_USER_ID}@local.test"
            conn.execute(
                """
                INSERT INTO admins (
                    user_id,
                    email,
                    password_hash,
                    is_verified,
                    dob_answer_hash,
                    birth_city_answer_hash,
                    school_name_answer_hash,
                    created_at
                ) VALUES (?, ?, ?, 1, ?, ?, ?, ?)
                """,
                (
                    MASTER_ADMIN_USER_ID,
                    placeholder_email,
                    hash_password(MASTER_ADMIN_PASSWORD),
                    hash_security_answer("master-dob"),
                    hash_security_answer("master-city"),
                    hash_security_answer("master-school"),
                    now_utc_iso(),
                ),
            )
            conn.commit()

        conn.commit()


def parse_questions(raw_text):
    """
    Parses MCQ text in flexible formats.

    Supported:
    - Question can be labeled as `Q1.`, `Q1)` or not labeled at all.
    - Options can be labeled as:
      - Letters: A-D (e.g. `A. foo`, `B) bar`)
      - Numbers: 1-4 (e.g. `1. foo`, `2) bar`)
      - Roman: I-IV (e.g. `I. foo`, `II) bar`)
    - Answer can be:
      - `Answer: B`, `Answer - 2`, `Correct Answer: IV`, `Ans: (A)`
    - "Fill in the blanks (enter)" lines are ignored.
    - Option lines can span multiple lines; non-option lines after an option
      are appended to the last option text.
    """
    raw = (raw_text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not raw:
        return []

    def normalize_space(s):
        return re.sub(r"\s+", " ", s or "").strip()

    def map_label_to_option(label_raw):
        if label_raw is None:
            return None
        label = normalize_space(str(label_raw)).upper()

        # Letters
        if label in {"A", "B", "C", "D"}:
            return label

        # Numbers
        if label in {"1", "2", "3", "4"}:
            return {"1": "A", "2": "B", "3": "C", "4": "D"}[label]

        # Roman numerals (I-IV)
        roman_map = {"I": "A", "II": "B", "III": "C", "IV": "D"}
        if label in roman_map:
            return roman_map[label]

        return None

    def extract_answer_token(line):
        # Remove leading marker words, then try to capture the first option-like token.
        candidate = re.sub(r"^(Answer|Ans|Correct Answer|Correct)\s*[:\-\)]\s*", "", line, flags=re.IGNORECASE).strip()
        candidate = candidate.strip("()[]{} ").strip()
        # Token could be like "B", "2", "II", "Option B"
        m = re.search(r"\b([A-Da-d]|[1-4]|IV|III|II|I)\b", candidate)
        if not m:
            return None
        return m.group(1)

    # Option line patterns:
    #   A. text | A) text | (A) text | 1. text | I. text
    option_line_re = re.compile(
        r"^\s*(?:Option\s*)?(?:\(?\s*)?(?P<label>[A-Da-d]|[1-4]|IV|III|II|I)\s*(?:\)?\s*)*(?:[\.\):\-])\s*(?P<text>.+?)\s*$",
        flags=re.IGNORECASE,
    )

    question_prefix_re = re.compile(
        r"^\s*(?:Q\s*|QUESTION\s*)?\s*\d+\s*[\.\)\:\-]\s*",
        flags=re.IGNORECASE,
    )

    lines = [normalize_space(l) for l in raw.split("\n")]
    # Keep empty lines out to simplify scanner.
    lines = [l for l in lines if l]

    parsed = []
    question_lines = []
    options = {"A": "", "B": "", "C": "", "D": ""}
    correct_answer = None
    in_options = False
    last_option_key = None

    def finalize_current():
        nonlocal question_lines, options, correct_answer, in_options, last_option_key
        qtext = normalize_space(" ".join(question_lines))
        if not qtext or not correct_answer:
            question_lines = []
            options = {"A": "", "B": "", "C": "", "D": ""}
            correct_answer = None
            in_options = False
            last_option_key = None
            return

        # Ensure all options exist (DB requires NOT NULL).
        # If missing, keep empty strings.
        parsed.append(
            {
                "question_text": qtext,
                "option_a": options.get("A", "") or "",
                "option_b": options.get("B", "") or "",
                "option_c": options.get("C", "") or "",
                "option_d": options.get("D", "") or "",
                "correct_answer": correct_answer,
            }
        )

        question_lines = []
        options = {"A": "", "B": "", "C": "", "D": ""}
        correct_answer = None
        in_options = False
        last_option_key = None

    for line in lines:
        # Ignore "Fill in the blanks (enter)" style helper lines.
        # (Only ignore if it's basically just that helper text.)
        if re.match(r"^\s*fill\s*in\s*the\s*blanks\s*(\(.+?\))?\s*$", line, flags=re.IGNORECASE):
            continue

        # Answer line
        ans_token = extract_answer_token(line) if re.match(r"^(Answer|Ans|Correct|Correct Answer)\b", line, flags=re.IGNORECASE) else None
        if ans_token:
            mapped = map_label_to_option(ans_token)
            if mapped:
                correct_answer = mapped
                finalize_current()
            continue

        # Option line
        opt_match = option_line_re.match(line)
        if opt_match:
            label = opt_match.group("label")
            text = normalize_space(opt_match.group("text"))
            mapped = map_label_to_option(label)
            if mapped:
                options[mapped] = text
                in_options = True
                last_option_key = mapped
            continue

        # If we are in options, allow multiline option continuation.
        if in_options and last_option_key:
            options[last_option_key] = normalize_space(f"{options[last_option_key]} {line}")
            continue

        # Question line
        # Remove leading prefixes like "Q1.", "1)" etc if present.
        cleaned = question_prefix_re.sub("", line).strip()
        if cleaned:
            question_lines.append(cleaned)

    # In case the last block has no Answer line, ignore (needs correct answer).
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
            SELECT a.id, a.user_id, a.email, s.expires_at, s.created_at
            FROM admin_sessions s
            JOIN admins a ON a.id = s.admin_id
            WHERE s.token = ?
            """,
            (token,),
        ).fetchone()
    if not row:
        return None

    # Token expiry hardening
    expires_at = row["expires_at"]
    if expires_at:
        expires_dt = parse_iso_datetime(expires_at)
    else:
        # Backward compatibility for older sessions: treat as expired after 8h.
        created_dt = parse_iso_datetime(row["created_at"])
        expires_dt = created_dt + timedelta(hours=8) if created_dt else None

    if expires_dt and expires_dt <= datetime.utcnow():
        # Best-effort cleanup
        with closing(get_db_connection()) as conn2:
            conn2.execute("DELETE FROM admin_sessions WHERE token = ?", (token,))
            conn2.commit()
        return None

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
    dob = normalize_birth_date(data.get("dob"))
    birth_city = normalize_answer_text(data.get("birthCity"))
    school_name = normalize_answer_text(data.get("schoolName"))

    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    # Simple mode: no OTP/email verification. Use a deterministic dummy email.
    if not email or "@" not in email:
        email = f"{user_id}@local.test"

    if not password:
        return jsonify({"error": "Password is required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    if not dob:
        return jsonify({"error": "DOB is required and must be in YYYY-MM-DD format"}), 400
    if not birth_city:
        return jsonify({"error": "City of birth is required"}), 400
    if not school_name:
        return jsonify({"error": "Name of school is required"}), 400

    dob_hash = hash_security_answer(dob)
    birth_city_hash = hash_security_answer(birth_city)
    school_name_hash = hash_security_answer(school_name)

    try:
        with closing(get_db_connection()) as conn:
            conn.execute(
                """
                INSERT INTO admins (
                    user_id, email, password_hash, is_verified,
                    verification_code, verification_expires_at,
                    reset_code, reset_expires_at,
                    dob_answer_hash, birth_city_answer_hash, school_name_answer_hash,
                    created_at
                )
                VALUES (?, ?, ?, 1, NULL, NULL, NULL, NULL, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    email,
                    hash_password(password),
                    dob_hash,
                    birth_city_hash,
                    school_name_hash,
                    now_utc_iso(),
                ),
            )
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "User ID or email already exists"}), 409

    return jsonify({"message": "Admin account created."})


@app.post("/api/admin/verify-email")
def admin_verify_email():
    return jsonify({"error": "Email/OTP verification is disabled in simple mode."}), 410


@app.post("/api/admin/login")
def admin_login():
    data = request.get_json(force=True)
    identifier = (data.get("userId") or data.get("identifier") or "").strip()
    password = (data.get("password") or "").strip()
    if not identifier:
        return jsonify({"error": "User ID is required"}), 400

    identifier_is_email = "@" in identifier
    user_id = identifier if not identifier_is_email else identifier.split("@", 1)[0]
    email = identifier.lower() if identifier_is_email else f"{user_id}@local.test"

    with closing(get_db_connection()) as conn:
        admin = conn.execute(
            "SELECT id, user_id, email, password_hash, dob_answer_hash, birth_city_answer_hash, school_name_answer_hash FROM admins WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        if not admin:
            return jsonify({"error": "Admin account not found"}), 404

        MASTER_ADMIN_USER_ID = "ISHU"
        MASTER_ADMIN_PASSWORD = "240204"

        # Master admin bypass: password-only.
        if admin["user_id"] == MASTER_ADMIN_USER_ID:
            if not password:
                return jsonify({"error": "Password is required"}), 400
            if not verify_password(password, admin["password_hash"]):
                return jsonify({"error": "Invalid credentials"}), 401
        else:
            # Normal admin login: password only.
            if not password:
                return jsonify({"error": "Password is required"}), 400
            if not verify_password(password, admin["password_hash"]):
                return jsonify({"error": "Invalid credentials"}), 401

        token = secrets.token_urlsafe(32)
        conn.execute(
            "INSERT INTO admin_sessions (admin_id, token, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (admin["id"], token, now_utc_iso(), session_expires_utc(hours=8)),
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
    return jsonify({"error": "Use /forgot-password/reset-password to reset your password."}), 400


@app.post("/api/admin/forgot-password/request-otp")
def admin_forgot_password_request_otp():
    # Kept for backward compatibility — redirect to direct reset.
    return jsonify({"error": "OTP flow is disabled. Use /forgot-password/reset-password."}), 410


@app.post("/api/admin/forgot-password/confirm-otp")
def admin_forgot_password_confirm_otp():
    # Kept for backward compatibility — redirect to direct reset.
    return jsonify({"error": "OTP flow is disabled. Use /forgot-password/reset-password."}), 410


@app.post("/api/admin/forgot-password/reset-password")
def admin_forgot_password_reset():
    """Direct reset: verify security answers then set new password. No OTP needed."""
    data = request.get_json(force=True)
    identifier = (data.get("userId") or data.get("identifier") or "").strip()
    dob = normalize_birth_date(data.get("dob"))
    birth_city = normalize_answer_text(data.get("birthCity"))
    school_name = normalize_answer_text(data.get("schoolName"))
    new_password = (data.get("newPassword") or "").strip()

    if not identifier:
        return jsonify({"error": "User ID is required"}), 400
    if not dob or not birth_city or not school_name:
        return jsonify({"error": "Date of birth, city of birth, and school name are required"}), 400
    if not new_password or len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters"}), 400

    identifier_is_email = "@" in identifier
    user_id = identifier if not identifier_is_email else identifier.split("@", 1)[0]

    with closing(get_db_connection()) as conn:
        admin = conn.execute(
            """
            SELECT id, user_id, dob_answer_hash, birth_city_answer_hash, school_name_answer_hash
            FROM admins
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

        if not admin:
            return jsonify({"error": "Admin account not found"}), 404

        if not (admin["dob_answer_hash"] and admin["birth_city_answer_hash"] and admin["school_name_answer_hash"]):
            return jsonify({"error": "Security answers not set for this account"}), 403

        if (
            hash_security_answer(dob) != admin["dob_answer_hash"]
            or hash_security_answer(birth_city) != admin["birth_city_answer_hash"]
            or hash_security_answer(school_name) != admin["school_name_answer_hash"]
        ):
            return jsonify({"error": "Security answers do not match. Please check your details."}), 401

        conn.execute(
            """
            UPDATE admins
            SET password_hash = ?, reset_code = NULL, reset_expires_at = NULL
            WHERE id = ?
            """,
            (hash_password(new_password), admin["id"]),
        )
        conn.commit()

    return jsonify({"message": "Password reset successfully."})


@app.get("/api/master-admin/admins")
@admin_required
def master_admin_list_admins():
    if g.admin["user_id"] != "ISHU":
        return jsonify({"error": "Forbidden"}), 403

    with closing(get_db_connection()) as conn:
        rows = conn.execute(
            """
            SELECT id, user_id, email, is_verified, created_at
            FROM admins
            ORDER BY id DESC
            """,
        ).fetchall()

    return jsonify(
        [
            {
                "id": row["id"],
                "userId": row["user_id"],
                "email": row["email"],
                "isVerified": bool(row["is_verified"]),
                "createdAt": normalize_utc_string(row["created_at"]),
            }
            for row in rows
        ]
    )


@app.post("/api/master-admin/admins/<int:admin_id>/reset-password")
@admin_required
def master_admin_reset_password(admin_id):
    if g.admin["user_id"] != "ISHU":
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json(force=True)
    new_password = (data.get("newPassword") or "").strip()
    if not new_password or len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters"}), 400

    with closing(get_db_connection()) as conn:
        admin = conn.execute("SELECT id FROM admins WHERE id = ?", (admin_id,)).fetchone()
        if not admin:
            return jsonify({"error": "Admin not found"}), 404

        conn.execute(
            """
            UPDATE admins
            SET password_hash = ?, reset_code = NULL, reset_expires_at = NULL
            WHERE id = ?
            """,
            (hash_password(new_password), admin_id),
        )
        conn.commit()

    return jsonify({"message": "Admin password updated."})


@app.delete("/api/master-admin/admins/<int:admin_id>/account")
@admin_required
def master_admin_delete_admin_account(admin_id):
    if g.admin["user_id"] != "ISHU":
        return jsonify({"error": "Forbidden"}), 403

    # Prevent locking yourself out.
    if admin_id == g.admin["id"]:
        return jsonify({"error": "Cannot delete master admin account"}), 403

    with closing(get_db_connection()) as conn:
        exists = conn.execute("SELECT id FROM admins WHERE id = ?", (admin_id,)).fetchone()
        if not exists:
            return jsonify({"error": "Admin not found"}), 404

        # Delete tests first so related submissions are removed.
        conn.execute("DELETE FROM tests WHERE admin_id = ?", (admin_id,))
        conn.execute("DELETE FROM admins WHERE id = ?", (admin_id,))
        conn.commit()

    return jsonify({"message": "Admin account deleted."})


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
        if not row or not verify_password(current_password, row["password_hash"]):
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


@app.delete("/api/admin/account")
@admin_required
def admin_delete_account():
    """
    Deletes the admin and all their tests/results.
    """
    admin_id = g.admin["id"]
    with closing(get_db_connection()) as conn:
        # Delete tests first so questions/submissions cascade correctly.
        conn.execute("DELETE FROM tests WHERE admin_id = ?", (admin_id,))
        # Then delete the admin record.
        conn.execute("DELETE FROM admins WHERE id = ?", (admin_id,))
        conn.commit()

    return jsonify({"message": "Account deleted"})


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


@app.get("/api/tests/<int:test_id>/wrong-answers")
@admin_required
def get_wrong_answers(test_id):
    with closing(get_db_connection()) as conn:
        owner = conn.execute(
            "SELECT id FROM tests WHERE id = ? AND admin_id = ?",
            (test_id, g.admin["id"]),
        ).fetchone()
        if not owner:
            return jsonify({"error": "Test not found"}), 404

        questions = conn.execute(
            """
            SELECT id, question_text, correct_answer
            FROM questions
            WHERE test_id = ?
            ORDER BY id ASC
            """,
            (test_id,),
        ).fetchall()

        qid_to_number = {row["id"]: idx + 1 for idx, row in enumerate(questions)}

        submissions = conn.execute(
            """
            SELECT id, student_name, reg_number, section, answers
            FROM submissions
            WHERE test_id = ?
            ORDER BY submitted_at DESC
            """,
            (test_id,),
        ).fetchall()

    response = []
    for sub in submissions:
        try:
            answers = json.loads(sub["answers"])
        except Exception:
            answers = {}

        wrong_questions = []
        for q in questions:
            selected = str(answers.get(str(q["id"]), "")).upper()
            if selected != str(q["correct_answer"]).upper():
                wrong_questions.append(
                    {
                        "questionNumber": qid_to_number[q["id"]],
                        "questionText": q["question_text"],
                    }
                )

        response.append(
            {
                "submissionId": sub["id"],
                "studentName": sub["student_name"],
                "regNumber": sub["reg_number"],
                "section": sub["section"],
                "wrongQuestions": wrong_questions,
            }
        )

    return jsonify(response)


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


@app.get("/api/tests/<int:test_id>/results/export/xlsx")
@admin_required
def export_results_xlsx(test_id):
    with closing(get_db_connection()) as conn:
        owner = conn.execute(
            "SELECT id FROM tests WHERE id = ? AND admin_id = ?",
            (test_id, g.admin["id"]),
        ).fetchone()
        if not owner:
            return jsonify({"error": "Test not found"}), 404

        test_questions = conn.execute(
            """
            SELECT id, question_text, correct_answer
            FROM questions
            WHERE test_id = ?
            ORDER BY id ASC
            """,
            (test_id,),
        ).fetchall()
        qid_to_number = {row["id"]: idx + 1 for idx, row in enumerate(test_questions)}

        rows = conn.execute(
            """
            SELECT
                id,
                student_name,
                reg_number,
                section,
                score,
                tab_switch_count,
                time_taken,
                submitted_at,
                answers
            FROM submissions
            WHERE test_id = ?
            ORDER BY submitted_at DESC
            """,
            (test_id,),
        ).fetchall()

    wb = openpyxl.Workbook()
    ws_summary = wb.active
    ws_summary.title = "Summary"
    ws_summary.append(
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
        ws_summary.append(
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

    ws_wrong = wb.create_sheet("Wrong Answers")
    ws_wrong.append(
        [
            "Name",
            "Registration Number",
            "Section",
            "Question No.",
            "Question Text",
        ]
    )

    for row in rows:
        try:
            answers = json.loads(row["answers"]) if row["answers"] else {}
        except Exception:
            answers = {}

        wrong_questions = []
        for q in test_questions:
            selected = str(answers.get(str(q["id"]), "")).upper()
            if selected != str(q["correct_answer"]).upper():
                wrong_questions.append((qid_to_number[q["id"]], q["question_text"]))

        for q_no, q_text in wrong_questions:
            ws_wrong.append([row["student_name"], row["reg_number"], row["section"], q_no, q_text])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"test_{test_id}_results_report.xlsx",
    )


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

        questions = conn.execute(
            """
            SELECT id, question_text, correct_answer
            FROM questions
            WHERE test_id = ?
            ORDER BY id ASC
            """,
            (test_id,),
        ).fetchall()
        qid_to_number = {row["id"]: idx + 1 for idx, row in enumerate(questions)}

        rows = conn.execute(
            """
            SELECT
                id,
                student_name,
                reg_number,
                section,
                score,
                tab_switch_count,
                time_taken,
                submitted_at,
                answers
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

    # Wrong answers section (name + question number + question text they got wrong)
    pdf.setFont("Helvetica-Bold", 12)
    if y < 200:
        pdf.showPage()
        y = 810
    pdf.drawString(40, y, "Wrong Answers (Per Candidate)")
    y -= 16
    pdf.setFont("Helvetica", 9)

    any_wrong = False
    for row in rows:
        try:
            answers = json.loads(row["answers"]) if row["answers"] else {}
        except Exception:
            answers = {}

        wrong_questions = []
        for q in questions:
            selected = str(answers.get(str(q["id"]), "")).upper()
            if selected != str(q["correct_answer"]).upper():
                wrong_questions.append((qid_to_number[q["id"]], q["question_text"]))

        if not wrong_questions:
            continue
        any_wrong = True

        if y < 70:
            pdf.showPage()
            y = 810
            pdf.setFont("Helvetica", 9)

        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(40, y, f"{row['student_name']} ({row['reg_number']})")
        y -= 12
        pdf.setFont("Helvetica", 9)

        for q_no, q_text in wrong_questions:
            line = f"Q{q_no}: {q_text}"
            wrapped = textwrap.wrap(line, width=95) or [line]
            for wline in wrapped:
                if y < 50:
                    pdf.showPage()
                    y = 810
                    pdf.setFont("Helvetica", 9)
                pdf.drawString(50, y, wline)
                y -= 11

        y -= 6

    if not any_wrong:
        if y < 80:
            pdf.showPage()
            y = 810
        pdf.drawString(40, y, "No wrong answers found for any candidate.")

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
