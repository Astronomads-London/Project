# Project

Install dependencies with `pip install -r requirements.txt` and set `MONGODB_URI`
in the project root `.env` file or the process environment. The process
environment takes precedence. Do not commit credentials.

Run `python -m app.db` to connect and create the `App` database and `Users`
collection if needed. For MongoDB Atlas, the cluster must be running and its
network access settings must allow the connecting IP address.

## Flight surgeon accounts

The sign-up form has an Astronaut / Flight surgeon switch. Astronauts sign up
with `INVITE_CODE` and their health profile; flight surgeons sign up with
`SURGEON_INVITE_CODE` and only a username and password. Set both codes in
`.env` and keep them different (a flight surgeon code identical to the
astronaut code is refused). Flight surgeons log in on the normal
login page and land on `/surgeon`, which lists every astronaut with any
readings flagged in the last seven days. Selecting an astronaut shows their
profile, charts, PVT results and self-reported data.

Flight surgeons write treatment instructions for an astronaut on
`/surgeon/treatment`. Each astronaut has one conversation shared by all flight
surgeons, stored in the `Messages` collection; the astronaut reads it and
replies on `/messages`. The latest messages also appear on both dashboards.

## Brief Psychomotor Vigilance Test

Authenticated participants can open the three-minute PVT-B from the dashboard.
The test requests fullscreen when started, presents a running counter after a
random 0–3000 ms foreperiod, and records response timing in the browser with a
monotonic clock. Completed trials and derived metrics are saved in the MongoDB
`PVTResults` collection.

Responses during the blank foreperiod count as commissions; responses under
100 ms are false starts, responses over 500 ms are lapses, and no response
within 30 seconds is an omission (also counted as a lapse). The final trial is
marked truncated if the three-minute session ends before it resolves. Summary
metrics include average response time, lapse/omission/commission/false-start
counts, overall performance, and reciprocal reaction-time measures. These
results are observational and are not a medical assessment.