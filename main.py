import logging
import schedule
import time
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from utils.webdav_sync import WebDAVSyncClient
from utils.db_handler import DatabaseManager
from utils.local_file_handler import get_available_files
from utils.zip_handler import ZipHandler

# 全局变量，用于跟踪任务执行状态
task_is_running = False

def setup_logging():
    # 确保日志目录存在
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 设置日志格式
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(log_format, date_format)

    # 创建 RotatingFileHandler
    log_file = os.path.join(log_dir, "webdav_sync.log")
    file_handler = RotatingFileHandler(log_file, maxBytes=20*1024*1024, backupCount=5, delay=True)
    file_handler.setFormatter(formatter)

    # 设置文件处理器为非阻塞模式
    file_handler.setLevel(logging.INFO)
    file_handler.setStream(open(log_file, 'a'))

    # 创建 StreamHandler 用于控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 配置 root logger
    logging.root.setLevel(logging.INFO)
    logging.root.addHandler(file_handler)
    logging.root.addHandler(console_handler)

    logging.info("日志系统初始化完成")

def handle_local_zip(client, sync_config):
    """处理本地文件压缩任务"""
    if not sync_config.get('local_zip', False):
        return get_available_files(sync_config['local_sync_directory'])
        
    origin_dir = sync_config['local_origin_directory']
    sync_dir = sync_config['local_sync_directory']
    
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        folder_name = os.path.basename(origin_dir.rstrip('/\\'))
        zip_filename = f"{folder_name}_{timestamp}.zip"
        
        zip_handler = ZipHandler(origin_dir, sync_dir, zip_filename)
        zip_path = zip_handler.create_zip()
        return get_available_files(os.path.dirname(zip_path))
    except Exception as e:
        logging.error(f"创建压缩文件失败，终止本次任务: {str(e)}")
        raise

def sync_files(client, db_manager, file_list, sync_config):
    """同步本地文件到远程"""
    unsynced_files = []
    for file_path in file_list:
        file_info = db_manager.get_file_info(file_path)
        if file_info is None or not file_info["sync_success"]:
            unsynced_files.append(file_path)
    
    success_count = 0
    for file_path in unsynced_files:
        try:
            remote_path = client.sync_file(file_path, sync_config['remote_directory'])
            db_manager.add_file(file_path, remote_path)
            db_manager.update_file_sync_status(file_path, True)
            logging.info(f"成功同步文件: {file_path}")
            success_count += 1
        except Exception as e:
            logging.error(f"同步文件失败: {file_path}, 错误: {str(e)}")
    
    logging.info(f"本次任务共成功同步 {success_count} 个文件")
    return success_count

def clean_remote_expired_files(client, db_manager, sync_config):
    """清理远程过期文件"""
    remote_files = client.list_remote_directory(sync_config['remote_directory'])
    remote_save_days = sync_config['remote_save_day']
    current_time = time.time()

    for remote_file in remote_files:
        remote_path = os.path.join(sync_config['remote_directory'], remote_file).replace('\\', '/')
        file_info = db_manager.get_file_info(remote_path)
        if file_info:
            sync_time = datetime.fromisoformat(file_info['sync_time']).timestamp()
            if current_time - sync_time > remote_save_days * 24 * 3600:
                try:
                    client.delete_remote_file(remote_path)
                    db_manager.mark_remote_deleted(remote_path)
                    logging.info(f"已删除过期远程文件: {remote_path}")
                except Exception as e:
                    logging.error(f"删除过期远程文件失败: {remote_path}, 错误: {str(e)}")

def hourly_task(client, db_manager):
    """主任务执行函数"""
    global task_is_running
    
    if task_is_running:
        logging.info("上一次任务还未完成，跳过本次执行")
        return
    
    task_is_running = True
    
    try:
        logging.info(f"【开始执行任务: {time.strftime('%Y-%m-%d %H:%M:%S')}】")
        
        # 遍历所有同步配置
        for sync_config in client.config['Sync']:
            logging.info(f"处理同步配置: {sync_config['local_origin_directory']} -> {sync_config['remote_directory']}")
            
            try:
                # 执行任务：压缩本地文件
                file_list = handle_local_zip(client, sync_config)
                
                # 执行任务：同步文件
                sync_files(client, db_manager, file_list, sync_config)
                
                # 执行任务：删除远端过期文件
                clean_remote_expired_files(client, db_manager, sync_config)
                
                logging.info(f"完成同步配置: {sync_config['local_origin_directory']}")
            except Exception as e:
                logging.error(f"处理同步配置时出错: {sync_config['local_origin_directory']}, 错误: {str(e)}")
                continue  # 继续处理下一个配置

        logging.info(f"【任务执行结束: {time.strftime('%Y-%m-%d %H:%M:%S')}】")
    except Exception as e:
        logging.error(f"任务执行出错: {str(e)}")
    finally:
        task_is_running = False

def run_scheduled_task(client, db_manager):
    hourly_task(client, db_manager)

def main():
    setup_logging()
    logging.info("程序开始执行")
    client = WebDAVSyncClient('config.json')
    # 指定数据库文件路径，如果不存在会自动创建
    db_manager = DatabaseManager('data/synced_files.db')
    logging.info("WebDAV客户端初始化完成")
    
    # 立即执行一次任务
    hourly_task(client, db_manager)
    
    # 设置定时任务
    schedule.every().second.do(run_scheduled_task, client=client, db_manager=db_manager)
    
    logging.info("定时任务已设置，每小时执行一次")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)

    except KeyboardInterrupt:
        logging.info("程序被用户中断")
    finally:
        logging.info("程序结束")

if __name__ == '__main__':
    main()
