"""
配置文件 - 存储API密钥和其他配置信息
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ChatAnywhere API 配置
CHATANYWHERE_API_KEY = os.getenv("CHATANYWHERE_API_KEY")
CHATANYWHERE_API_URL = "https://api.chatanywhere.tech/v1/chat/completions"
CHATANYWHERE_MODEL = "deepseek-v3.2"

# 其他配置
MAX_RETRIES = 5
MAX_TOKENS = 16384
TEMPERATURE = 0.1