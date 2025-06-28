# MDD_Diagnosis

## Running the HTTP server

Questionnaire results are collected by `Dev/Filippo/MDD/http_server.py`.  The
server relies only on the Python standard library and stores incoming data in
`patient_responses.db`.

1. Launch the server:

   ```bash
   python Dev/Filippo/MDD/http_server.py
   ```

   The application listens on port `5000` and creates the SQLite database if it
   does not already exist.

## Configuring `SERVER_URL`

Assessment scripts transmit each response to the URL stored in the
`SERVER_URL` environment variable (default: `http://localhost:5000/store`).  Set
this variable before running a questionnaire so that data reaches the server:

```bash
export SERVER_URL="http://<server-ip>:5000/store"
```

Replace `<server-ip>` with the host running `http_server.py`.

## Verifying stored data

After completing one or more questionnaires, check that the answers were
recorded:

```bash
sqlite3 patient_responses.db ".tables"
sqlite3 patient_responses.db "SELECT * FROM patient_demographics LIMIT 5;"
```

The first command shows all tables created by the server.  You can then run
standard SQLite queries to inspect the contents and confirm that data was saved.

## Patient identifiers

When running `main.py` the system asks for the patient's first and last name and
automatically generates an ID in the format `PAT-xxxxxx`.  If the database
already contains a record with the same first and last name, that existing ID is
reused so repeated visits are linked to the correct patient.  To run any
questionnaire independently you can set the environment variable `patient_id`
before execution.

## Web dashboard

You can view interactive charts of questionnaire results through a small
dashboard script that relies only on Python's standard library. It reads from
the same `patient_responses.db` database created by `http_server.py` and groups
results by `patient_id`.

```bash
python Dev/Filippo/MDD/web_dashboard.py
```

Visit `http://localhost:8000` in your browser.  The landing page lists all
patients with stored responses.  Selecting an ID shows one plot per questionnaire
containing numeric scores.  Reload the page after new assessments to view the
latest results.

You can also launch the same dashboard with `visualize_results.py`, which simply
imports the `run` function and starts the server on the default port.
