"""Audit log for write-tool approvals.

Every decision is recorded BEFORE the tool runs. This is what makes the
Phase 4 safety assertion checkable:

    no write tool ever executes without a matching 'approved' row.

Same SQLite file as short-term memory -- one database to inspect.
"""
import os
import json
import sqlite3
from datetime import datetime


def _db_path():
    return os.environ.get('CHAT_DB', 'chat_memory.db')


def _connect():
    return sqlite3.connect(_db_path())


def init_approvals_db():
    connection = _connect()
    cursor = connection.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS approval_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT,
    thread_id TEXT,
    tool_call_id TEXT,
    tool_name TEXT,
    arguments TEXT,
    decision TEXT,
    timestamp TEXT
    )''')
    connection.commit()
    connection.close()


def record_decision(chat_id, thread_id, tool_call_id, tool_name,
                    arguments, decision):
    """Write one decision row. `decision` is 'approved' or 'cancelled'."""
    connection = _connect()
    cursor = connection.cursor()
    cursor.execute(
        'INSERT INTO approval_events '
        '(chat_id, thread_id, tool_call_id, tool_name, arguments, decision, timestamp) '
        'VALUES (?,?,?,?,?,?,?)',
        (chat_id, thread_id, tool_call_id, tool_name,
         json.dumps(arguments, default=str), decision,
         datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
    )
    connection.commit()
    connection.close()


def get_approvals(thread_id=None):
    connection = _connect()
    cursor = connection.cursor()
    if thread_id:
        rows = cursor.execute(
            'SELECT * FROM approval_events WHERE thread_id = ? ORDER BY event_id DESC',
            (thread_id,)).fetchall()
    else:
        rows = cursor.execute(
            'SELECT * FROM approval_events ORDER BY event_id DESC').fetchall()
    connection.close()
    return rows