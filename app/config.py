"""
配置管理
集中管理所有配置，方便以后修改
"""
import os
from dotenv import load_dotenv

# 加载 .env 文件里的配置
load_dotenv()

class Settings:
    """应用的所有配置"""
    
    # 数据库地址
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./ledger.db")
    
    # 企业微信
    WECOM_TOKEN: str = os.getenv("WECOM_TOKEN", "")
    
    # AI（暂时不用）
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    
    # 应用信息
    APP_NAME: str = "智能记账助手"
    VERSION: str = "1.0.0"

    # 飞书
    FEISHU_APP_ID: str = os.getenv("FEISHU_APP_ID", "")
    FEISHU_APP_SECRET: str = os.getenv("FEISHU_APP_SECRET", "")




# 创建一个全局实例，其他文件直接导入这个就能用
settings = Settings()