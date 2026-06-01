"""
数据模型
定义数据库表的结构，就像 Excel 表格的表头
"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DECIMAL, Date, DateTime, Index
from app.db.database import Base

class Transaction(Base):
    """
    交易记录表
    每一行就是一笔记账记录
    """
    # 表名
    __tablename__ = "transactions"
    
    # === 字段定义 ===
    
    # 主键：每条记录的唯一编号，自动递增
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 用户ID：区分不同用户（飞书或企微的用户ID）
    user_id = Column(String(64), nullable=False, comment="用户ID")
    
    # 用户昵称：方便查看是谁记的账
    user_name = Column(String(128), comment="用户昵称")
    
    # 金额：正数=收入，负数=支出。用 DECIMAL 保证精确（不会出现 0.1+0.2=0.300000000004）
    amount = Column(DECIMAL(10, 2), nullable=False, comment="金额：正收入，负支出")
    
    # 分类：餐饮、交通、购物等
    category = Column(String(32), comment="分类")
    
    # 备注：消费的具体描述
    note = Column(String(256), comment="备注")
    
    # 交易日期：哪天花的钱
    transaction_date = Column(Date, nullable=False, default=date.today)
    
    # 创建时间：这条记录什么时候录入的
    created_at = Column(DateTime, default=datetime.now)
    
    # 更新时间
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 索引：加速查询
    __table_args__ = (
        Index('idx_user_date', 'user_id', 'transaction_date'),
        Index('idx_user_category', 'user_id', 'category'),
    )
    
    def to_dict(self):
        """把记录转成字典，方便输出"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "amount": float(self.amount),
            "category": self.category,
            "note": self.note,
            "transaction_date": str(self.transaction_date),
            "created_at": str(self.created_at)
        }
    
    def __repr__(self):
        """打印记录时显示的信息"""
        return f"<Transaction(金额={self.amount}, 分类={self.category}, 备注={self.note})>"