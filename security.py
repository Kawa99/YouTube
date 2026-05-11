import hmac
import os

from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

EXEMPT_ENDPOINTS = {
    "login",
    "healthz",
    "static",
}


def register_security(app):
    app.config["ADMIN_AUTH_ENABLED"] = _auth_enabled()

    @app.before_request
    def require_admin_auth():
        if not app.config["ADMIN_AUTH_ENABLED"]:
            return None
        endpoint = request.endpoint or ""
        if endpoint in EXEMPT_ENDPOINTS or endpoint.startswith("static"):
            return None
        if session.get("admin_authenticated") is True:
            return None
        return redirect(url_for("login", next=_safe_next(request.full_path)))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if not app.config["ADMIN_AUTH_ENABLED"]:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            if _valid_password(request.form.get("password", "")):
                session["admin_authenticated"] = True
                return redirect(
                    _safe_next(request.form.get("next")) or url_for("dashboard")
                )
            flash("Invalid admin password.", "warning")
        return render_template(
            "login.html", next_url=_safe_next(request.args.get("next"))
        )

    @app.route("/logout", methods=["POST"])
    def logout():
        session.pop("admin_authenticated", None)
        return redirect(url_for("login"))


def _auth_enabled():
    return bool(
        os.environ.get("ADMIN_PASSWORD") or os.environ.get("ADMIN_PASSWORD_HASH")
    )


def _valid_password(candidate):
    password_hash = os.environ.get("ADMIN_PASSWORD_HASH")
    if password_hash:
        return check_password_hash(password_hash, candidate)
    password = os.environ.get("ADMIN_PASSWORD", "")
    return bool(password) and hmac.compare_digest(candidate, password)


def _safe_next(value):
    if not value:
        return None
    value = str(value)
    if not value.startswith("/") or value.startswith("//"):
        return None
    return value
