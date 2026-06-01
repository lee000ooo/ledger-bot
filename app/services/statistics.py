"""
统计服务
负责从数据库查询数据，整理成报告
"""
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.db.crud import TransactionCRUD

class StatisticsService:
    """统计服务"""
    
    def __init__(self, db: Session):
        """初始化，需要传入数据库会话"""
        self.crud = TransactionCRUD(db)
    
    def get_weekly_report(self, user_id: str) -> dict:
        """
        生成本周报告
        
        返回格式：
        {
            "period": "2024-06-03 ~ 2024-06-09",
            "total": 990.50,
            "categories": [
                {"category": "餐饮", "total": 350.50, "count": 8},
                ...
            ]
        }
        """
        today = date.today()
        # 本周一
        monday = today - timedelta(days=today.weekday())
        # 本周日
        sunday = monday + timedelta(days=6)
        
        # 查询分类汇总
        categories = self.crud.get_category_summary(user_id, monday, sunday)
        
        # 计算总支出
        total = sum(c['total'] for c in categories)
        
        return {
            "period": f"{monday} ~ {sunday}",
            "total": round(total, 2),
            "categories": categories
        }
    
    def get_monthly_report(self, user_id: str) -> dict:
        """
        生成本月报告
        """
        today = date.today()
        # 本月1号
        first_day = today.replace(day=1)
        
        # 查询分类汇总
        categories = self.crud.get_category_summary(user_id, first_day, today)
        
        # 计算总支出
        total = sum(c['total'] for c in categories)
        
        return {
            "period": f"{first_day} ~ {today}",
            "total": round(total, 2),
            "categories": categories
        }
    
    def get_category_report(self, user_id: str, category: str) -> dict:
        """
        查询特定分类的统计
        """
        today = date.today()
        first_day = today.replace(day=1)
        
        # 先获取所有分类的汇总
        all_categories = self.crud.get_category_summary(user_id, first_day, today)
        
        # 找到目标分类
        target = None
        for c in all_categories:
            if c['category'] == category:
                target = c
                break
        
        return {
            "category": category,
            "period": f"{first_day} ~ {today}",
            "total": target['total'] if target else 0,
            "count": target['count'] if target else 0
        }