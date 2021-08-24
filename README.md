# Autobids Portal

This is a webapp for interacting with the autobids system.

# Setup

## Non-python requirements

To use all functionality, you will need:

- `dcm4che` and `tar2bids` installed, either natively or through a container.
- A mail server compatible with Flask-Mail.
- A redis server.

## Installation instructions

1. Set up a virtual environment.
2. `pip install -e .`.
3. Adjust your configuration by making a copy of `defaultconfig.py` and changing any relevant config variables.
4. Export all necessary environment variables (see `.envtemplate` for a full listing), including `FLASK_APP=bids_form.py` and `AUTOBIDSPORTAL_CONFIG={configfile}.Config`.
5. Set up the db: `flask db upgrade`.

# Running the application

## Local/Development

1. Ensure your configured redis server is running.
2. In a separate terminal, activate your virtual environment and run `rq worker` from the project root.
3. `flask run`

## Production

- A [production server](https://flask.palletsprojects.com/en/2.0.x/deploying/) (i.e. not the Flask development server invoked with `flask run`) should be used to serve the autobids portal.
- A [service manager](https://python-rq.org/patterns/) should also be used to manage the rq workers that execute asynchronous tasks.
- The `check_pis` CLI command (i.e. `flask check_pis`) should be run on a regular basis: See `crontab.example` for an example of how this can be configured.
