import sqlite3
import json
import os
from datetime import datetime

DB_FILE = "chat_history.db"

class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Table for Chat Sessions (The Sidebar items)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table for Messages (The Chat items)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                role TEXT,
                content TEXT,
                image_path TEXT,
                file_paths TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            )
        ''')
        self.conn.commit()

    def create_session(self, title="New Chat"):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO sessions (title) VALUES (?)", (title,))
        self.conn.commit()
        return cursor.lastrowid

    def get_sessions(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title FROM sessions ORDER BY id DESC")
        return cursor.fetchall()

    def delete_session(self, session_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
        cursor.execute("DELETE FROM sessions WHERE id=?", (session_id,))
        self.conn.commit()

    def add_message(self, session_id, role, content, image_path=None, file_paths=None):
        cursor = self.conn.cursor()
        # Convert list to JSON string for storage
        files_json = json.dumps(file_paths) if file_paths else None
        
        cursor.execute('''
            INSERT INTO messages (session_id, role, content, image_path, file_paths)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_id, role, content, image_path, files_json))
        self.conn.commit()
        
        # Update session title based on first user message
        if role == 'user':
            # Check if title is generic
            cursor.execute("SELECT title FROM sessions WHERE id=?", (session_id,))
            current_title = cursor.fetchone()[0]
            if current_title == "New Chat":
                # Truncate content for title
                new_title = (content[:30] + '..') if len(content) > 30 else content
                cursor.execute("UPDATE sessions SET title=? WHERE id=?", (new_title, session_id))
                self.conn.commit()

    def get_messages(self, session_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT role, content, image_path, file_paths FROM messages WHERE session_id=? ORDER BY id ASC", (session_id,))
        rows = cursor.fetchall()
        
        formatted = []
        for r in rows:
            formatted.append({
                'role': r[0],
                'text': r[1],
                'image_path': r[2],
                'file_paths': json.loads(r[3]) if r[3] else []
            })
        return formatted