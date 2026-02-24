import csv
import io
import tempfile

from openpyxl import Workbook
from sqlalchemy import text

from models import db

EXPORT_TABLES = ("videos", "channels", "channel_videos", "channel_history")
TABLE_SELECT_QUERIES = {
    "videos": "SELECT * FROM videos",
    "channels": "SELECT * FROM channels",
    "channel_videos": "SELECT * FROM channel_videos",
    "channel_history": "SELECT * FROM channel_history",
}
DB_FETCH_CHUNK_SIZE = 1000


def execute_table_query(table_name):
    query = TABLE_SELECT_QUERIES.get(table_name)
    if query is None:
        raise ValueError(f"Unsupported table name: {table_name}")
    return db.session.execute(text(query))


def iter_table_csv(table_name):
    result = execute_table_query(table_name)
    columns = list(result.keys())

    buffer = io.StringIO()
    writer = csv.writer(buffer)

    writer.writerow(columns)
    yield buffer.getvalue()
    buffer.seek(0)
    buffer.truncate(0)

    try:
        while True:
            rows = result.fetchmany(DB_FETCH_CHUNK_SIZE)
            if not rows:
                break

            writer.writerows(tuple(row) for row in rows)
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)
    finally:
        result.close()


def stream_all_tables_csv():
    for table_name in EXPORT_TABLES:
        yield f"=== {table_name.upper()} ===\n"
        yield from iter_table_csv(table_name)
        yield "\n"


def build_xlsx_export_file():
    workbook = Workbook(write_only=True)

    try:
        for table_name in EXPORT_TABLES:
            sheet = workbook.create_sheet(title=table_name[:31])
            result = execute_table_query(table_name)
            columns = list(result.keys())
            sheet.append(columns)

            try:
                while True:
                    rows = result.fetchmany(DB_FETCH_CHUNK_SIZE)
                    if not rows:
                        break
                    for row in rows:
                        sheet.append(tuple(row))
            finally:
                result.close()

        temp_file = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        temp_file_path = temp_file.name
        temp_file.close()
        workbook.save(temp_file_path)
        return temp_file_path
    finally:
        workbook.close()
