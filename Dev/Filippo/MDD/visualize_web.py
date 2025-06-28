import sqlite3
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
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
    cur = conn.cursor()
    union = " UNION ".join([f"SELECT DISTINCT patient_id FROM {t}" for t in tables])
    cur.execute(f"SELECT DISTINCT patient_id FROM ({union})")
    return [str(row[0]) for row in cur.fetchall()]

def plot_data_for_table(patient_id, conn, table_name):
    query = f"SELECT question_title, score FROM {table_name} WHERE patient_id = ?"
    df = pd.read_sql_query(query, conn, params=(patient_id,))
    fig, ax = plt.subplots(figsize=(9, 5))
    if df.empty:
        ax.text(0.5, 0.5, f'No data found for {table_name}', ha='center', va='center')
        ax.axis('off')
    else:
        df['question_title'] = df['question_title'].str[:40]
        ax.bar(df['question_title'], df['score'], color='skyblue')
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
<!DOCTYPE html>
<html>
<head>
    <title>Patient Dashboard</title>
</head>
<body>
<h1>Available Patients</h1>
<ul>
{% for pid in patient_ids %}
  <li><a href="/patient/{{ pid }}">{{ pid }}</a></li>
{% endfor %}
</ul>
</body>
</html>
"""

PATIENT_TPL = """
<!DOCTYPE html>
<html>
<head>
    <title>Results for {{ patient_id }}</title>
</head>
<body>
<h1>Results for {{ patient_id }}</h1>
{% for table, img in images.items() %}
  <h2>{{ table.replace('responses_', '').upper() }}</h2>
  <img src="data:image/png;base64,{{ img }}" alt="{{ table }}">
{% endfor %}
<p><a href="/">Back to patients</a></p>
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
    app.run(port=8000, debug=True)
