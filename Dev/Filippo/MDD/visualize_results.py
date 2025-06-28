import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk

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
    query = f"SELECT question_title, score FROM {table_name} WHERE patient_id = ?"
    df = pd.read_sql_query(query, conn, params=(patient_id,))
    
    fig, ax = plt.subplots(figsize=(9, 5))
    if df.empty:
        ax.text(0.5, 0.5, f"No data found for {table_name}", ha='center', va='center')
        return fig

    df['question_title'] = df['question_title'].str[:40]  # Trim long titles
    ax.bar(df['question_title'], df['score'], color='skyblue')
    ax.set_title(table_name.replace("responses_", "").upper())
    ax.set_ylabel("Score")
    ax.tick_params(axis='x', labelrotation=90)
    ax.grid(True, axis='y', linestyle='--', alpha=0.7)
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
            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    dropdown.bind("<<ComboboxSelected>>", on_id_selected)

    root.mainloop()

if __name__ == "__main__":
    launch_gui()
