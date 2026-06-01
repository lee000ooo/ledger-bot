"""
消息格式化服务
把数据变成好看的文本消息
"""
from decimal import Decimal
from datetime import date

class MessageFormatter:
    """消息格式化器"""
    
    # 每个分类对应的 emoji 图标
    CATEGORY_EMOJI = {
        "餐饮": "🍜",
        "交通": "🚇",
        "购物": "🛒",
        "娱乐": "🎮",
        "住房": "🏠",
        "水电": "💡",
        "医疗": "💊",
        "教育": "📚",
        "工资": "💰",
        "奖金": "🎁",
        "兼职": "💼",
        "投资": "📈",
        "其他": "📌",
        "其他收入": "💵",
    }
    
    @classmethod
    def format_transaction(cls, amount: Decimal, category: str, note: str) -> str:
        """
        格式化单笔交易确认消息
        
        示例输出：
        ✅ 已记录支出
        🍜 金额：¥68.00
        📂 分类：餐饮
        📝 备注：肯德基午餐
        """
        emoji = cls.CATEGORY_EMOJI.get(category, "📌")
        
        if amount < 0:
            # 支出
            return (
                f"✅ 已记录支出\n"
                f"{emoji} 金额：¥{abs(amount):.2f}\n"
                f"📂 分类：{category}\n"
                f"📝 备注：{note}"
            )
        else:
            # 收入
            return (
                f"✅ 已记录收入\n"
                f"{emoji} 金额：¥{amount:.2f}\n"
                f"📂 分类：{category}\n"
                f"📝 备注：{note}"
            )
    
    @classmethod
    def format_weekly_report(cls, report: dict) -> str:
        """
        格式化周报
        
        示例输出：
        📊 本周支出统计
        📅 2024-06-03 ~ 2024-06-09
        
        📋 分类汇总：
          🍜 餐饮: ¥350.50 (8笔)
          🚇 交通: ¥120.00 (5笔)
          🛒 购物: ¥520.00 (3笔)
        
        💰 总支出：¥990.50
        📈 日均：¥141.50
        """
        lines = []
        lines.append("📊 本周支出统计")
        lines.append(f"📅 {report['period']}")
        lines.append("")
        lines.append("📋 分类汇总：")
        
        # 每个分类一行
        for cat in report['categories']:
            emoji = cls.CATEGORY_EMOJI.get(cat['category'], "📌")
            lines.append(
                f"  {emoji} {cat['category']}: "
                f"¥{cat['total']:.2f} "
                f"({cat['count']}笔)"
            )
        
        lines.append("")
        lines.append(f"💰 总支出：¥{report['total']:.2f}")
        
        # 日均
        daily_avg = report['total'] / 7
        lines.append(f"📈 日均：¥{daily_avg:.2f}")
        
        return "\n".join(lines)
    
    @classmethod
    def format_monthly_report(cls, report: dict) -> str:
        """
        格式化月报
        
        示例输出：
        📊 本月支出统计
        📅 2024-06-01 ~ 2024-06-09
        
        📋 分类汇总：
          🍜 餐饮: ¥1350.50 (18笔)
          🚇 交通: ¥320.00 (12笔)
        
        💰 总支出：¥2890.50
        📈 日均：¥321.17
        """
        lines = []
        lines.append("📊 本月支出统计")
        lines.append(f"📅 {report['period']}")
        lines.append("")
        lines.append("📋 分类汇总：")
        
        for cat in report['categories']:
            emoji = cls.CATEGORY_EMOJI.get(cat['category'], "📌")
            lines.append(
                f"  {emoji} {cat['category']}: "
                f"¥{cat['total']:.2f} "
                f"({cat['count']}笔)"
            )
        
        lines.append("")
        lines.append(f"💰 总支出：¥{report['total']:.2f}")
        
        # 日均（按本月已过天数算）
        today = date.today()
        days_passed = today.day
        if days_passed > 0:
            daily_avg = report['total'] / days_passed
            lines.append(f"📈 日均：¥{daily_avg:.2f}")
        
        return "\n".join(lines)
    
    @classmethod
    def format_category_report(cls, report: dict) -> str:
        """
        格式化分类统计
        
        示例输出：
        📊 餐饮 本月统计
        🍜 总支出：¥350.50
        📝 笔数：8笔
        📅 2024-06-01 ~ 2024-06-09
        """
        emoji = cls.CATEGORY_EMOJI.get(report['category'], "📌")
        
        lines = []
        lines.append(f"📊 {report['category']} 本月统计")
        lines.append(f"{emoji} 总支出：¥{report['total']:.2f}")
        lines.append(f"📝 笔数：{report['count']}笔")
        lines.append(f"📅 {report['period']}")
        
        return "\n".join(lines)
    
    @classmethod
    def format_help(cls) -> str:
        """格式化帮助信息"""
        return (
            "🤖 记账助手使用指南\n"
            "\n"
            "📝 记账\n"
            "• 午餐 68 肯德基\n"
            "• 打车 25 去公司\n"
            "• 工资 15000 到账\n"
            "• 买衣服 299\n"
            "\n"
            "📊 查询\n"
            "• /周统计 - 查看本周开销\n"
            "• /月统计 - 查看本月开销\n"
            "• /餐饮统计 - 查看特定分类\n"
            "\n"
            "🗑️ 删除\n"
            "• /删除 - 删除最近一笔\n"
            "\n"
            "❓ 帮助\n"
            "• /help - 显示此帮助\n"
            "\n"
            "💡 提示：消息中包含数字就会被识别为记账"
        )
    
    @classmethod
    def format_delete_success(cls) -> str:
        """删除成功消息"""
        return "✅ 已删除最近一笔记录"
    
    @classmethod
    def format_delete_fail(cls) -> str:
        """删除失败消息"""
        return "❌ 没有可删除的记录"
    
    @classmethod
    def format_unknown(cls) -> str:
        """无法识别的消息"""
        return "🤔 我没有理解你的意思\n发送 /help 查看使用说明"
    
    @classmethod
    def format_no_data(cls, period: str) -> str:
        """没有数据"""
        return f"📊 {period}还没有支出记录哦"