import os
import time
import logging
import json
from webdav3.client import Client
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime
import pytz

class WebDAVSyncClient:
    def __init__(self, config_file):
        with open(config_file, 'r') as f:
            self.config = json.load(f)
        
        self.webdav_options = {
            'webdav_hostname': self.config['WebDAV']['url'],
            'webdav_login': self.config['WebDAV']['username'],
            'webdav_password': self.config['WebDAV']['password']
        }
        self.webdav_client = Client(self.webdav_options)
        
        # 修改这里以处理 Sync 是一个列表的情况
        self.local_directory = self.config['Sync'][0]['local_directory']
        self.remote_directory = self.config['Sync'][0]['remote_directory']
        
        logging.info(f"WebDAV客户端初始化完成，本地目录：{self.local_directory}，远程目录：{self.remote_directory}")

        logging.info("正在测试WebDAV连接...")
        try:
            self.webdav_client.list()
            logging.info("WebDAV连接测试成功")
        except Exception as e:
            logging.error(f"WebDAV连接测试失败: {str(e)}")

    def start_sync(self):
        self.observer.schedule(self.event_handler, self.local_directory, recursive=True)
        self.observer.start()
        logging.info(f"开始监控目录: {self.local_directory}")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()

    def sync_all_files(self):
        logging.info(f"开始同步所有文件从 {self.local_directory} 到 {self.remote_directory}")
        for root, dirs, files in os.walk(self.local_directory):
            for file in files:
                local_path = os.path.join(root, file)
                self.sync_file(local_path)
        logging.info("所有文件同步完成")

    def sync_file(self, local_path):
        try:
            relative_path = os.path.relpath(local_path, self.local_directory)
            remote_path = os.path.join(self.remote_directory, relative_path).replace('\\', '/')
            
            logging.info(f"正在同步文件: {local_path} -> {remote_path}")
            self.webdav_client.upload_sync(local_path=local_path, remote_path=remote_path)
            logging.info(f"已同步文件: {local_path} -> {remote_path}")
            
            return remote_path  # 返回远程文件路径
        except Exception as e:
            logging.error(f"同步文件时出错: {str(e)}")
            return None  # 如果同步失败，返回 None

    def delete_remote_file(self, remote_path):
        """
        删除远程文件

        :param remote_path: 远程文件的完整路径
        :return: 布尔值,表示删除是否成功
        """
        try:
            if self.webdav_client.check(remote_path):
                self.webdav_client.clean(remote_path)
                logging.info(f"已删除远程文件: {remote_path}")
                return True
            else:
                logging.warning(f"远程文件不存在，无法删除: {remote_path}")
                return False
        except Exception as e:
            logging.error(f"删除远程文件时出错: {remote_path}, 错误: {str(e)}")
            return False

    def get_remote_file_info(self, remote_path):
        """
        获取远程文件的信息,包括更新时间
        
        :param remote_path: 远程文件路径
        :return: 包含文件信息的字典,如果文件不存在则返回 None
        """
        try:
            info = self.webdav_client.info(remote_path)
            if info:
                # 解析更新时间
                modified_time_str = info.get('modified', '')
                if modified_time_str:
                    # 将字符串转换为 datetime 对象
                    modified_time = datetime.strptime(modified_time_str, "%a, %d %b %Y %H:%M:%S %Z")
                    # 确保时间是 UTC 时间
                    modified_time = modified_time.replace(tzinfo=pytz.UTC)
                else:
                    modified_time = None

                return {
                    'name': info['name'],
                    'size': info['size'],
                    'modified': modified_time,
                    'created': info.get('created'),
                    'is_dir': info['isdir']
                }
            return None
        except Exception as e:
            logging.error(f"获取远程文件信息失败: {remote_path}, 错误: {str(e)}")
            return None

    def list_remote_directory(self):
        """
        列出远程目录中的所有文件

        :return: 文件名列表
        """
        try:
            files = self.webdav_client.list(self.remote_directory)
            return files
        except Exception as e:
            logging.error(f"列出远程目录内容时出错: {str(e)}")
            return []

class SyncEventHandler(FileSystemEventHandler):
    def __init__(self, sync_client):
        self.sync_client = sync_client

    def on_created(self, event):
        if not event.is_directory:
            self.sync_client.sync_file(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self.sync_client.sync_file(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self.sync_client.delete_remote_file(event.src_path)
