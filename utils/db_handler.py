import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_file='synced_files.db'):
        # 确保数据库文件所在的目录存在
        db_dir = os.path.dirname(db_file)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        self.db_file = db_file
        self.conn = None
        self.cursor = None
        self.initialize_db()

    def initialize_db(self):
        # 连接到数据库文件，如果不存在会自动创建
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()
        
        # 创建表（如果不存在）
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS synced_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE,
                remote_path TEXT,
                sync_time TIMESTAMP,
                sync_success BOOLEAN DEFAULT 0,
                remote_deleted BOOLEAN DEFAULT 0
            )
        ''')
        self.conn.commit()

    def add_file(self, local_path, remote_path):
        """添加或更新文件记录"""
        self.cursor.execute('''
            INSERT OR REPLACE INTO synced_files 
            (file_path, remote_path, sync_time, sync_success, remote_deleted)
            VALUES (?, ?, ?, ?, ?)
        ''', (local_path, remote_path, datetime.now(), True, False))
        self.conn.commit()

    def update_file_sync_status(self, file_path, success):
        """更新文件同步状态"""
        self.cursor.execute('''
            UPDATE synced_files
            SET sync_time = ?, sync_success = ?
            WHERE file_path = ?
        ''', (datetime.now(), success, file_path))
        self.conn.commit()

    def mark_remote_deleted(self, remote_path):
        """标记远程文件已删除"""
        self.cursor.execute('''
            UPDATE synced_files
            SET remote_deleted = 1
            WHERE file_path = ? OR remote_path = ?
        ''', (remote_path, remote_path))
        self.conn.commit()

    def delete_file(self, file_path):
        """删除文件记录"""
        self.cursor.execute('DELETE FROM synced_files WHERE file_path = ? OR remote_path = ?', (file_path, file_path))
        self.conn.commit()

    def get_file_info(self, file_path):
        """获取单个文件信息"""
        self.cursor.execute('''
            SELECT id, file_path, remote_path, sync_time, sync_success, remote_deleted 
            FROM synced_files 
            WHERE file_path = ? OR remote_path = ?
        ''', (file_path, file_path))
        result = self.cursor.fetchone()
        if result:
            return {
                'id': result[0],
                'file_path': result[1],
                'remote_path': result[2],
                'sync_time': result[3],
                'sync_success': result[4],
                'remote_deleted': result[5]
            }
        return None

    def get_all_files(self):
        """获取所有文件信息"""
        self.cursor.execute('SELECT * FROM synced_files')
        return self.cursor.fetchall()

    # ... 其他方法保持不变 ...
