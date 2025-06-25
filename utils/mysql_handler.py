import pymysql
import os
import datetime

class MySQLBackup:
    def __init__(self, host='localhost', user='root', password='', port=3306):
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        
    def get_connection(self):
        return pymysql.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            port=self.port,
            charset='utf8mb4'
        )

    def backup_database(self, database_name, backup_path='./backups/', tag=None):
        # 创建备份目录结构
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = os.path.join(backup_path, f'{database_name}_{timestamp}')
        if tag:
            backup_dir = os.path.join(backup_path, f'{tag}_{database_name}_{timestamp}')
        os.makedirs(backup_dir, exist_ok=True)
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # 先选择数据库
                cursor.execute(f"USE `{database_name}`")
                
                # 然后获取数据库信息
                cursor.execute(f"SELECT @@character_set_database, @@collation_database")
                charset, collation = cursor.fetchone()
                
                cursor.execute(f"SELECT SCHEMA_NAME, DEFAULT_ENCRYPTION FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = '{database_name}'")
                _, encryption = cursor.fetchone()
                encryption = 'Y' if encryption.upper() == 'YES' else 'N'
                
                # 1. 创建数据库结构文件（包含表结构、视图、函数）
                structure_file = os.path.join(backup_dir, '0_structure.sql')
                with open(structure_file, 'w', encoding='utf8') as f:
                    # 写入数据库创建语句
                    create_db_sql = (
                        f"CREATE DATABASE /*!32312 IF NOT EXISTS*/ `{database_name}` "
                        f"/*!40100 DEFAULT CHARACTER SET {charset} COLLATE {collation} */ "
                        f"/*!80016 DEFAULT ENCRYPTION='{encryption}' */;\n"
                        f"USE `{database_name}`;\n\n"
                    )
                    f.write(create_db_sql)
                    
                    # 写入表结构
                    cursor.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'")
                    tables = cursor.fetchall()
                    total_tables = len(tables)
                    print(f"\n开始备份数据库 {database_name}，共有 {total_tables} 个表")
                    
                    for table in tables:
                        table_name = table[0]
                        cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
                        create_table = cursor.fetchone()[1]
                        f.write(f"{create_table};\n\n")
                    
                    # 写入视图
                    f.write("\n-- Views\n")
                    cursor.execute("SHOW FULL TABLES WHERE Table_type = 'VIEW'")
                    views = cursor.fetchall()
                    for view in views:
                        view_name = view[0]
                        cursor.execute(f"SHOW CREATE VIEW `{view_name}`")
                        create_view = cursor.fetchone()[1]
                        f.write(f"{create_view};\n\n")
                    
                    # 写入存储过程和函数
                    f.write("\n-- Routines\n")
                    cursor.execute("SHOW PROCEDURE STATUS WHERE Db = %s", (database_name,))
                    procedures = cursor.fetchall()
                    for proc in procedures:
                        proc_name = proc[1]
                        cursor.execute(f"SHOW CREATE PROCEDURE `{proc_name}`")
                        create_proc = cursor.fetchone()[2]
                        f.write(f"DELIMITER //\n{create_proc}//\nDELIMITER ;\n\n")
                
                # 2. 为每个表创建单独的数据文件
                for index, table in enumerate(tables, 1):
                    table_name = table[0]
                    print(f"正在备份表数据 ({index}/{total_tables}): {table_name}")
                    
                    data_file = os.path.join(backup_dir, f'{index}_data_{table_name}.sql')
                    with open(data_file, 'w', encoding='utf8') as f:
                        f.write(f"USE `{database_name}`;\n")
                        f.write("SET FOREIGN_KEY_CHECKS=0;\n")
                        f.write("SET UNIQUE_CHECKS=0;\n\n")
                        
                        cursor.execute(f"SELECT * FROM `{table_name}`")
                        rows = cursor.fetchall()
                        
                        if rows:
                            cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
                            columns = [column[0] for column in cursor.fetchall()]
                            
                            for row in rows:
                                values = []
                                for value in row:
                                    if value is None:
                                        values.append('NULL')
                                    elif isinstance(value, (int, float)):
                                        values.append(str(value))
                                    else:
                                        values.append(f"'{str(value)}'")
                                
                                f.write(f"INSERT INTO `{table_name}` "
                                       f"({', '.join(['`'+c+'`' for c in columns])}) "
                                       f"VALUES ({', '.join(values)});\n")
                    
                        f.write("\nSET FOREIGN_KEY_CHECKS=1;\n")
                        f.write("SET UNIQUE_CHECKS=1;\n")
        
        print(f'\n数据库 {database_name} 备份成功！备份目录：{backup_dir}')
        return backup_dir

        """
        备份单个表的结构和数据
        :param database_name: 数据库名称
        :param table_name: 表名
        :param backup_path: 备份路径
        :param tag: 备份文件名前缀标签，用于区分不同服务器
        """
        os.makedirs(backup_path, exist_ok=True)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 根据是否有tag构建文件名
        if tag:
            backup_file = os.path.join(backup_path, f'{tag}_{database_name}_{table_name}_{timestamp}.sql')
        else:
            backup_file = os.path.join(backup_path, f'{database_name}_{table_name}_{timestamp}.sql')
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"USE {database_name}")
                    
                    with open(backup_file, 'w', encoding='utf8') as f:
                        # 获取建表语句
                        cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
                        create_table = cursor.fetchone()[1]
                        f.write(f"{create_table};\n\n")
                        
                        # 获取表数据
                        cursor.execute(f"SELECT * FROM `{table_name}`")
                        rows = cursor.fetchall()
                        
                        if rows:
                            # 获取列名
                            cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
                            columns = [column[0] for column in cursor.fetchall()]
                            
                            # 生成INSERT语句
                            for row in rows:
                                values = []
                                for value in row:
                                    if value is None:
                                        values.append('NULL')
                                    elif isinstance(value, (int, float)):
                                        values.append(str(value))
                                    else:
                                        values.append(f"'{str(value)}'")
                                
                                f.write(f"INSERT INTO `{table_name}` "
                                       f"({', '.join(['`'+c+'`' for c in columns])}) "
                                       f"VALUES ({', '.join(values)});\n")
                                
            print(f'数据表 {database_name}.{table_name} 备份成功！备份文件：{backup_file}')
            return backup_file
            
        except Exception as e:
            print(f'备份失败：{str(e)}')
            return None

    def get_user_databases(self):
        """
        获取所有用户数据库，排除系统数据库
        :return: 数据库名称列表
        """
        # 系统数据库列表
        system_databases = {'mysql', 'information_schema', 'performance_schema', 'sys'}
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SHOW DATABASES")
                    databases = cursor.fetchall()
                    # 过滤掉系统数据库
                    user_databases = [db[0] for db in databases if db[0] not in system_databases]
                    return user_databases
        except Exception as e:
            print(f'获取数据库列表失败：{str(e)}')
            return []

    def backup_all_user_databases(self, backup_path='./backups/', tag=None):
        """
        备份所有用户数据库
        :param backup_path: 备份文件保存路径
        :param tag: 备份文件名前缀标签，用于区分不同服务器
        :return: 备份文件路径列表
        """
        backup_files = []
        user_databases = self.get_user_databases()
        
        for database in user_databases:
            backup_file = self.backup_database(database, backup_path, tag)
            if backup_file:
                backup_files.append(backup_file)
        
        return backup_files

if __name__ == "__main__":
    # 据库连接配置
    configs = [
        {
            'host': '192.168.10.247',
            'user': 'root',
            'password': 'mymysql135',
            'port': 11306,
            'tag': 'server1'  # 第一台服务器的标签
        }
    ]
    
    try:
        for config in configs:
            tag = config.pop('tag')  # 从配置中取出tag
            backup = MySQLBackup(**config)
            
            print(f"\n开始备份服务器 {config['host']} ({tag}) 的数据库...")
            
            # 获取所有用户数据库
            databases = backup.get_user_databases()
            print(f"找到以下用户数据库: {', '.join(databases)}")
            
            
            backup.backup_database('fas4bs', tag='server1')
            
            print(f"\n服务器 {tag} 备份完成！备份文件列表：")
            
            # 备份所有数据库
            # backup_files = backup.backup_all_user_databases(tag=tag)
            
            # if backup_files:
            #     print(f"\n服务器 {tag} 备份完成！备份文件列表：")
            #     for file in backup_files:
            #         print(f"- {file}")
            # else:
            #     print(f"\n服务器 {tag} 备份过程中出现错误，请检查日志。")
            
    except Exception as e:
        print(f"\n程序执行出错: {str(e)}")

