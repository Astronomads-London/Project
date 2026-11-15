# Project

Install dependencies with `pip install -r requirements.txt` and set `MONGODB_URI`
in the project root `.env` file or the process environment. The process
environment takes precedence. Do not commit credentials.

Run `python -m app.db` to connect and create the `App` database and `Users`
collection if needed. For MongoDB Atlas, the cluster must be running and its
network access settings must allow the connecting IP address.

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