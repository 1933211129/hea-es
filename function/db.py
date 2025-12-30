DB_HOST = '10.0.32.32'       # 你的 Ubuntu 服务器 IP
DB_NAME = 'hea'             # 数据库名称
DB_USER = 'root'            # 数据库用户名
DB_PASSWORD = '123456'      # 数据库密码
DB_PORT = 5432              # PostgreSQL 默认端口

# -----------------------------------------------------------
# 用于连接的参数字典
# -----------------------------------------------------------

def get_connection_params():
    """返回一个字典，包含连接所需的所有参数。"""
    return {
        'host': DB_HOST,
        'database': DB_NAME,
        'user': DB_USER,
        'password': DB_PASSWORD,
        'port': DB_PORT
    }