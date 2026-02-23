import csv
import io
import os
import sqlite3
import tempfile

from openpyxl import Workbook

EXPORT_TABLES = ("videos", "channels", "channel_videos", "channel_history")
DB_FETCH_CHUNK_SIZE = 1000
DB_PATH = os.path.join(os.path.dirname(__file__), "videos.db")


def open_videos_db_connection():
    return sqlite3.connect(DB_PATH)


def iter_table_csv(conn, table_name):
    cursor = conn.execute(f"SELECT * FROM {table_name}")
    columns = [description[0] for description in cursor.description]

    buffer = io.StringIO()
    writer = csv.writer(buffer)

    writer.writerow(columns)
    yield buffer.getvalue()
    buffer.seek(0)
    buffer.truncate(0)

    while True:
        rows = cursor.fetchmany(DB_FETCH_CHUNK_SIZE)
        if not rows:
            break

        writer.writerows(rows)
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)


def stream_all_tables_csv():
    conn = sqlite3.connect(DB_PATH)

    try:
        for table_name in EXPORT_TABLES:
            yield f"=== {table_name.upper()} ===\n"
            yield from iter_table_csv(conn, table_name)
            yield "\n"
    finally:
        conn.close()


def build_xlsx_export_file():
    conn = sqlite3.connect(DB_PATH)
    workbook = Workbook(write_only=True)

    try:
        for table_name in EXPORT_TABLES:
            sheet = workbook.create_sheet(title=table_name[:31])
            cursor = conn.execute(f"SELECT * FROM {table_name}")
            columns = [description[0] for description in cursor.description]
            sheet.append(columns)

            while True:
                rows = cursor.fetchmany(DB_FETCH_CHUNK_SIZE)
                if not rows:
                    break
                for row in rows:
                    sheet.append(row)

        temp_file = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        temp_file_path = temp_file.name
        temp_file.close()
        workbook.save(temp_file_path)
        return temp_file_path
    finally:
        conn.close()
