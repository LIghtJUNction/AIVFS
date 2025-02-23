from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Optional, Set

class FileType(Enum):
    """文件类型枚举"""
    REGULAR = auto()     # 普通文件（替换原来的FILE）
    DIRECTORY = auto()   # 目录
    SYMLINK = auto()     # 符号链接
    SPECIAL = auto()     # 特殊文件（新增）

@dataclass
class Permission:
    """权限类"""
    read: bool = False
    write: bool = False
    execute: bool = False
    
    @classmethod
    def from_mode(cls, mode: int) -> 'Permission':
        """从数字模式创建权限对象"""
        return cls(
            read=bool(mode & 4),
            write=bool(mode & 2),
            execute=bool(mode & 1)
        )
    
    def to_mode(self) -> int:
        """转换为数字模式"""
        mode = 0
        if self.read: mode |= 4
        if self.write: mode |= 2
        if self.execute: mode |= 1
        return mode
    
    def to_unix_style(self) -> str:
        """转换为Unix风格的权限字符串"""
        return (
            ('r' if self.read else '-') +
            ('w' if self.write else '-') +
            ('x' if self.execute else '-')
        )

@dataclass
class FileMetadata:
    """文件元数据（替换原来的Metadata）"""
    path: str
    file_type: FileType
    owner: str
    group: str
    size: Optional[int]
    created_at: datetime
    modified_at: datetime
    user_perm: Permission
    group_perm: Permission
    other_perm: Permission

    def get_permissions(self) -> str:
        """获取Unix风格的完整权限字符串"""
        type_char = {
            FileType.DIRECTORY: 'd',
            FileType.SYMLINK: 'l',
            FileType.REGULAR: '-',
            FileType.SPECIAL: 's'
        }[self.file_type]
        
        return (
            type_char +
            self.user_perm.to_unix_style() +
            self.group_perm.to_unix_style() +
            self.other_perm.to_unix_style()
        )

    def has_permission(self, username: str, groups: Set[str], check_perm: Permission) -> bool:
        """检查用户是否有指定的权限"""
        if username == self.owner:
            return (
                (not check_perm.read or self.user_perm.read) and
                (not check_perm.write or self.user_perm.write) and
                (not check_perm.execute or self.user_perm.execute)
            )
            
        if self.group in groups:
            return (
                (not check_perm.read or self.group_perm.read) and
                (not check_perm.write or self.group_perm.write) and
                (not check_perm.execute or self.group_perm.execute)
            )
            
        return (
            (not check_perm.read or self.other_perm.read) and
            (not check_perm.write or self.other_perm.write) and
            (not check_perm.execute or self.other_perm.execute)
        )