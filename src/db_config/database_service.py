import os
import sqlite3
from pathlib import Path
from datetime import datetime

from src.contants.queries import Queries


class DatabaseService:
    _connection = None

    def __init__(self):
        self.db_path = self._get_database_path()
        self.ensure_directories()
        self.connect()
        self.initialize_schema()

    def _get_database_path(self) -> Path:
        documents_dir = Path.home() / "Documents"
        db_dir = documents_dir / "DrCamApp" / "databases"
        db_dir.mkdir(parents=True, exist_ok=True)

        db_path = db_dir / "AppDb.db"
        return db_path

    def ensure_directories(self):
        db_dir = self.db_path.parent
        db_dir.mkdir(parents=True, exist_ok=True)

    def connect(self):
        if not self._connection:
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row

    def get_connection(self):
        return self._connection

    def initialize_schema(self):
        cursor = self._connection.cursor()
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
        self._connection.commit()

    def reset_database(self):
        if self._connection:
            self._connection.close()
            self._connection = None
        if self.db_path.exists():
            self.db_path.unlink()
        self.connect()
        self.initialize_schema()

    def insert(self, model):
        conn = self.get_connection()
        cursor = conn.cursor()
        placeholders = ', '.join(['?'] * len(model.to_map()))
        query = f"INSERT INTO {model.get_table_name()} ({', '.join(model.to_map().keys())}) VALUES ({placeholders})"
        cursor.execute(query, tuple(model.to_map().values()))
        conn.commit()
        return cursor.lastrowid

    def update(self, model, key="id"):
        conn = self.get_connection()
        cursor = conn.cursor()
        data = model.to_map()
        fields = ', '.join([f"{k}=?" for k in data if k != key])
        query = f"UPDATE {model.get_table_name()} SET {fields} WHERE {key} = ?"
        cursor.execute(query, [data[k] for k in data if k != key] + [data[key]])
        conn.commit()
        return cursor.rowcount

    def query_all(self, table, from_map):
        conn = self.get_connection()
        cursor = conn.execute(f"SELECT * FROM {table}")
        return [from_map(dict(row)) for row in cursor.fetchall()]

    def query_by_column(self, table, column, value, from_map):
        with sqlite3.connect(self.db_path) as conn:
         conn.row_factory = sqlite3.Row
         cursor = conn.execute(f"SELECT * FROM {table} WHERE {column} = ? LIMIT 1", (value,))
         row = cursor.fetchone()
        return from_map(dict(row)) if row else None

    def custom_query(self, query, from_map, args=[]):
        conn = self.get_connection()
        cursor = conn.execute(query, args)
        return [from_map(dict(row)) for row in cursor.fetchall()]

    def get_single_int(self, query, args=[]):
        conn = self.get_connection()
        cursor = conn.execute(query, args)
        row = cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else 0