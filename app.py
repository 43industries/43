from __future__ import annotations

import json
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

import requests
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-me-in-production")

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "submissions.json"


def load_submissions() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def save_submissions(items: list[dict]) -> None:
    DATA_FILE.write_text(json.dumps(items, indent=2), encoding="utf-8")


def send_contact_email(payload: dict) -> None:
    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    to_addr = os.environ.get("CONTACT_TO")

    if not (host and user and password and to_addr):
        # Email not configured; just skip silently.
        return

    msg = EmailMessage()
    msg["Subject"] = f"[43 Industries] New contact: {payload.get('subject')}"
    msg["From"] = user
    msg["To"] = to_addr
    body = (
        f"New contact form submission\n\n"
        f"Name: {payload.get('name')}\n"
        f"Email: {payload.get('email')}\n"
        f"Subject: {payload.get('subject')}\n"
        f"Message:\n{payload.get('message')}\n\n"
        f"Created at: {payload.get('created_at')}"
    )
    msg.set_content(body)

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/xrpl")
def xrpl_page():
    return render_template("xrpl.html")


@app.route("/fund")
def fund_page():
    return render_template("fund.html")


@app.route("/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password", "")
        expected = os.environ.get("ADMIN_PASSWORD", "admin")
        if password == expected:
            session["is_admin"] = True
            return redirect(url_for("admin_dashboard"))
        return render_template("login.html", error="Invalid password")
    return render_template("login.html")


def require_admin() -> bool:
    return bool(session.get("is_admin"))


@app.route("/contact", methods=["POST"])
def contact_submit():
    submissions = load_submissions()
    entry = {
        "id": len(submissions) + 1,
        "name": request.form.get("name", "").strip(),
        "email": request.form.get("email", "").strip(),
        "subject": request.form.get("subject", "").strip(),
        "message": request.form.get("message", "").strip(),
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    submissions.append(entry)
    save_submissions(submissions)

    try:
        send_contact_email(entry)
    except Exception:
        # Avoid breaking the UX if email fails.
        pass
    flash("Thanks, your message has been received.")
    return redirect(url_for("home"))


@app.route("/fund/interest", methods=["POST"])
def fund_interest():
    path = BASE_DIR / "fund_leads.json"
    if path.exists():
        try:
            leads = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            leads = []
    else:
        leads = []

    leads.append(
        {
            "name": request.form.get("name", "").strip(),
            "email": request.form.get("email", "").strip(),
            "ticket": request.form.get("ticket", "").strip(),
            "notes": request.form.get("notes", "").strip(),
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
    )
    path.write_text(json.dumps(leads, indent=2), encoding="utf-8")
    flash("Thanks for your interest. We’ll follow up directly.")
    return redirect(url_for("fund_page"))


@app.route("/admin")
def admin_dashboard():
    if not require_admin():
        return redirect(url_for("admin_login"))
    submissions = list(reversed(load_submissions()))
    return render_template("admin.html", submissions=submissions)


@app.route("/api/submissions")
def api_submissions():
    return jsonify(load_submissions())


@app.route("/admin/delete/<int:submission_id>", methods=["POST"])
def delete_submission(submission_id: int):
    if not require_admin():
        return redirect(url_for("admin_login"))
    submissions = load_submissions()
    submissions = [s for s in submissions if int(s.get("id", 0)) != submission_id]
    save_submissions(submissions)
    return redirect(url_for("admin_dashboard"))


@app.route("/xrpl/address", methods=["GET", "POST"])
def xrpl_address():
    data = None
    error = None
    address = ""
    if request.method == "POST":
        address = request.form.get("address", "").strip()
        if address:
            try:
                resp = requests.get(
                    f"https://api.xrpscan.com/api/v1/account/{address}", timeout=5
                )
                if resp.status_code == 200:
                    data = resp.json()
                else:
                    error = "Address not found or XRPL API error."
            except Exception:
                error = "Unable to reach XRPL API right now."
        else:
            error = "Please enter an address."
    return render_template("xrpl_address.html", data=data, error=error, address=address)


if __name__ == "__main__":
    app.run(debug=True)

