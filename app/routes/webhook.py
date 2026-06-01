"""
Webhook 路由
接收企业微信的消息，处理后返回回复
这是整个机器人的"总指挥"
"""
from decimal import Decimal
from datetime import date
from fastapi import APIRouter, Depends, Request, Body
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.crud import TransactionCRUD
from app.agent.parser import MessageParser
from app.services.statistics import StatisticsService
from app.services.formatter import MessageFormatter

# 创建路由
router = APIRouter()

@router.post("/webhook/wecom")
async def wecom_webhook(
    body: dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    企业微信机器人 Webhook
    
    流程：
    1. 接收消息
    2. 理解消息（解析意图）
    3. 执行操作（记账/查询/删除）
    4. 返回回复
    """
    
    # ========== 第1步：接收消息 ==========
    print("收到消息:", body)
    
    # 企业微信的消息格式
    msg_content = ""
    user_id = "unknown"
    user_name = "用户"
    
    # 提取消息内容
    if "text" in body:
        msg_content = body["text"].get("content", "")
    elif "msgContent" in body:
        msg_content = body.get("msgContent", "")
    
    # 提取用户信息
    if "from" in body:
        user_id = body["from"].get("userid", "unknown")
        user_name = body["from"].get("name", "用户")
    
    # 去除@机器人的部分（如果有的话）
    msg_content = msg_content.strip()
    
    # 如果消息为空
    if not msg_content:
        return {
            "msgtype": "text",
            "text": {"content": "请发送文字消息"}
        }
    
    # ========== 第2步：理解消息 ==========
    intent = MessageParser.parse_intent(msg_content)
    print("识别意图:", intent)
    
    # 创建工具对象
    crud = TransactionCRUD(db)
    stats = StatisticsService(db)
    
    # ========== 第3步：执行操作 ==========
    reply = ""
    
    # --- 帮助 ---
    if intent["intent"] == "help":
        reply = MessageFormatter.format_help()
    
    # --- 删除 ---
    elif intent["intent"] == "delete":
        success = crud.delete_last(user_id)
        if success:
            reply = MessageFormatter.format_delete_success()
        else:
            reply = MessageFormatter.format_delete_fail()
    
    # --- 周统计 ---
    elif intent["intent"] == "query_week":
        report = stats.get_weekly_report(user_id)
        if report['total'] == 0:
            reply = MessageFormatter.format_no_data("本周")
        else:
            reply = MessageFormatter.format_weekly_report(report)
    
    # --- 月统计 ---
    elif intent["intent"] == "query_month":
        report = stats.get_monthly_report(user_id)
        if report['total'] == 0:
            reply = MessageFormatter.format_no_data("本月")
        else:
            reply = MessageFormatter.format_monthly_report(report)
    
    # --- 分类统计 ---
    elif intent["intent"] == "query_category":
        cat = intent.get("category", "其他")
        report = stats.get_category_report(user_id, cat)
        reply = MessageFormatter.format_category_report(report)
    
    # --- 记账 ---
    elif intent["intent"] == "record":
        # 解析记账信息
        parsed = MessageParser.parse_transaction(msg_content)
        
        if "error" in parsed:
            # 解析失败
            reply = f"❌ {parsed['error']}\n\n发送 /help 查看使用说明"
        else:
            # 保存到数据库
            try:
                transaction = crud.create(
                    user_id=user_id,
                    amount=parsed["amount"],
                    category=parsed["category"],
                    note=parsed["note"],
                    user_name=user_name,
                    transaction_date=date.today()
                )
                # 格式化确认消息
                reply = MessageFormatter.format_transaction(
                    parsed["amount"],
                    parsed["category"],
                    parsed["note"]
                )
                print("记账成功:", transaction)
            except Exception as e:
                print("记账失败:", e)
                reply = f"❌ 记账失败，请重试\n\n发送 /help 查看使用说明"
    
    # --- 无法识别 ---
    else:
        reply = MessageFormatter.format_unknown()
    
    # ========== 第4步：返回回复 ==========
    print("回复消息:", reply)
    
    return {
        "msgtype": "text",
        "text": {
            "content": reply
        }
    }


@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "ok",
        "message": "记账助手运行中",
        "tips": "发送 /help 查看使用说明"
    }