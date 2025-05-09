import os
from datetime import datetime
import hashlib


def root_dir():
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def storage_dir(sub_dir: str = "", create: bool = False):
    d = os.path.join(root_dir(), "storage")
    print(d)
    if sub_dir:
        d = os.path.join(d, sub_dir)
        print(d)
    if create and not os.path.exists(d):
        os.makedirs(d)

    return d


def check_dir_and_make_dir(dir_name):
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)


# 生成当前时间字符串名
def generate_datetime_string(prefix=None):
    # 获取当前的日期和时间
    now = datetime.now()
    # 将日期和时间格式化为字符串
    datetime_string = now.strftime("%Y-%m-%d_%H-%M-%S")
    # 返回带有前缀的日期和时间字符串
    if prefix is not None:
        return f"{prefix}_{datetime_string}"
    else:
        return f"{datetime_string}"

# 生成哈希码
def generate_hash_code(text):
    text = text.encode('utf-8')
    hash_code = hashlib.sha256(text).hexdigest()
    return hash_code

# 获取文件夹下的所有子文件夹的相对路径
def get_sorted_absolute_subdirectories(path):
    subdirs = []
    for root, dirs, _ in os.walk(path):
        for d in dirs:
            abs_dir = os.path.join(root, d)
            subdirs.append(abs_dir)
    subdirs.sort()
    return subdirs

def find_files_by_extensions(root_dir, extensions):
    """
    扫描指定根目录下的所有文件夹，查找指定后缀名的文件。

    Args:
        root_dir (str): 根目录路径。
        extensions (list): 文件后缀名列表，例如 ['.txt', '.pdf', '.jpg']。

    Returns:
        list: 符合条件的文件路径列表。
    """
    found_files = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if any(file.lower().endswith(ext.lower()) for ext in extensions):
                found_files.append(os.path.join(root, file))
    return found_files



def main():
    path = r'D:\DuximpresaProject\Github\video_edit\input\赫学熊\秋季长袖\2024_10_20\Video'
    for i in get_sorted_absolute_subdirectories(path):
        print(i)

if __name__ == "__main__":
    main()
