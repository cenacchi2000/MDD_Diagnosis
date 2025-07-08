from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import sqlite3

DB_PATH = 'patient_responses.db'

TABLE_SCHEMAS = {
    'patient_demographics': '''
        CREATE TABLE IF NOT EXISTS patient_demographics (
            patient_id TEXT PRIMARY KEY,
            date TEXT,
            name_last TEXT,
            name_first TEXT,
            name_middle TEXT,
            phone TEXT,
            sex TEXT,
            dob TEXT,
            marital_status TEXT,
            education TEXT,
            degree TEXT,
            occupation TEXT,
            spouse_occupation TEXT,
            job_status TEXT,
            diagnosis_time TEXT,
            disease_pain TEXT,
            pain_symptom TEXT,
            surgery TEXT,
            surgery_type TEXT,
            other_pain TEXT,
            pain_med_week TEXT,
            pain_med_daily TEXT
        )''',
    'responses_bdi': '''
        CREATE TABLE IF NOT EXISTS responses_bdi (
            patient_id TEXT,
            timestamp TEXT,
            question_number INTEGER,
            question_title TEXT,
            answer TEXT,
            score INTEGER
        )''',
    'responses_bpi': '''
        CREATE TABLE IF NOT EXISTS responses_bpi (
            patient_id TEXT,
            timestamp TEXT,
            question_number INTEGER,
            question_text TEXT,
            response TEXT
        )''',
    'responses_csi': '''
        CREATE TABLE IF NOT EXISTS responses_csi (
            patient_id TEXT,
            timestamp TEXT,
            question_number INTEGER,
            question_text TEXT,
            answer TEXT,
            score INTEGER
        )''',
    'worksheet_csi': '''
        CREATE TABLE IF NOT EXISTS worksheet_csi (
            patient_id TEXT,
            timestamp TEXT,
            condition TEXT,
            knows_about TEXT,
            diagnosed TEXT,
            year_diagnosed TEXT
        )''',
    'responses_dass21': '''
        CREATE TABLE IF NOT EXISTS responses_dass21 (
            patient_id TEXT,
            timestamp TEXT,
            question_number INTEGER,
            question_text TEXT,
            score INTEGER,
            category TEXT
        )''',
    'responses_eq5d5l': '''
        CREATE TABLE IF NOT EXISTS responses_eq5d5l (
            patient_id TEXT,
            timestamp TEXT,
            dimension TEXT,
            level INTEGER,
            health_state_code TEXT,
            vas_score INTEGER
        )''',
    'responses_odi': '''
        CREATE TABLE IF NOT EXISTS responses_odi (
            patient_id TEXT,
            timestamp TEXT,
            question_number INTEGER,
            question_text TEXT,
            selected_option TEXT,
            score INTEGER
        )''',
    'responses_pcs': '''
        CREATE TABLE IF NOT EXISTS responses_pcs (
            patient_id TEXT,
            timestamp TEXT,
            question_number INTEGER,
            question_text TEXT,
            score INTEGER
        )''',
    'responses_psqi': '''
        CREATE TABLE IF NOT EXISTS responses_psqi (
            patient_id TEXT,
            timestamp TEXT,
            question_number TEXT,
            question_text TEXT,
            answer TEXT,
            score INTEGER
        )''',
    'conversation_history': '''
        CREATE TABLE IF NOT EXISTS conversation_history (
            timestamp TEXT,
            speaker TEXT,
            text TEXT,
            patient_id TEXT,
            id TEXT
        )'''
}

class StoreHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/store':
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8')
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'invalid json')
            return

        table = data.pop('table', None)
        if not table or table not in TABLE_SCHEMAS:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'unknown table')
            return

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(TABLE_SCHEMAS[table])
        columns = ', '.join(data.keys())
        placeholders = ', '.join('?' for _ in data)
        cur.execute(
            f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
            tuple(data.values()),
        )
        conn.commit()
        conn.close()

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'ok')


if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 5000), StoreHandler)
    print('Server listening on port 5000...')
    server.serve_forever()
