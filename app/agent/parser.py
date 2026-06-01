"""
消息解析引擎
负责理解用户发来的消息是什么意思
比如："午餐 68 肯德基" → 金额=68, 分类=餐饮, 备注=肯德基
"""
import re
from decimal import Decimal
from typing import Optional

class MessageParser:
    """消息解析器"""
    
    # 分类关键词字典
    # 如果用户消息里包含这些词，就自动归类
    CATEGORY_KEYWORDS = {
        "餐饮": [
            "餐", "饭", "外卖", "食堂", "肯德基", "麦当劳", "奶茶", 
            "咖啡", "饮料", "零食", "水果", "午饭", "晚饭", "早餐", 
            "午餐", "晚餐", "吃", "喝", "烧烤", "火锅", "面", "米线"
        ],
        "交通": [
            "打车", "滴滴", "地铁", "公交", "加油", "停车", "出租", 
            "高铁", "机票", "火车", "单车", "共享"
        ],
        "购物": [
            "买", "购", "淘宝", "京东", "拼多多", "衣服", "鞋", 
            "手机", "电脑", "日用品", "超市", "商场"
        ],
        "娱乐": [
            "电影", "游戏", "KTV", "唱歌", "旅游", "门票", "游乐", 
            "演出", "演唱会"
        ],
        "住房": ["房租", "房贷", "物业", "租房"],
        "水电": ["电费", "水费", "燃气", "话费", "网费", "宽带"],
        "医疗": ["药", "医院", "挂号", "看病", "检查"],
        "教育": ["书", "课程", "培训", "学费"],
        "工资": ["工资", "薪水", "发工资", "年终奖", "奖金"],
        "兼职": ["兼职", "副业", "外快"],
        "投资": ["股票", "基金", "理财", "利息", "分红"],
    }
    
    @classmethod
    def parse_intent(cls, text: str) -> dict:
        """
        判断用户想干什么
        
        返回示例：
        {"intent": "record"}           → 记账
        {"intent": "query_week"}       → 查周统计
        {"intent": "query_month"}      → 查月统计
        {"intent": "query_category", "category": "餐饮"}  → 查分类
        {"intent": "delete"}           → 删除
        {"intent": "help"}             → 帮助
        {"intent": "unknown"}          → 不知道
        """
        text = text.strip()
        
        # 帮助
        if text in ["/help", "帮助", "help", "？", "?", "/帮助"]:
            return {"intent": "help"}
        
        # 删除
        if text in ["/delete", "删除", "撤销", "撤回", "删掉", "/删除"]:
            return {"intent": "delete"}
        
        # 周统计
        if any(kw in text for kw in ["/week", "/周统计", "周统计", "本周", "这周"]):
            return {"intent": "query_week"}
        
        # 月统计
        if any(kw in text for kw in ["/month", "/月统计", "月统计", "本月", "这个月"]):
            return {"intent": "query_month"}
        
        # 分类统计，比如 "/餐饮统计" 或 "餐饮统计"
        match = re.search(r'[/]?(\S+)统计', text)
        if match:
            cat = match.group(1)
            return {"intent": "query_category", "category": cat}
        
        # 如果包含数字，认为是要记账
        if cls._has_amount(text):
            return {"intent": "record"}
        
        # 无法识别
        return {"intent": "unknown"}
    
    @classmethod
    def _has_amount(cls, text: str) -> bool:
        """检查消息里有没有数字（金额）"""
        return bool(re.search(r'\d+', text))
    
    @classmethod
    def parse_transaction(cls, text: str) -> dict:
        """
        从消息中解析出记账信息
        
        输入："午餐 68 肯德基"
        输出：{"amount": -68.00, "category": "餐饮", "note": "午餐 肯德基"}
        """
        # 1. 提取金额
        amount = cls._extract_amount(text)
        if amount is None:
            return {"error": "没有找到金额，请加上数字，比如：午餐 68 肯德基"}
        
        # 2. 识别分类
        category = cls._classify_category(text)
        
        # 3. 提取备注
        note = cls._extract_note(text)
        
        return {
            "amount": amount,
            "category": category,
            "note": note
        }
    
    @classmethod
    def _extract_amount(cls, text: str) -> Optional[Decimal]:
        """
        从消息中提取金额
        
        规则：
        - 默认是支出（负数）
        - 如果包含"收入""工资""奖金""赚"等词，则是收入（正数）
        """
        # 找到第一个数字
        match = re.search(r'(\d+\.?\d*)', text)
        if not match:
            return None
        
        amount = Decimal(match.group(1))
        
        # 判断收入还是支出
        income_keywords = ["收入", "工资", "奖金", "赚", "进账", "兼职", "到账", "发工资"]
        if any(kw in text for kw in income_keywords):
            return abs(amount)  # 收入为正数
        else:
            return -abs(amount)  # 支出为负数
    
    @classmethod
    def _classify_category(cls, text: str) -> str:
        """
        自动识别消费分类
        
        遍历关键词字典，看消息里包含哪个分类的关键词
        """
        for category, keywords in cls.CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    return category
        
        # 如果没匹配到，判断是收入还是支出
        income_keywords = ["收入", "工资", "奖金", "赚", "兼职", "到账"]
        if any(kw in text for kw in income_keywords):
            if "工资" in text:
                return "工资"
            elif "奖金" in text:
                return "奖金"
            elif "兼职" in text:
                return "兼职"
            return "其他收入"
        
        # 啥都没匹配到
        return "其他"
    
    @classmethod
    def _extract_note(cls, text: str) -> str:
        """
        提取备注（去掉数字后的文字）
        
        输入："午餐 68 肯德基"
        去掉数字后："午餐  肯德基"
        清理后："午餐 肯德基"
        """
        # 去掉数字
        note = re.sub(r'\d+\.?\d*', '', text)
        # 去掉多余空格
        note = re.sub(r'\s+', ' ', note)
        # 去掉首尾空格
        note = note.strip()
        return note