import sqlite3
from pathlib import Path
import ctypes.wintypes  # Only applies for Windows
import os
from contants.queries import Queries


class DatabaseService:
    def __init__(self):
        self.db_path = self._get_database_path()
        self._ensure_directories()
        self._ensure_database()

    def _get_documents_path(self):
        """Get Windows 'Documents' folder using SHGetKnownFolderPath"""
        try:
            from ctypes import windll, POINTER, byref
            from uuid import UUID
            SHGetKnownFolderPath = windll.shell32.SHGetKnownFolderPath
            SHGetKnownFolderPath.argtypes = [
                ctypes.POINTER(ctypes.c_byte), ctypes.wintypes.DWORD,
                ctypes.wintypes.HANDLE, ctypes.POINTER(ctypes.c_wchar_p)
            ]
            FOLDERID_Documents = UUID('{FDD39AD0-238F-46AF-ADB4-6C85480369C7}')
            path_ptr = ctypes.c_wchar_p()
            SHGetKnownFolderPath(
                (ctypes.c_byte * 16).from_buffer_copy(FOLDERID_Documents.bytes_le),
                0, 0, byref(path_ptr)
            )
            return Path(path_ptr.value)
        except Exception as e:
            print("Error getting Documents path, falling back to home/Documents:", e)
            return Path.home() / "Documents"

    def _get_database_path(self) -> Path:
        documents_dir = self._get_documents_path()
        db_dir = documents_dir / "DrCamApp" / "databases"
        return db_dir / "AppDb.db"

    def _ensure_directories(self):
        db_dir = self.db_path.parent
        db_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_database(self):
        if not self.db_path.exists():
            print(f"Database not found. Initializing schema at {self.db_path}")
            self.initialize_schema()
        else:
            print(f"Database exists: {self.db_path}")
            self.migrate_schema()  # ✅ Added schema migration step

    def get_connection(self):
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize_schema(self):
        self._ensure_directories()
        conn = self.get_connection()
        cursor = conn.cursor()
        queries = [
            Queries.CREATE_USER,
            Queries.DOCTOR_PROFILE,
            Queries.PATIENTS,
            Queries.PATIENT_HISTORY,
            Queries.PATIENT_IMAGES,
            Queries.PATIENT_VIDEOS,
            Queries.CAMERA_SETTINGS
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

    def bulk_insert(self, models):
        if not models:
            return

        conn = self.get_connection()
        cursor = conn.cursor()
        table_name = models[0].get_table_name()
        columns = models[0].to_map().keys()
        placeholders = ', '.join(['?'] * len(columns))
        values = [tuple(model.to_map().values()) for model in models]
        query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        cursor.executemany(query, values)
        conn.commit()
        conn.close()

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

    def updatePatient(self, model, key="patientId"):
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

    def custom_query_v1(self, query, args=[]):
        conn = self.get_connection()
        cursor = conn.execute(query, args)
        row = cursor.fetchone()
        conn.close()
        if row is None:
            return 0
        row_dict = dict(row)
        val = list(row_dict.values())[0]
        return val if val is not None else 0

    def get_single_int(self, query, args=[]):
        conn = self.get_connection()
        cursor = conn.execute(query, args)
        row = cursor.fetchone()
        conn.close()
        return int(row[0]) if row and row[0] is not None else 0



    def migrate_schema(self):
        """Perform schema updates like adding missing columns."""
        conn = self.get_connection()
        try:
            self.add_column_if_missing(conn, "patient_images", "comment", "TEXT")
            self.add_column_if_missing(conn, "camera_settings", "rotation_angle", "INTEGER")
        except Exception as e:
            print(f"Migration failed: {e}")
        finally:
            conn.close()

    def column_exists(self, conn, table: str, column: str) -> bool:
        """Check if a column exists in a given table."""
        cursor = conn.execute(f"PRAGMA table_info({table})")
        return any(row["name"] == column for row in cursor.fetchall())

    def add_column_if_missing(self, conn, table: str, column: str, coltype: str):
        """Safely add a column to a table if it doesn't already exist."""
        if not self.column_exists(conn, table, column):
            print(f"Adding missing column '{column}' to table '{table}'")
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")
            conn.commit()
        else:
            print(f"Column '{column}' already exists in table '{table}'")
