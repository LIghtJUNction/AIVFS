from pathlib import Path
import sqlite3
from typing import Optional, cast
from datetime import datetime
from ..core.interfaces import IFSOperations
from ..core.types import FileMetadata, FileType, Permission

class MetadataManager:
    """元数据管理器"""
    
    def __init__(self, root: Path):
        self.root = root
        self.db_path = root / 'etc' / 'aivfs' / 'metadata.db'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.fs_ops: Optional[IFSOperations] = None
        self._init_db()
    
    def set_fs_ops(self, fs_ops: IFSOperations) -> None:
        """设置文件系统操作实例"""
        self.fs_ops = fs_ops
    
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    path TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    file_group TEXT NOT NULL,
                    size INTEGER,
                    created_at INTEGER NOT NULL,
                    modified_at INTEGER NOT NULL,
                    user_perm INTEGER NOT NULL,
                    group_perm INTEGER NOT NULL,
                    other_perm INTEGER NOT NULL
                )
            """)

    def add_file(self, metadata: FileMetadata) -> None:
        """添加或更新文件元数据"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO metadata
                (path, type, owner, file_group, size, created_at, modified_at,
                 user_perm, group_perm, other_perm)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata.path,
                metadata.file_type.name,
                metadata.owner,
                metadata.group,
                metadata.size,
                int(metadata.created_at.timestamp()),
                int(metadata.modified_at.timestamp()),
                metadata.user_perm.to_mode(),
                metadata.group_perm.to_mode(),
                metadata.other_perm.to_mode()
            ))

    def get_file(self, path: str) -> Optional[FileMetadata]:
        """获取文件元数据"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM metadata WHERE path = ?",
                (path,)
            )
            row = cursor.fetchone()
            
            if row:
                return FileMetadata(
                    path=row[0],
                    file_type=FileType[row[1]],
                    owner=row[2],
                    group=row[3],
                    size=row[4],
                    created_at=datetime.fromtimestamp(row[5]),
                    modified_at=datetime.fromtimestamp(row[6]),
                    user_perm=Permission.from_mode(row[7]),
                    group_perm=Permission.from_mode(row[8]),
                    other_perm=Permission.from_mode(row[9])
                )
        return None

    def remove_file(self, path: str) -> None:
        """删除文件元数据"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM metadata WHERE path = ?", (path,))

    def close(self) -> None:
        """关闭数据库连接"""
        # SQLite会自动管理连接
        pass
