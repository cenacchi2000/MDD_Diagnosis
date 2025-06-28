
import json
import re
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer

DB_NAME = "patient_responses.db"


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

    union_query = " UNION ".join([f"SELECT patient_id FROM {t}" for t in tables])
    cur.execute(f"SELECT DISTINCT patient_id FROM ({union_query}) AS ids")
    return [str(row[0]) for row in cur.fetchall() if row[0] is not None]


def get_data_for_table(patient_id, conn, table_name):
    """Return label and score lists for the given patient and table."""
    cur = conn.cursor()
    cols = [row[1] for row in cur.execute(f"PRAGMA table_info({table_name})")]
    if "score" not in cols:
        return None

    q_col = next((c for c in ("question_title", "question_text", "dimension") if c in cols), None)

    if not q_col:
        return None
    cur.execute(
        f"SELECT {q_col}, score FROM {table_name} WHERE patient_id=?",
        (patient_id,),
    )
    rows = cur.fetchall()
    if not rows:
        return None
    labels = [str(r[0])[:40] for r in rows]
    scores = [r[1] for r in rows]
    return {"labels": labels, "scores": scores}



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
  {patient_list}
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
  <script src='https://cdn.jsdelivr.net/npm/chart.js'></script>
  <title>Results for {patient_id}</title>
</head>
<body class='bg-light'>
<nav class='navbar navbar-dark bg-primary mb-4'>
  <div class='container'>
    <a class='navbar-brand' href='/'>Patient Dashboard</a>
  </div>
</nav>
<div class='container'>
  <h2 class='mb-4'>Results for {patient_id}</h2>
  {chart_divs}
  <a class='btn btn-secondary' href='/'>Back</a>
</div>
<script>

  const patientId = "{patient_id}";
  const charts = {};

  async function fetchData() {
    const resp = await fetch('/api/patient/' + patientId);
    const data = await resp.json();
    Object.entries(data).forEach(([table, d], idx) => {
      const ctx = document.getElementById('chart-' + (idx + 1));
      if (!charts[table]) {
        charts[table] = new Chart(ctx, {
          type: 'bar',
          data: { labels: d.labels, datasets: [{ label: 'Score', data: d.scores, backgroundColor: '#0d6efd' }] },
          options: { responsive: true, scales: { y: { beginAtZero: true } } }
        });
      } else {
        charts[table].data.labels = d.labels;
        charts[table].data.datasets[0].data = d.scores;
        charts[table].update();
      }
    });
  }

  fetchData();
  setInterval(fetchData, 5000);

</script>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ('/', '/index.html'):
            self.send_index()
        else:
            m = re.match(r'^/patient/(.+)$', self.path)
            if m:
                self.send_patient(m.group(1))

                return
            m = re.match(r'^/api/patient/(.+)$', self.path)
            if m:
                self.send_patient_api(m.group(1))
                return
            self.send_response(404)
            self.end_headers()


    def _write_html(self, html: str) -> None:
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def send_index(self):
        conn = sqlite3.connect(DB_NAME)
        tables = get_response_tables(conn)
        patient_ids = get_all_patient_ids(conn, tables)
        conn.close()
        if patient_ids:
            items = '\n'.join(
                f"<li class='list-group-item'><a class='text-decoration-none' href='/patient/{pid}'>{pid}</a></li>"
                for pid in patient_ids
            )
        else:
            items = "<li class='list-group-item'>No patients found.</li>"
        html = INDEX_TEMPLATE.format(patient_list=items)
        self._write_html(html)

    def send_patient(self, patient_id: str):
        conn = sqlite3.connect(DB_NAME)
        tables = get_response_tables(conn)
        charts = {}
        for table in tables:
            data = get_data_for_table(patient_id, conn, table)
            if data:
                charts[table] = data
        conn.close()
        if charts:
            divs = ''
            for idx, table in enumerate(charts, start=1):
                label = table.replace('responses_', '').upper()
                divs += (
                    "<div class='card mb-4'>"
                    f"<div class='card-header fw-bold'>{label}</div>"
                    "<div class='card-body'>"
                    f"<canvas id='chart-{idx}'></canvas>"
                    "</div></div>"
                )
        else:
            divs = "<p>No results found.</p>"
        html = PATIENT_TEMPLATE.format(
            patient_id=patient_id,
            chart_divs=divs,
            charts_json=json.dumps(charts),
        )
        self._write_html(html)


    def send_patient_api(self, patient_id: str):
        conn = sqlite3.connect(DB_NAME)
        tables = get_response_tables(conn)
        charts = {}
        for table in tables:
            data = get_data_for_table(patient_id, conn, table)
            if data:
                charts[table] = data
        conn.close()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(charts).encode('utf-8'))



def run(port: int = 8000) -> None:
    """Start the dashboard server on the given port."""
    server = HTTPServer(('0.0.0.0', port), DashboardHandler)
    print(f"Dashboard listening on http://localhost:{port}")
    server.serve_forever()


if __name__ == '__main__':
    run()

