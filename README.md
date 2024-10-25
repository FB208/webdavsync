# webdavsync
通过webdav协议定期备份文件

# 创建虚拟环境
conda create -n webdavsync python=3.9.2

# 激活虚拟环境
conda activate webdavsync

# 安装依赖
pip install -r requirements.txt

# 运行程序
python main.py


# 使用说明
> 注意，本项目不包含文件内容比对，仅以文件名作为唯一同步标识，不支持修改文件，所以一定要给每个要同步的文件增加唯一时间戳，重名文件不会同步。
> 已同步过的文件，云端删除后不会重复同步
> 虽然配置文件中是一个数据，但是现在只支持配置一个