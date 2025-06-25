# 简介
通过webdav协议定期备份文件

# 开发
## 创建虚拟环境
conda create -n webdavsync python=3.9.2

## 激活虚拟环境
conda activate webdavsync

## 安装依赖
pip install -r requirements.txt

## 运行程序
python main.py

## 打包
- 提交到github之后，create tag，输入一个版本号v0.0.1，会自动打包tags
- 版本号带alpha的为测试版，不发布release，不带的话还会发布一个releases

# 使用说明
> 在运行程序同级目录下创建config.json
> 注意，本项目不包含文件内容比对，仅以文件名作为唯一同步标识，不支持修改文件，所以一定要给每个要同步的文件增加唯一时间戳，重名文件不会同步。
> 已同步过的文件，云端删除后不会重复同步
> 虽然配置文件中是一个数组，但是现在只支持配置一个
>

## 配置文件
config.json 配置文件说明    
local_zip: 是否压缩本地文件，默认不压缩
local_origin_directory: 选择压缩时，这个是需要备份的文件夹；不压缩则不用填
local_sync_directory: 选择压缩时，这个是压缩后文件的保存路径；不压缩则填需要备份的文件夹
remote_directory: 远程文件夹路径，同步文件时，同步的文件夹
local_save_day: 本地文件保存天数，超过天数后，本地文件会被删除
remote_save_day: 远程文件保存天数，超过天数后，远程文件会被删除

## 在linux上运行
> 注意修改版本号
``` bash
# 测试
chmod +x webdavsync-v0.1.0-debian
./webdavsync-v0.1.0-debian

# 后台运行
chmod +x webdavsync-v0.1.0-debian
nohup ./webdavsync-v0.1.0-debian > /dev/null 2>&1 & echo $! > webdavsync.pid

# 查看程序是否在运行
pidof webdavsync-v0.1.0-debian

# 关闭后台运行
kill $(cat webdavsync.pid) && rm webdavsync.pid
```

# 在windows上运行
需要以管理员身份运行

