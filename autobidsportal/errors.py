"""Define error handlers for flask."""

from flask import render_template

from autobidsportal import app, db


@app.errorhandler(404)
def not_found_error(_):
    """404 error template."""
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(_):
    """500 error template."""
    db.session.rollback()
    return render_template("500.html"), 500
