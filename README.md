# MDD_Diagnosis

## Running the HTTP server

Patient questionnaire results can be stored remotely using
`Dev/Filippo/MDD/http_server.py`.  The server relies on Flask and writes all
incoming data to `patient_responses.db` in the current directory.

```bash
pip install flask
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

You can view basic plots of questionnaire results using a small Flask app.  It
reads from the same `patient_responses.db` file created by `http_server.py` and
presents graphs for each patient.

```bash
pip install flask pandas matplotlib
python Dev/Filippo/MDD/visualize_web.py
```

Visit `http://localhost:8000` in your browser to choose a patient ID and see the
corresponding charts.  Reloading the page will show newly stored results.
