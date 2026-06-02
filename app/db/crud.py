"""
数据库增删改查操作
CRUD = Create(创建) + Read(读取) + Update(更新) + Delete(删除)
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import func, extract
from sqlalchemy.orm import Session
from app.db.models import Transaction

class TransactionCRUD:
    """交易记录的数据操作类"""
    
    def __init__(self, db: Session):
        """
        初始化，需要传入数据库会话
        就像告诉仓库管理员："这是仓库的钥匙"
        """
        self.db = db
    
    # ========== 创建 ==========
    
    def create(
        self,
        user_id: str,
        amount: Decimal,
        category: str,
        note: str = "",
        user_name: str = "",
        transaction_date: Optional[date] = None
    ) -> Transaction:
        """
        创建一条记账记录
        
        参数：
        - user_id: 用户ID（必填）
        - amount: 金额，负数=支出，正数=收入（必填）
        - category: 分类，如"餐饮"（必填）
        - note: 备注，如"肯德基"（可选）
        - user_name: 用户昵称（可选）
        - transaction_date: 交易日期，默认今天（可选）
        
        返回：创建好的记录
        """
        transaction = Transaction(
            user_id=user_id,
            user_name=user_name,
            amount=amount,
            category=category,
            note=note,
            transaction_date=transaction_date or date.today()
        )
        
        # 添加到数据库
        self.db.add(transaction)
        # 保存（提交）
        self.db.commit()
        # 刷新，获取自动生成的ID
        self.db.refresh(transaction)
        
        return transaction
    
    # ========== 查询 ==========
    
    def get_last_transaction(self, user_id: str) -> Optional[Transaction]:
        """
        获取用户最近一条记录
        
        参数：user_id - 用户ID
        返回：最近一条记录，没有则返回 None
        """
        return self.db.query(Transaction)\
            .filter(Transaction.user_id == user_id)\
            .order_by(Transaction.created_at.desc())\
            .first()
    
    def delete_last(self, user_id: str) -> bool:
        """
        删除用户最近一条记录
        
        参数：user_id - 用户ID
        返回：True=删除成功，False=没有可删的记录
        """
        last = self.get_last_transaction(user_id)
        if last:
            self.db.delete(last)
            self.db.commit()
            return True
        return False

    def delete_all(self, user_id: str) -> int:
        """
        删除用户所有记录
        
        返回：删除的条数
        """
        count = self.db.query(Transaction)\
            .filter(Transaction.user_id == user_id)\
            .delete()
        self.db.commit()
        return count

    # ========== 统计查询 ==========
    
    def get_week_expenses(self, user_id: str) -> List[Transaction]:
        """
        获取用户本周所有支出记录
        
        参数：user_id - 用户ID
        返回：本周的支出记录列表
        """
        today = date.today()
        # 计算本周一是几号
        monday = today - timedelta(days=today.weekday())
        
        return self.db.query(Transaction)\
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= monday,
                Transaction.amount < 0  # 只查支出（负数）
            )\
            .order_by(Transaction.transaction_date.desc())\
            .all()
    
    def get_month_expenses(self, user_id: str) -> List[Transaction]:
        """
        获取用户本月所有支出记录
        
        参数：user_id - 用户ID
        返回：本月的支出记录列表
        """
        today = date.today()
        
        return self.db.query(Transaction)\
            .filter(
                Transaction.user_id == user_id,
                extract('year', Transaction.transaction_date) == today.year,
                extract('month', Transaction.transaction_date) == today.month,
                Transaction.amount < 0
            )\
            .order_by(Transaction.transaction_date.desc())\
            .all()
    
    def get_category_summary(
        self, user_id: str, start_date: date, end_date: date
    ) -> List[dict]:
        """
        按分类汇总支出
        
        参数：
        - user_id: 用户ID
        - start_date: 开始日期
        - end_date: 结束日期
        
        返回示例：
        [
            {"category": "餐饮", "total": 350.50, "count": 8},
            {"category": "交通", "total": 120.00, "count": 5},
        ]
        """
        results = self.db.query(
            Transaction.category,
            func.sum(Transaction.amount).label('total'),
            func.count(Transaction.id).label('count')
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Transaction.amount < 0
        ).group_by(
            Transaction.category
        ).order_by(
            func.sum(Transaction.amount).asc()  # 按总额升序（花的多的在后面）
        ).all()
        
        return [
            {
                "category": r.category if r.category else "其他",
                "total": abs(float(r.total)),  # 转成正数方便显示
                "count": r.count
            }
            for r in results
        ]
    
    def get_daily_summary(
        self, user_id: str, start_date: date, end_date: date
    ) -> List[dict]:
        """
        按天汇总支出
        
        返回示例：
        [
            {"date": "2024-06-01", "total": 168.50},
            {"date": "2024-06-02", "total": 45.00},
        ]
        """
        results = self.db.query(
            Transaction.transaction_date,
            func.sum(Transaction.amount).label('total')
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Transaction.amount < 0
        ).group_by(
            Transaction.transaction_date
        ).order_by(
            Transaction.transaction_date
        ).all()
        
        return [
            {
                "date": str(r.transaction_date),
                "total": abs(float(r.total))
            }
            for r in results
        ]