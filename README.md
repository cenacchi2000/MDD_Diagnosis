# MDD_Diagnosis

## Running the HTTP server


Patient questionnaire results can be stored remotely using
`Dev/Filippo/MDD/http_server.py`.  The script uses only Python's built-in
modules and writes incoming data to `patient_responses.db` in the current
directory.

```bash
python Dev/Filippo/MDD/http_server.py
```


The server listens on port `5000` and automatically creates the database file if
it does not already exist.

## Configuring `SERVER_URL`

Questionnaire modules send data to the URL specified by the `SERVER_URL`
environment variable (default: `http://localhost:5000/store`).  Before running a
client script, set this variable to point at the server location:

```bash
export SERVER_URL="http://<server-ip>:5000/store"
```

Replace `<server-ip>` with the address of the machine where `http_server.py` is
running.

## Verifying stored data

After running the assessments, confirm that the responses were saved by querying
`patient_responses.db`:


```bash
sqlite3 patient_responses.db ".tables"
sqlite3 patient_responses.db "SELECT * FROM patient_demographics LIMIT 5;"
```

This will list the created tables such as `patient_demographics` and
`responses_bdi`.  You can inspect table contents with standard SQLite commands
to ensure that data was recorded.

## Web dashboard


You can view interactive charts of questionnaire results using a small Flask
web dashboard.  The app reads from the same `patient_responses.db` database
created by `http_server.py` and groups results by `patient_id`.

```bash
pip install flask

python Dev/Filippo/MDD/web_dashboard.py
```

Visit `http://localhost:8000` in your browser.  The landing page lists all
patients with stored responses.  Selecting an ID shows one plot per questionnaire
containing numeric scores.  Reload the page after new assessments to view the
latest results.

You can also launch the same dashboard with `visualize_results.py`, which simply
imports the dashboard app and runs it on the default port.

