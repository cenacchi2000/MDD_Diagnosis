import sqlite3

try:  # matplotlib is optional on the robot
    import matplotlib
    matplotlib.use("Agg")  # use non-GUI backend
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover - if matplotlib isn't available
    plt = None

from flask import Flask, render_template_string
import base64
import io

DB_NAME = "patient_responses.db"

app = Flask(__name__)

def get_available_tables(conn):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [row[0] for row in cur.fetchall() if row[0].startswith('responses_')]

def get_all_patient_ids(conn, tables):
    """Return all unique patient IDs across response tables."""
    cur = conn.cursor()
    selects = [f"SELECT patient_id FROM {t}" for t in tables]
    union = " UNION ".join(selects)
    cur.execute(f"SELECT DISTINCT patient_id FROM ({union}) AS all_ids")
    return [str(row[0]) for row in cur.fetchall() if row[0] is not None]

def plot_data_for_table(patient_id, conn, table_name):
    """Create a bar chart for the given patient from the specified table."""
    if plt is None:
        return None
    cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table_name})")]
    if 'score' not in cols:
        return None  # skip tables without numeric scores

    q_col = None
    for possible in ('question_title', 'question_text', 'dimension'):
        if possible in cols:
            q_col = possible
            break
    if q_col is None:
        return None

    cur = conn.cursor()
    cur.execute(
        f"SELECT {q_col}, score FROM {table_name} WHERE patient_id = ?",
        (patient_id,),
    )
    rows = cur.fetchall()

    fig, ax = plt.subplots(figsize=(9, 5))
    if not rows:
        ax.text(0.5, 0.5, f'No data found for {table_name}', ha='center', va='center')
        ax.axis('off')
    else:
        labels = [str(r[0])[:40] for r in rows]
        scores = [r[1] for r in rows]
        ax.bar(labels, scores, color='#0d6efd')
        ax.set_title(table_name.replace('responses_', '').upper())
        ax.set_ylabel('Score')
        ax.tick_params(axis='x', labelrotation=90)
        ax.grid(True, axis='y', linestyle='--', alpha=0.7)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode('utf-8')


INDEX_TPL = """
<!doctype html>
<html lang=\"en\">
<head>
    <meta charset=\"utf-8\">
    <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css\" rel=\"stylesheet\">
    <title>Patient Dashboard</title>
</head>
<body class=\"bg-light\">
<div class="container py-4">
  <h1 class="mb-4">Patient Dashboard</h1>
  <ul class="list-group">
    {% for pid in patient_ids %}
      <li class="list-group-item"><a href="/patient/{{ pid }}">{{ pid }}</a></li>
    {% endfor %}
  </ul>
</div>

</body>
</html>
"""

PATIENT_TPL = """
<!doctype html>
<html lang=\"en\">
<head>
    <meta charset=\"utf-8\">
    <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css\" rel=\"stylesheet\">
    <title>Results for {{ patient_id }}</title>
</head>
<body class=\"bg-light\">
<div class="container py-4">
  <h1 class="mb-4">Results for {{ patient_id }}</h1>
  {% for table, img in images.items() if img %}
    <div class="card mb-4">
      <div class="card-header">{{ table.replace('responses_', '').upper() }}</div>
      <div class="card-body text-center">
        <img class="img-fluid" src="data:image/png;base64,{{ img }}" alt="{{ table }}">
      </div>
    </div>
  {% else %}
    <p>No results found.</p>
  {% endfor %}
  <a class="btn btn-secondary" href="/">Back</a>
</div>

</body>
</html>
"""

@app.route('/')
def index():
    conn = sqlite3.connect(DB_NAME)
    tables = get_available_tables(conn)
    patient_ids = get_all_patient_ids(conn, tables)
    conn.close()
    return render_template_string(INDEX_TPL, patient_ids=patient_ids)

@app.route('/patient/<pid>')
def patient(pid):
    conn = sqlite3.connect(DB_NAME)
    tables = get_available_tables(conn)
    images = {table: plot_data_for_table(pid, conn, table) for table in tables}
    conn.close()
    return render_template_string(PATIENT_TPL, patient_id=pid, images=images)

if __name__ == '__main__':
    app.run(port=8000)
