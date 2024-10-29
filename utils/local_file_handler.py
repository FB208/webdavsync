import os
import re
from datetime import datetime
import time

class FileLockedError(Exception):
    """当文件被占用时抛出的自定义异常"""
    pass

def check_file_access(file_path):
    """
    检查文件是否可访问且写入完成
    
    :param file_path: 文件路径
    :raises FileLockedError: 如果文件被占用则抛出此异常
    """
    try:
        # 获取初始文件大小
        initial_size = os.path.getsize(file_path)
        # 等待一小段时间
        time.sleep(1)
        # 再次获取文件大小
        final_size = os.path.getsize(file_path)
        
        # 如果文件大小发生变化，说明文件正在被写入
        if initial_size != final_size:
            raise FileLockedError(f"文件 {file_path} 正在被写入")
            
        # 尝试以独占模式打开文件
        with open(file_path, 'rb') as f:
            # 尝试获取文件锁
            try:
                # Windows 系统
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                # Linux/Unix 系统
                else:
                    import fcntl
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except (IOError, OSError):
                raise FileLockedError(f"文件 {file_path} 被占用")
                
    except (IOError, OSError) as e:
        raise FileLockedError(f"文件 {file_path} 被占用或无法访问: {str(e)}")

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
