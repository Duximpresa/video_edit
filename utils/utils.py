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


def generate_hash_code(text):
    text = text.encode('utf-8')
    hash_code = hashlib.sha256(text).hexdigest()
    return hash_code
