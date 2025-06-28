import os
import sys

# Ensure local imports work when run directly
sys.path.append(os.path.dirname(__file__))

from web_dashboard import app

if __name__ == "__main__":
    app.run(port=8000)


DB_NAME = "patient_responses.db"

def get_available_tables(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [row[0] for row in cursor.fetchall() if row[0].startswith("responses_")]

def get_all_patient_ids(conn, tables):
    cursor = conn.cursor()
    union_query = " UNION ".join([f"SELECT DISTINCT patient_id FROM {table}" for table in tables])
    cursor.execute(f"SELECT DISTINCT patient_id FROM ({union_query})")
    return [str(row[0]) for row in cursor.fetchall()]

def plot_data_for_table(patient_id, conn, table_name):
    """Return a matplotlib figure for the given patient's data."""
    cur = conn.cursor()
    cols = [row[1] for row in cur.execute(f"PRAGMA table_info({table_name})")]
    if "score" not in cols:
        return None

    q_col = None
    for possible in ("question_title", "question_text", "dimension"):
        if possible in cols:
            q_col = possible
            break
    if not q_col:
        return None

    cur.execute(
        f"SELECT {q_col}, score FROM {table_name} WHERE patient_id = ?",
        (patient_id,),
    )
    rows = cur.fetchall()

    fig, ax = plt.subplots(figsize=(9, 5))
    if not rows:
        ax.text(0.5, 0.5, f"No data found for {table_name}", ha="center", va="center")
        ax.axis("off")
        return fig

    labels = [str(r[0])[:40] for r in rows]
    scores = [r[1] for r in rows]

    ax.bar(labels, scores, color="skyblue")
    ax.set_title(table_name.replace("responses_", "").upper())
    ax.set_ylabel("Score")
    ax.tick_params(axis="x", labelrotation=90)
    ax.grid(True, axis="y", linestyle="--", alpha=0.7)
    plt.tight_layout()
    return fig

def launch_gui():
    conn = sqlite3.connect(DB_NAME)
    tables = get_available_tables(conn)
    patient_ids = get_all_patient_ids(conn, tables)

    root = tk.Tk()
    root.title("Patient Results Dashboard")
    root.geometry("1200x800")

    selected_id = tk.StringVar()
    ttk.Label(root, text="Select Patient ID:").pack(pady=5)
    dropdown = ttk.Combobox(root, textvariable=selected_id, values=patient_ids, state="readonly")
    dropdown.pack(pady=5)

    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True)

    def on_id_selected(event=None):
        for tab in notebook.tabs():
            notebook.forget(tab)

        for table in tables:
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=table.replace("responses_", "").upper())

            fig = plot_data_for_table(selected_id.get(), conn, table)
            if fig is None:
                ttk.Label(frame, text="No numeric data available").pack(pady=20)
                continue
            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    dropdown.bind("<<ComboboxSelected>>", on_id_selected)

    root.mainloop()

if __name__ == "__main__":
    launch_gui()

