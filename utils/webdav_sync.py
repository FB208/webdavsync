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
        
        logging.info("正在测试WebDAV连接...")
        try:
            self.webdav_client.list()
            logging.info("WebDAV连接测试成功")
        except Exception as e:
            logging.error(f"WebDAV连接测试失败: {str(e)}")

    def sync_file(self, local_path, remote_directory):
        """
        同步单个文件到远程目录
        
        :param local_path: 本地文件路径
        :param remote_directory: 远程目录路径
        :return: 远程文件路径或None（如果同步失败）
        """
        try:
            relative_path = os.path.basename(local_path)
            remote_path = os.path.join(remote_directory, relative_path).replace('\\', '/')
            
            logging.info(f"正在同步文件: {local_path} -> {remote_path}")
            self.webdav_client.upload_sync(local_path=local_path, remote_path=remote_path)
            logging.info(f"已同步文件: {local_path} -> {remote_path}")
            
            return remote_path
        except Exception as e:
            logging.error(f"同步文件时出错: {str(e)}")
            return None

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
                modified_time_str = info.get('modified', '')
                if modified_time_str:
                    modified_time = datetime.strptime(modified_time_str, "%a, %d %b %Y %H:%M:%S %Z")
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

    def list_remote_directory(self, remote_directory):
        """
        列出远程目录中的所有文件

        :param remote_directory: 要列出内容的远程目录路径
        :return: 文件名列表
        """
        try:
            files = self.webdav_client.list(remote_directory)
            return files
        except Exception as e:
            logging.error(f"列出远程目录内容时出错: {str(e)}")
            return []

class SyncEventHandler(FileSystemEventHandler):
    def __init__(self, sync_client, sync_config):
        self.sync_client = sync_client
        self.sync_config = sync_config

    def on_created(self, event):
        if not event.is_directory:
            self.sync_client.sync_file(event.src_path, self.sync_config['remote_directory'])

    def on_modified(self, event):
        if not event.is_directory:
            self.sync_client.sync_file(event.src_path, self.sync_config['remote_directory'])

    def on_deleted(self, event):
        if not event.is_directory:
            relative_path = os.path.basename(event.src_path)
            remote_path = os.path.join(self.sync_config['remote_directory'], relative_path).replace('\\', '/')
            self.sync_client.delete_remote_file(remote_path)
