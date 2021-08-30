"""Define error handlers for flask."""

from flask import render_template

from autobidsportal.models import db


def bad_request(_):
    """400 error template."""
    return render_template("400.html"), 400


def not_found_error(_):
    """404 error template."""
    return render_template("404.html"), 404


def internal_error(_):
    """500 error template."""
    db.session.rollback()
    return render_template("500.html"), 500
