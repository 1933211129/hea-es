"""
FastAPI 应用主文件
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import (
    API_TITLE,
    API_VERSION,
    IMAGE_DIR,
    PDF_DIR,
    CORS_ORIGINS,
    CORS_CREDENTIALS,
    CORS_METHODS,
    CORS_HEADERS
)
from .routes import papers, root, feedback


def create_app() -> FastAPI:
    """
    创建并配置 FastAPI 应用
    
    Returns:
        FastAPI: 配置好的 FastAPI 应用实例
    """
    # 创建 FastAPI 应用
    app = FastAPI(title=API_TITLE, version=API_VERSION)
    
    # 挂载图片目录
    app.mount("/static_images", StaticFiles(directory=IMAGE_DIR), name="static_images")
    
    # 挂载 PDF 目录
    app.mount("/static_pdfs", StaticFiles(directory=PDF_DIR), name="static_pdfs")
    
    # 配置 CORS（允许跨域请求）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=CORS_CREDENTIALS,
        allow_methods=CORS_METHODS,
        allow_headers=CORS_HEADERS,
    )
    
    # 注册路由
    app.include_router(root.router)
    app.include_router(papers.router)
    app.include_router(feedback.router)
    
    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn
    from .config import API_HOST, API_PORT
    
    uvicorn.run(app, host=API_HOST, port=API_PORT)

