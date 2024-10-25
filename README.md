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
>

## 在linux上运行
> 注意修改版本号
``` bash
# 测试
chmod +x webdavsync-v1.0.0-debian
./webdavsync-v1.0.0-debian

# 后台运行
chmod +x webdavsync-v1.0.0-debian
nohup ./webdavsync-v1.0.0-debian > /dev/null 2>&1 & echo $! > webdavsync.pid

# 查看程序是否在运行
pidof webdavsync-v1.0.0-debian

# 关闭后台运行
kill $(cat webdavsync.pid) && rm webdavsync.pid
```
