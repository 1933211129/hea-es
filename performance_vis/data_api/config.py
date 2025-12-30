"""
API 配置项
"""
from pathlib import Path

# 数据库配置
DB_HOST = '10.0.32.32'
DB_NAME = 'hea'
DB_USER = 'root'
DB_PASSWORD = '123456'
DB_PORT = 5432

# 优先显示的论文 identifier 列表（按顺序）
PRIORITY_IDENTIFIERS = [
    '964e909e7be3f7be1dbebde6285bfdf5',
    '20cdf2e71a891ee72b71d19bb659543b',
    '08052e05207e767a5e040c5738327f3c',
    '0b0a35b64be8126224dceff2a1e436f4',
    '1640967f0d19ba37c4acd00053d4679c',
    '78e90ba9c7ee2d2b94b93fd5ce8c0fd3',
    'bbdce4825323017dbdd9fab04d4e6a91'
]

# 图片目录路径
IMAGE_DIR = "/Users/xiaokong/task/2025/electrocatalysis/extract/result"

# PDF 目录路径
PDF_DIR = "/Users/xiaokong/task/2025/electrocatalysis/ref"

# API 配置
API_TITLE = "HEA 论文性能数据 API"
API_VERSION = "1.0.0"
API_HOST = "0.0.0.0"
API_PORT = 8003

# CORS 配置
CORS_ORIGINS = ["*"]  # 生产环境应该限制具体域名
CORS_CREDENTIALS = True
CORS_METHODS = ["*"]
CORS_HEADERS = ["*"]

