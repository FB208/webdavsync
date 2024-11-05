import logging, os, time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from utils.webdav_sync import WebDAVSyncClient
from utils.db_handler import DatabaseManager
from utils.local_file_handler import get_available_files
from utils.zip_handler import ZipHandler
from logging.handlers import RotatingFileHandler
import hashlib
import zipfile

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
        zip_filename = f"{folder_name}_{timestamp}.wdsync.zip"
        zip_filepath = os.path.join(sync_dir, zip_filename)
        
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(origin_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        # 获取相对路径
                        arc_path = os.path.relpath(file_path, origin_dir)
                        # 尝试添加文件到压缩包
                        zipf.write(file_path, arc_path)
                    except (OSError, IOError) as e:
                        # 记录错误但继续处理其他文件
                        logging.warning(f"无法压缩文件 {file_path}: {str(e)}")
                        continue
        
        logging.info(f"成功创建压缩文件: {zip_filepath}")
        return [zip_filepath]
        
    except Exception as e:
        logging.error(f"创建压缩文件失败: {str(e)}")
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

def create_task_function(client, db_config, sync_config):
    """为每个配置创建独立的任务函数"""
    def task():
        try:
            logging.info(f"开始执行任务: {sync_config['local_origin_directory']}")
            
            # 在任务线程中创建新的数据库连接
            db_manager = DatabaseManager(db_config)
            
            # 执行任务：压缩本地文件
            file_list = handle_local_zip(client, sync_config)
            
            # 执行任务：同步文件
            sync_files(client, db_manager, file_list, sync_config)
            
            # 执行任务：删除本地过期文件
            clean_local_expired_files(sync_config)
            
            # 执行任务：删除远端过期文件
            clean_remote_expired_files(client, db_manager, sync_config)
            
            logging.info(f"完成同步配置: {sync_config['local_origin_directory']}")
        except Exception as e:
            logging.error(f"处理同步配置时出错: {sync_config['local_origin_directory']}, 错误: {str(e)}")
    
    return task

def clean_local_expired_files(sync_config):
    """清理本地过期文件"""
    # 只在local_zip为true时执行清理
    if not sync_config.get('local_zip', False):
        return

    try:
        local_dir = sync_config['local_sync_directory']
        local_save_days = sync_config['local_save_day']
        current_time = datetime.now()

        # 确保目录存在
        if not os.path.exists(local_dir):
            logging.warning(f"本地同步目录不存在: {local_dir}")
            return

        # 获取本地目录中的所有wdsync压缩文件
        for root, _, files in os.walk(local_dir):
            for file in files:
                if not file.endswith('.wdsync.zip'):
                    continue

                file_path = os.path.join(root, file)
                
                try:
                    # 解析文件名���的时间戳
                    # 文件名格式：folder_name_YYYY-MM-DD-HH-mm-SS.wdsync.zip
                    timestamp_str = file.split('_')[-1].replace('.wdsync.zip', '')
                    try:
                        file_time = datetime.strptime(timestamp_str, '%Y-%m-%d-%H-%M-%S')
                    except ValueError:
                        # 如果无法解析时间戳，说明文件名格式不对，跳过
                        logging.debug(f"跳过文件名格式不符的文件: {file_path}")
                        continue

                    # 计算文件是否过期
                    days_old = (current_time - file_time).days
                    if days_old > local_save_days:
                        # 检查文件是否被锁定
                        if not is_file_accessible(file_path):
                            logging.warning(f"文件被占用，跳过删除: {file_path}")
                            continue

                        os.remove(file_path)
                        logging.info(f"已删除过期本地压缩文件: {file_path}")

                except Exception as e:
                    logging.error(f"处理文件时出错: {file_path}, 错误: {str(e)}")
                    continue

    except Exception as e:
        logging.error(f"清理本地过期文件时出错: {str(e)}")

def is_file_accessible(file_path):
    """检查文件是否可访问（未被锁定）"""
    try:
        with open(file_path, 'ab') as _:
            pass
        return True
    except IOError:
        return False

def create_safe_task_id(path):
    """创建基于路径哈希的安全任务ID"""
    # 使用 MD5（生成32位哈希）
    path_hash = hashlib.md5(path.encode('utf-8')).hexdigest()
    # 或者使用 SHA256（生成64位哈希）
    # path_hash = hashlib.sha256(path.encode('utf-8')).hexdigest()
    
    # 可以只取前8位作为简短标识
    short_hash = path_hash[:8]
    return f"sync_task_{short_hash}"

def main():
    setup_logging()
    logging.info("程序开始执行")
    client = WebDAVSyncClient('config.json')
    logging.info("WebDAV客户端初始化完成")
    
    # 创建调度器
    scheduler = BackgroundScheduler()
    scheduler.start()
    
    # 为每个同步配置创建独立的定时任务
    for sync_config in client.config['Sync']:
        task_func = create_task_function(client, 'data/synced_files.db', sync_config)
        
        # 从配置中获取cron表达式
        cron_expression = sync_config['schedule']
        
        # 添加任务到调度器
        task_id = create_safe_task_id(sync_config['local_origin_directory'])
        logging.info(f"任务ID映射: {task_id} -> {sync_config['local_origin_directory']}")
        scheduler.add_job(
            task_func,
            CronTrigger.from_crontab(cron_expression),
            id=task_id,
            replace_existing=True
        )
        
        logging.info(f"已设置定时任务: {sync_config['local_origin_directory']}, 调度: {cron_expression}")
    
    try:
        # 保持主线程运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("程序被用户中断")
        scheduler.shutdown()
    finally:
        logging.info("程序结束")

if __name__ == '__main__':
    main()
