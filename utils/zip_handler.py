import os
import zipfile
from datetime import datetime
import logging

class ZipHandler:
    def __init__(self, origin_dir, sync_dir, zip_filename=None):
        self.origin_dir = origin_dir
        self.sync_dir = sync_dir
        self.zip_filename = zip_filename
        
    def create_zip(self):
        if self.zip_filename:
            zip_path = os.path.join(self.sync_dir, self.zip_filename)
        else:
            # 保留原有的默认命名逻辑作为后备
            zip_path = os.path.join(self.sync_dir, 'archive.zip')
        
        try:
            # 确保同步目录存在
            if not os.path.exists(self.sync_dir):
                os.makedirs(self.sync_dir)
            
            # 创建zip文件
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 遍历源目录
                for root, _, files in os.walk(self.origin_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # 获取相对路径
                        rel_path = os.path.relpath(file_path, self.origin_dir)
                        # 添加文件到zip
                        zipf.write(file_path, rel_path)
            
            logging.info(f"成功创建压缩文件: {zip_path}")
            return zip_path
            
        except Exception as e:
            logging.error(f"创建压缩文件失败: {str(e)}")
            raise