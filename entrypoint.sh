#!/bin/bash

# Set to exit on error
set -e

# Functions
ssh_known_hosts() {
    # This causes problems if run as part of docker compose, but keeping this 
    # in here as a hint for what to run
    echo "Gathering public ssh keys of services..."
    ssh-keyscan -p 2222 archive >> /etc/ssh/ssh_known_hosts
    ssh-keyscan -p 2222 ria >> /etc/ssh/ssh_known_hosts
    echo "Finished gathering keys."
}


flask_db() {
    # Upgrade db task
    echo "Upgrading flask database..."
    flask db upgrade -d /usr/local/lib/python3.9/dist-packages/autobidsportal_migrations/
    echo "Completed database upgrade."
}


init() {
    # Init web app task
    echo "+----------------------------+"
    echo "| Starting autobidsportal... |"
    echo "+----------------------------+"
    uwsgi --ini=autobidsportal.ini
}


# Main body of code
flask_db
init