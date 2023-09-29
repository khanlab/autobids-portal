# Autobids Portal

This is a webapp for interacting with the autobids system.

# Setup

## Non-python requirements

To use all functionality, you will need:

- Apptainer, with the following images:
  - docker://khanlab/tar2bids
  - docker://khanlab/cfmm2tar
  - docker://khanlab/gradcorrect (along with a private coefficients file)
- A mail server compatible with Flask-Mail.
- A redis server.
- A PostgreSQL server.
- A git repository containing custom heuristics.

## Installation instructions

1. Set up a virtual environment.
2. `pip install -e .`, or `poetry install` if your environment has poetry.
3. Adjust your configuration by making a copy of `.envtemplate` and changing any relevant variables.
4. Export all necessary environment variables (`set -a && . .env && set +a` does the job if you keep them in a `.env` file).
5. Set up the db: `flask db upgrade`.

# Running the application

## Local/Development

The easiest way to get a local development system running is to use docker compose.

1. `docker-compose up --build`
2. The first time and after any DB model changes, run your migrations by sshing into the `autobidsportal` container (`docker -it exec {container_id} /bin/bash`) and running `flask db upgrade`.
3. The ssh setup for archiving between containers in docker-compose can be a little finnicky. If those steps fail, this is a first place to look. Usually sshing into the relevant containers and running `ssh-keyscan` and friends can help resolve this.

## Production

- A [production server](https://flask.palletsprojects.com/en/2.0.x/deploying/) (i.e. not the Flask development server invoked with `flask run`) should be used to serve the autobids portal.
- A [service manager](https://python-rq.org/patterns/) should also be used to manage the rq workers that execute asynchronous tasks.
- The operational CLI commands (i.e. `flask check_pis`, `flask run-all-cfmm2tar`, etc.) should be run on a regular basis: See `crontab.example` for an example of how this can be configured.
