# MDD_Diagnosis

## Running the HTTP server


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


