# 快速开始

## 安装

```bash
pip install aivfs
# 
import aivfs

# 创建新的文件系统
fs = aivfs.init('my_fs', force=True)

# 写入文件
fs.write_file('/home/test.txt', 'Hello World')

# 读取文件
content = fs.read_file('/home/test.txt')

# 创建目录
fs.mkdir('/home/user1', parents=True)

# 列出目录内容
files = fs.list_dir('/home')
```


from aivfs import FileMode

# 设置文件权限(rwxr-xr-x)
fs.chmod('/home/test.txt', FileMode(7, 5, 5))

# 修改所有者
fs.chown('/home/test.txt', 'user1', 'users')