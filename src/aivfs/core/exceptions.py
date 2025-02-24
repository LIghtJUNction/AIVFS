"""AIVFS 异常类定义"""

class AIVFSError(Exception):
    """AIVFS 基础异常类"""
    pass

class FileSystemError(AIVFSError):
    """文件系统操作异常"""
    pass

class MetadataError(AIVFSError):
    """元数据操作异常"""
    pass

class PermissionError(AIVFSError):
    """权限相关异常"""
    def __init__(self, path: str, required_perm: str, message: str = None):
        self.path = path
        self.required_perm = required_perm
        super().__init__(
            message or f"没有足够权限访问 {path}，需要 {required_perm} 权限"
        )

class FileNotFoundError(AIVFSError):
    """文件不存在异常"""
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"文件不存在: {path}")

class DirectoryNotFoundError(AIVFSError):
    """目录不存在异常"""
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"目录不存在: {path}")

class FileExistsError(AIVFSError):
    """文件已存在异常"""
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"文件已存在: {path}")

class NotADirectoryError(AIVFSError):
    """不是目录异常"""
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"不是目录: {path}")

class IsADirectoryError(AIVFSError):
    """是目录异常"""
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"是目录: {path}")

class InvalidPathError(AIVFSError):
    """无效路径异常"""
    def __init__(self, path: str, reason: str = None):
        self.path = path
        super().__init__(
            f"无效路径 {path}" + (f": {reason}" if reason else "")
        )

class DatabaseError(AIVFSError):
    """数据库操作异常"""
    pass

class FileSizeError(AIVFSError):
    """文件大小异常"""
    def __init__(self, path: str, size: int, max_size: int):
        self.path = path
        self.size = size
        self.max_size = max_size
        super().__init__(
            f"文件 {path} 大小 ({size} bytes) 超过最大限制 ({max_size} bytes)"
        )