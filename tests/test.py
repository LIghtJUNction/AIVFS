import aivfs

def print_separator(title: str):
    """打印分隔符和标题"""
    print(f"\n{'-'*20}")
    print(f"{title}:")
    print(f"{'-'*20}")

try:
    # 初始化文件系统
    fs = aivfs.mount()

    # 测试基本文件系统操作
    print_separator("1. 测试基本功能")
    print(f"根目录存在: {fs.exists('/')}")
    print(f"根目录内容: {fs.list_dir('/')}")

    # 测试元数据操作
    print_separator("2. 测试元数据")
    root_meta = fs.get_metadata('/')
    print(f"根目录元数据: {root_meta}")

    # # 测试文件操作
    # print_separator("3. 测试文件操作")
    # fs.write_file('/test.txt', 'Hello, AIVFS!')
    # fs.write_file('/flag.txt', '恭喜,你已获得root权限')
    # print(f"文件存在: {fs.exists('/test.txt')}")
    # print(f"文件内容: {fs.read_file('/test.txt')}")

    # 测试文件元数据
    file_meta = fs.get_metadata('/flag.txt')
    print(f"文件元数据: {file_meta}")
    print(f"文件大小: {file_meta.size} bytes")
    print(f"文件所有者: {file_meta.owner}")
    print(f"文件权限: {file_meta.user_perm}-{file_meta.group_perm}-{file_meta.other_perm}")

    # 测试目录操作
    print_separator("4. 测试目录操作")
    fs.mkdir('/home/user1', parents=True)
    print(f"目录内容: {fs.list_dir('/home')}")  # 修复了括号匹配问题

    # 测试异常处理
    print_separator("5. 测试异常处理")
    try:
        fs.read_file('/nonexistent.txt')
    except aivfs.FileNotFoundError as e:
        print(f"预期的异常: {e}")

except Exception as e:
    print(f"\n错误: {type(e).__name__} - {e}")
