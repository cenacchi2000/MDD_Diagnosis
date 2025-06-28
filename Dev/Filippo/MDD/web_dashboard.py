import sqlite3
import base64
import io

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask, render_template_string

DB_NAME = 'patient_responses.db'

app = Flask(__name__)


def get_response_tables(conn):
    """Return all table names that store questionnaire responses."""
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [row[0] for row in cur.fetchall() if row[0].startswith('responses_')]


def get_all_patient_ids(conn, tables):
    """Gather every patient_id appearing in the given tables."""
    if not tables:
        return []
    cur = conn.cursor()
    union_query = ' UNION '.join([f"SELECT patient_id FROM {t}" for t in tables])
    cur.execute(f"SELECT DISTINCT patient_id FROM ({union_query}) AS ids")
    return [str(row[0]) for row in cur.fetchall() if row[0] is not None]


def plot_data_for_table(patient_id, conn, table_name):
    """Generate a base64-encoded bar chart for a patient's data in table."""
    cur = conn.cursor()
    cols = [row[1] for row in cur.execute(f"PRAGMA table_info({table_name})")]
    if 'score' not in cols:
        return None
    q_col = next((c for c in ('question_title','question_text','dimension') if c in cols), None)
    if not q_col:
        return None
    cur.execute(
        f"SELECT {q_col}, score FROM {table_name} WHERE patient_id=?",
        (patient_id,)
    )
    rows = cur.fetchall()

    fig, ax = plt.subplots(figsize=(9,5))
    if rows:
        labels = [str(r[0])[:40] for r in rows]
        scores = [r[1] for r in rows]
        ax.bar(labels, scores, color='#0d6efd')
        ax.set_ylabel('Score')
        ax.set_title(table_name.replace('responses_','').upper())
        ax.tick_params(axis='x', labelrotation=90)
        ax.grid(True, axis='y', linestyle='--', alpha=0.7)
    else:
        ax.text(0.5,0.5,'No data', ha='center', va='center')
        ax.axis('off')
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

INDEX_TEMPLATE = """<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'>
  <title>Patient Dashboard</title>
</head>
<body class='bg-light'>
<nav class='navbar navbar-dark bg-primary mb-4'>
  <div class='container'>
    <span class='navbar-brand mb-0 h1'>Patient Dashboard</span>
  </div>
</nav>
<div class='container'>
  <h2 class='mb-3'>Select a patient</h2>
  <ul class='list-group'>
  {% for pid in patient_ids %}
    <li class='list-group-item'><a href='/patient/{{ pid }}' class='text-decoration-none'>{{ pid }}</a></li>
  {% else %}
    <li class='list-group-item'>No patients found.</li>
  {% endfor %}
  </ul>
</div>
</body>
</html>"""

PATIENT_TEMPLATE = """<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'>
  <title>Results for {{ patient_id }}</title>
</head>
<body class='bg-light'>
<nav class='navbar navbar-dark bg-primary mb-4'>
  <div class='container'>
    <a class='navbar-brand' href='/'>Patient Dashboard</a>
  </div>
</nav>
<div class='container'>
  <h2 class='mb-4'>Results for {{ patient_id }}</h2>
  {% if images %}
    {% for table, img in images.items() %}
    <div class='card mb-4'>
      <div class='card-header fw-bold'>{{ table.replace('responses_', '').upper() }}</div>
      <div class='card-body text-center'>
        <img class='img-fluid' src='data:image/png;base64,{{ img }}' alt='{{ table }}'>
      </div>
    </div>
    {% endfor %}
  {% else %}
    <p>No results found.</p>
  {% endif %}
  <a class='btn btn-secondary' href='/'>Back</a>
</div>
</body>
</html>"""

@app.route('/')
def index():
    conn = sqlite3.connect(DB_NAME)
    tables = get_response_tables(conn)
    patient_ids = get_all_patient_ids(conn, tables)
    conn.close()
    return render_template_string(INDEX_TEMPLATE, patient_ids=patient_ids)


@app.route('/patient/<pid>')
def patient(pid):
    conn = sqlite3.connect(DB_NAME)
    tables = get_response_tables(conn)
    images = {}
    for table in tables:
        img = plot_data_for_table(pid, conn, table)
        if img:
            images[table] = img
    conn.close()
    return render_template_string(PATIENT_TEMPLATE, patient_id=pid, images=images)


if __name__ == '__main__':
    app.run(port=8000)
