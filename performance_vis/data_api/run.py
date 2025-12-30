"""
API 服务启动脚本
唯一启动方式：python -m data_api.run
"""
import uvicorn
from .api import app
from .config import API_HOST, API_PORT

if __name__ == "__main__":
    uvicorn.run(app, host=API_HOST, port=API_PORT)
