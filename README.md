# Autobids Portal

This is a webapp for interacting with the autobids system.

# Setup

## Non-python requirements

Some functionality will not be available without a local installation of `dcm4che`, either natively or through a container.

## Installation instructions

1. Set up a virtual environment.
2. `pip install -e .`.
3. Adjust your configuration as necessary by making a copy of `defaultconfig.py` and making any changes.
4. Export all necessary environment variables (see `.envtemplate`), including pointing to your local configuration file.
5. Set up the db: `flask db upgrade`.
