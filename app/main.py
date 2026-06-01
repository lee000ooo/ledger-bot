"""
应用入口
FastAPI 主程序，负责启动整个服务
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import init_db
from app.routes.webhook import router as webhook_router
from app.config import settings

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="智能记账助手 - 支持企业微信"
)

# 允许跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 Webhook 路由
app.include_router(webhook_router, prefix="/api/v1")

# 启动时自动初始化数据库
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    init_db()
    print("=" * 50)
    print(f"🚀 {settings.APP_NAME} v{settings.VERSION} 启动成功！")
    print(f"📖 API 文档: http://localhost:8000/docs")
    print(f"💚 健康检查: http://localhost:8000/api/v1/health")
    print("=" * 50)

# 根路径
@app.get("/")
async def root():
    """根路径，显示欢迎信息"""
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "message": "欢迎使用智能记账助手！",
        "docs": "/docs",
        "health": "/api/v1/health"
    }