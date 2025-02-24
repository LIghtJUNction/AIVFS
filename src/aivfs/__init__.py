"""AIVFS - 一个基于元数据的AI虚拟文件系统

AIVFS 提供了一个类 Unix 的虚拟文件系统实现，支持：
1. 文件和目录的基本操作（创建、读写、复制、移动、删除）
2. 类 Unix 的文件权限管理（用户、组、其他用户权限）
3. 元数据管理（权限、所有者、时间戳）
4. 文件系统挂载和初始化
5. 文件系统遍历和搜索
6. 磁盘使用情况统计

基本使用:
    >>> import aivfs
    >>> # 创建新的文件系统
    >>> fs = aivfs.init('my_fs', force=True)
    >>> # 写入文件
    >>> fs.write_file('/home/test.txt', 'Hello World')
    >>> # 读取文件
    >>> content = fs.read_file('/home/test.txt')
    >>> # 挂载已存在的文件系统
    >>> fs = aivfs.mount('my_fs')
"""

from pathlib import Path
from typing import Optional, Union
from .core.types import PathLike, FileMode, FileType, Permission
from .core.exceptions import (
    AIVFSError, FileSystemError, PermissionError,
    FileNotFoundError, InvalidPathError
)
# 最后导入 AIVFS
from .core.fs import AIVFS

# 设置基本目录的权限和所有者
DIR_PERMISSIONS = {
    'home': {
        'owner': lambda o, g: (o, g),           # 继承创建者的权限
        'mode': FileMode(7, 5, 5),              # rwxr-xr-x
        'subdirs': ['public']                   # 预创建子目录
    },
    'tmp': {
        'owner': lambda o, g: ('root', 'users'),
        'mode': FileMode(7, 7, 7),              # rwxrwxrwx
        'cleanup': True                         # 启动时清理
    },
    'var': {
        'owner': lambda o, g: ('root', 'root'),
        'mode': FileMode(7, 5, 0),              # rwxr-x---
        'subdirs': ['log', 'run', 'cache']      # 系统运行时目录
    },
    'etc': {
        'owner': lambda o, g: ('root', 'root'),
        'mode': FileMode(7, 4, 4),              # rwxr--r--
        'subdirs': ['aivfs', 'security']        # 配置目录
    },
    'usr': {
        'owner': lambda o, g: ('root', 'root'),
        'mode': FileMode(7, 5, 5),              # rwxr-xr-x
        'subdirs': ['bin', 'lib', 'share']      # 用户程序目录
    }
}

def init(path: Optional[PathLike] = None, 
         force: bool = False,
         owner: str = "root",
         group: str = "root") -> AIVFS:
    """初始化AIVFS文件系统
    
    创建一个新的AIVFS文件系统实例。如果目标目录已存在，可以通过force参数
    强制删除现有目录并重新创建。
    
    Args:
        path: 文件系统路径，默认为当前目录下的aivfs_root
        force: 是否强制创建，如果为True则会删除已存在的目录
        owner: 文件系统所有者，默认为root
        group: 文件系统所属组，默认为root
        
    Returns:
        AIVFS: 文件系统实例
        
    Raises:
        ValueError: 目录已存在且force=False时
        PermissionError: 没有足够权限创建或删除目录时
        AIVFSError: 文件系统创建失败时
    
    Examples:
        >>> fs = aivfs.init('my_fs', force=True)
        >>> fs.write_file('/test.txt', 'Hello')
    """
    try:
        root = Path(path or 'aivfs_root').absolute()
        
        if root.exists():
            if not force:
                raise ValueError(f"目录已存在: {root}")
            try:
                import shutil
                shutil.rmtree(root)
            except PermissionError:
                raise PermissionError(f"无法删除目录 {root}，请检查权限")
            except Exception as e:
                raise AIVFSError(f"删除现有目录失败: {e}")
        
        fs = AIVFS.create(root, force)
        
        # 初始化和设置基本目录结构
        for dir_name, config in DIR_PERMISSIONS.items():
            path = f'/{dir_name}'
            if not fs.exists(path):
                continue
                
            # 设置目录所有者和权限
            dir_owner, dir_group = config['owner'](owner, group)
            fs.chown(path, dir_owner, dir_group)
            fs.chmod(path, config['mode'])
            
            # 创建子目录
            if 'subdirs' in config:
                for subdir in config['subdirs']:
                    subpath = f'{path}/{subdir}'
                    if not fs.exists(subpath):
                        fs.mkdir(subpath, 
                                 owner=dir_owner,
                                 group=dir_group,
                                 mode=config['mode'],
                                 parents=True)
            
            # 清理临时目录
            if config.get('cleanup', False):
                for item in fs.list_dir(path):
                    try:
                        fs.remove(f'{path}/{item}', recursive=True)
                    except Exception as e:
                        print(f"警告: 清理 {path}/{item} 失败: {e}")
        
        # 创建用户主目录（如果指定了非root用户）
        if owner != "root":
            user_home = f'/home/{owner}'
            if not fs.exists(user_home):
                fs.mkdir(user_home,
                         owner=owner,
                         group=group,
                         mode=FileMode(7, 0, 0),  # rwx------
                         parents=True)
                
                # 创建用户配置目录
                fs.mkdir(f'{user_home}/.config',
                         owner=owner,
                         group=group,
                         mode=FileMode(7, 0, 0))
        
        return fs
        
    except (ValueError, PermissionError) as e:
        raise e
    except Exception as e:
        raise AIVFSError(f"创建文件系统失败: {e}")

def mount(path: Optional[PathLike] = None) -> AIVFS:
    """挂载已存在的AIVFS文件系统
    
    将现有的AIVFS文件系统挂载到程序中。目标目录必须包含有效的AIVFS文件系统
    结构（包括.aivroot文件和元数据数据库）。
    
    Args:
        path: 文件系统路径，默认为当前目录下的aivfs_root
        
    Returns:
        AIVFS: 文件系统实例
        
    Raises:
        ValueError: 目录不存在或不是有效的AIVFS文件系统
        PermissionError: 没有足够权限访问目录
        AIVFSError: 文件系统挂载失败时
        
    Examples:
        >>> fs = aivfs.mount('my_fs')
        >>> content = fs.read_file('/test.txt')
    """
    try:
        root = Path(path or 'aivfs_root').absolute()
        
        if not root.exists():
            raise ValueError(f"目录不存在: {root}")
            
        if not (root / '.aivroot').exists():
            raise ValueError(f"不是有效的AIVFS文件系统: {root}")
            
        return AIVFS.mount(root)
        
    except (ValueError, PermissionError) as e:
        raise e
    except Exception as e:
        raise AIVFSError(f"挂载文件系统失败: {e}")

# 版本信息
__version__ = '1.0.0'
__author__ = 'LIghtJUNction'
__license__ = 'MIT'
__description__ = '一个AI虚拟文件系统'
__url__ = 'https://github.com/LIghtJUNction/AIVFS'

# 公开的接口
__all__ = [
    # 主要功能
    'init',           # 初始化文件系统
    'mount',          # 挂载文件系统
    
    # 核心类
    'AIVFS',         # 文件系统类
    'FileMode',      # 文件权限模式
    'FileType',      # 文件类型
    'Permission',    # 权限类
    
    # 类型
    'PathLike',      # 路径类型
    
    # 异常
    'AIVFSError',    # 基础异常
    'FileSystemError',# 文件系统异常
    'PermissionError',# 权限异常
    'FileNotFoundError',# 文件未找到异常
    'InvalidPathError'# 无效路径异常
]