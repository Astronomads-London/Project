# Project

Install dependencies with `pip install -r requirements.txt` and set `MONGODB_URI`
in the project root `.env` file or the process environment. The process
environment takes precedence. Do not commit credentials.

Run `python -m app.db` to connect and create the `App` database and `Users`
collection if needed. For MongoDB Atlas, the cluster must be running and its
network access settings must allow the connecting IP address.