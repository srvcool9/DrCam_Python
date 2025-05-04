import sqlite3
from pathlib import Path

from src.contants.queries import Queries


class DatabaseService:
    def __init__(self):
        self.db_path = self._get_database_path()
        self.ensure_directories()
        self.initialize_schema()

    def _get_database_path(self) -> Path:
        documents_dir = Path.home() / "Documents"
        db_dir = documents_dir / "DrCamApp" / "databases"
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir / "AppDb.db"

    def ensure_directories(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize_schema(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        queries = [
            Queries.CREATE_USER,
            Queries.DOCTOR_PROFILE,
            Queries.PATIENTS,
            Queries.PATIENT_HISTORY,
            Queries.PATIENT_IMAGES,
            Queries.PATIENT_VIDEOS,
        ]
        for query in queries:
            cursor.execute(query)
        conn.commit()
        conn.close()

    def reset_database(self):
        if self.db_path.exists():
            self.db_path.unlink()
        self.initialize_schema()

    def insert(self, model):
        conn = self.get_connection()
        cursor = conn.cursor()
        placeholders = ', '.join(['?'] * len(model.to_map()))
        query = f"INSERT INTO {model.get_table_name()} ({', '.join(model.to_map().keys())}) VALUES ({placeholders})"
        cursor.execute(query, tuple(model.to_map().values()))
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id

    def update(self, model, key="id"):
        conn = self.get_connection()
        cursor = conn.cursor()
        data = model.to_map()
        fields = ', '.join([f"{k}=?" for k in data if k != key])
        query = f"UPDATE {model.get_table_name()} SET {fields} WHERE {key} = ?"
        cursor.execute(query, [data[k] for k in data if k != key] + [data[key]])
        conn.commit()
        rowcount = cursor.rowcount
        conn.close()
        return rowcount

    def query_all(self, table, from_map):
        conn = self.get_connection()
        cursor = conn.execute(f"SELECT * FROM {table}")
        results = [from_map(dict(row)) for row in cursor.fetchall()]
        conn.close()
        return results

    def query_by_column(self, table, column, value, from_map):
        conn = self.get_connection()
        cursor = conn.execute(f"SELECT * FROM {table} WHERE {column} = ? LIMIT 1", (value,))
        row = cursor.fetchone()
        conn.close()
        return from_map(dict(row)) if row else None

    def custom_query(self, query, from_map, args=[]):
        conn = self.get_connection()
        cursor = conn.execute(query, args)
        results = [from_map(dict(row)) for row in cursor.fetchall()]
        conn.close()
        return results

    def get_single_int(self, query, args=[]):
        conn = self.get_connection()
        cursor = conn.execute(query, args)
        row = cursor.fetchone()
        conn.close()
        return int(row[0]) if row and row[0] is not None else 0
