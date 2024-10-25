import os
import re
from datetime import datetime
import time

class FileLockedError(Exception):
    """当文件被占用时抛出的自定义异常"""
    pass

def check_file_access(file_path):
    """
    检查文件是否可访问（未被占用）

    :param file_path: 文件路径
    :raises FileLockedError: 如果文件被占用则抛出此异常
    """
    try:
        # 尝试以读写模式打开文件
        with open(file_path, 'r+'):
            pass
    except IOError:
        raise FileLockedError(f"文件 {file_path} 被占用或无法访问")

def get_available_files(folder_path):
    """
    获取指定文件夹下所有未被占用的文件

    :param folder_path: 文件夹路径
    :return: 未被占用的文件路径列表
    """
    available_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                check_file_access(file_path)
                available_files.append(file_path)
            except FileLockedError:
                # 如果文件被占用，跳过该文件
                continue
    return available_files
