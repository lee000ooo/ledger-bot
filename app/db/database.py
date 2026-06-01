"""
数据库连接管理
负责创建数据库、连接数据库
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

# 创建数据库引擎
# 这就像是"打开数据库程序"
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,  # 设为 True 可以看到 SQL 语句（调试时用）
    connect_args={"check_same_thread": False}  # SQLite 需要这个
)

# 创建会话工厂
# 每次操作数据库，都要通过这个"会话"
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基类，所有数据库表都要继承这个
class Base(DeclarativeBase):
    pass

# 获取数据库会话
def get_db():
    """每次请求获取一个数据库连接"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 创建所有表
def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库初始化完成")