import aivfs
from pathlib import Path

# 初始化新的文件系统
fs = aivfs.init(force=True)  # 强制创建新的文件系统

def print_metadata(path: str):
    metadata = fs.get_metadata(path)
    if metadata:
        print(f"路径: {metadata.path}")
        print(f"类型: {metadata.file_type}")
        print(f"所有者: {metadata.owner}")
        print(f"组: {metadata.group}")
        print(f"大小: {metadata.size if metadata.size is not None else 'N/A'}")
        print(f"创建时间: {metadata.created_at}")
        print(f"修改时间: {metadata.modified_at}")
        print(f"权限: {metadata.user_perm}-{metadata.group_perm}-{metadata.other_perm}")
        print("-" * 50)
    else:
        print(f"未找到 {path} 的元数据")

# 创建一些测试文件和目录
fs.create_file("/home/test.txt", "Hello World", owner="user1", group="users")
fs.mkdir("/home/docs", owner="user1", group="users", exist_ok=True)

# 测试元数据
print("根目录元数据:")
print_metadata("/")

print("\n/home 目录元数据:")
print_metadata("/home")

print("\n/home/test.txt 文件元数据:")
print_metadata("/home/test.txt")

print("\n/home/docs 目录元数据:")
print_metadata("/home/docs")

# 显示目录内容
print("\n列出 /home 目录内容:")
for entry in fs.metadata.list_dir("/home"):
    print(f"- {entry.path} ({entry.file_type})")



