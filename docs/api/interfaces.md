# AIVFS API 文档

## 目录

1. [概述](#概述)
2. [基本用法](#基本用法)
3. [核心接口](#核心接口)
4. [文件系统配置](#文件系统配置)
5. [异常处理](#异常处理)

## 概述

AIVFS 是一个基于元数据的虚拟文件系统，提供类 Unix 的文件系统功能。

### 主要特性

- 文件和目录的基本操作
- 类 Unix 的权限管理
- 元数据管理
- 文件系统遍历和搜索
- 磁盘使用统计

## 基本用法

```python
import aivfs

# 创建新文件系统
fs = aivfs.init('my_fs', force=True, owner='user1', group='users')

# 写入文件
fs.write_file('/home/test.txt', 'Hello World')

# 读取文件
content = fs.read_file('/home/test.txt')

# 挂载已存在的文件系统
fs = aivfs.mount('my_fs')
```

## 核心接口

### 初始化函数

#### `init(path: Optional[PathLike], force: bool, owner: str, group: str) -> AIVFS`

创建新的文件系统实例。

参数：
- `path`: 文件系统路径，默认为 'aivfs_root'
- `force`: 是否强制创建，默认为 False
- `owner`: 文件系统所有者，默认为 'root'
- `group`: 文件系统所属组，默认为 'root'

返回：
- `AIVFS`: 文件系统实例

异常：
- `ValueError`: 目录已存在且 force=False
- `PermissionError`: 权限不足
- `AIVFSError`: 创建失败

### 文件操作接口

#### `write_file(path: PathLike, content: str, owner: str, group: str, mode: FileMode) -> None`

写入文件内容。

参数：
- `path`: 文件路径
- `content`: 文件内容
- `owner`: 所有者（可选）
- `group`: 用户组（可选）
- `mode`: 权限模式（可选）

#### `read_file(path: PathLike) -> str`

读取文件内容。

参数：
- `path`: 文件路径

返回：
- `str`: 文件内容

### 目录操作接口

#### `mkdir(path: PathLike, owner: str, group: str, mode: FileMode, parents: bool, exist_ok: bool) -> None`

创建目录。

参数：
- `path`: 目录路径
- `owner`: 所有者（可选）
- `group`: 用户组（可选）
- `mode`: 权限模式（可选）
- `parents`: 是否创建父目录
- `exist_ok`: 是否允许目录已存在

## 文件系统配置

### 基本目录结构

```python
DIR_PERMISSIONS = {
    'home': {
        'owner': lambda o, g: (o, g),           # 继承创建者权限
        'mode': FileMode(7, 5, 5),              # rwxr-xr-x
        'subdirs': ['public']                   # 预创建子目录
    },
    'tmp': {
        'owner': lambda o, g: ('root', 'users'),
        'mode': FileMode(7, 7, 7),              # rwxrwxrwx
        'cleanup': True                         # 启动时清理
    }
    # ...其他目录配置
}
```

### 权限模式

```python
class FileMode:
    def __init__(self, user: int, group: int, other: int):
        """初始化权限模式
        
        参数：
            user: 用户权限 (0-7)
            group: 组权限 (0-7)
            other: 其他用户权限 (0-7)
        """
```

## 异常处理

### 异常层次

- `AIVFSError`: 基础异常类
  - `FileSystemError`: 文件系统操作异常
  - `MetadataError`: 元数据操作异常
  - `PermissionError`: 权限相关异常
  - `FileNotFoundError`: 文件不存在异常
  - `InvalidPathError`: 无效路径异常

### 异常处理示例

```python
try:
    fs.write_file('/root/test.txt', 'Hello')
except PermissionError as e:
    print(f"权限错误: {e}")
except FileNotFoundError as e:
    print(f"文件不存在: {e}")
except AIVFSError as e:
    print(f"文件系统错误: {e}")
```

## 高级功能

### 文件系统遍历

```python
# 遍历目录树
for path, dirs, files in fs.walk('/home'):
    print(f"当前目录: {path}")
    print(f"子目录: {dirs}")
    print(f"文件: {files}")

# 搜索文件
for path in fs.find('/home', '*.txt'):
    print(f"找到文件: {path}")
```

### 磁盘使用统计

```python
# 获取磁盘使用情况
total, used, free = fs.get_disk_usage('/home')
print(f"总空间: {total}")
print(f"已用空间: {used}")
print(f"可用空间: {free}")
```

## IMetadataManager 接口

元数据管理器接口，负责管理文件系统中所有文件和目录的元数据信息。

### 主要职责

1. 管理文件和目录的元数据
2. 提供元数据的查询和修改功能
3. 支持目录列表功能

### 方法说明

#### `upsert(metadata: FileMetadata) -> None`
添加或更新元数据
- 参数：
  - `metadata`: 文件或目录的元数据对象
- 返回：无

#### `get(path: PathLike) -> Optional[FileMetadata]`
获取元数据，如果不存在则继承父目录元数据
- 参数：
  - `path`: 文件或目录路径
- 返回：元数据对象，如果不存在则返回 None

#### `remove(path: PathLike) -> None`
删除元数据
- 参数：
  - `path`: 要删除元数据的路径
- 返回：无

#### `list_dir(path: PathLike) -> List[FileMetadata]`
列出目录内容的元数据
- 参数：
  - `path`: 目录路径
- 返回：目录下所有项目的元数据列表

#### `exists(path: PathLike) -> bool`
检查是否存在元数据
- 参数：
  - `path`: 检查路径
- 返回：存在返回 True，否则返回 False

## IFSOperations 接口

文件系统操作接口，提供文件系统的基本操作功能。

### 文件操作

#### `write_file(path: PathLike, content: str, *, owner: str = "root", group: str = "root", mode: FileMode = FileMode(6, 4, 4)) -> None`
写入文件内容
- 参数：
  - `path`: 文件路径
  - `content`: 文件内容
  - `owner`: 所有者（默认 "root"）
  - `group`: 用户组（默认 "root"）
  - `mode`: 权限模式（默认 644）
- 返回：无

#### `read_file(path: PathLike) -> str`
读取文件内容
- 参数：
  - `path`: 文件路径
- 返回：文件内容字符串

#### `append_file(path: PathLike, content: str) -> None`
追加文件内容
- 参数：
  - `path`: 文件路径
  - `content`: 要追加的内容
- 返回：无

### 目录操作

#### `mkdir(path: PathLike, *, owner: str = "root", group: str = "root", mode: FileMode = FileMode(7, 5, 5), parents: bool = False, exist_ok: bool = False) -> None`
创建目录
- 参数：
  - `path`: 目录路径
  - `owner`: 所有者（默认 "root"）
  - `group`: 用户组（默认 "root"）
  - `mode`: 权限模式（默认 755）
  - `parents`: 是否创建父目录
  - `exist_ok`: 是否允许目录已存在
- 返回：无

### 路径操作

#### `remove(path: PathLike, recursive: bool = False) -> None`
删除文件或目录
- 参数：
  - `path`: 要删除的路径
  - `recursive`: 是否递归删除
- 返回：无

#### `copy(src: PathLike, dst: PathLike, recursive: bool = False) -> None`
复制文件或目录
- 参数：
  - `src`: 源路径
  - `dst`: 目标路径
  - `recursive`: 是否递归复制
- 返回：无

#### `move(src: PathLike, dst: PathLike) -> None`
移动文件或目录
- 参数：
  - `src`: 源路径
  - `dst`: 目标路径
- 返回：无

### 信息查询

#### `get_metadata(path: PathLike) -> Optional[FileMetadata]`
获取文件或目录的元数据
- 参数：
  - `path`: 路径
- 返回：元数据对象，不存在则返回 None

#### `list_dir(path: PathLike) -> List[str]`
列出目录内容
- 参数：
  - `path`: 目录路径
- 返回：目录下的文件和子目录名称列表

#### `exists(path: PathLike) -> bool`
检查路径是否存在
- 参数：
  - `path`: 检查路径
- 返回：存在返回 True，否则返回 False

#### `get_type(path: PathLike) -> FileType`
获取文件类型
- 参数：
  - `path`: 路径
- 返回：文件类型枚举值

## 类型定义

### PathLike
文件路径类型，可以是字符串或 Path 对象
```python
PathLike = Union[str, Path]