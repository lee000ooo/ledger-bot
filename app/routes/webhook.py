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
    
    # --- 删除所有 ---
    elif intent["intent"] == "delete_all":
        count = crud.delete_all(user_id)
        if count > 0:
            reply = f"✅ 已删除全部 {count} 条记录"
        else:
            reply = "📊 没有可删除的记录"

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
                    transaction_date=parsed.get("transaction_date", date.today())
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




# ========== 飞书相关 ==========

import json
import httpx
from app.config import settings

@router.post("/webhook/feishu")
async def feishu_webhook(body: dict = Body(...), db: Session = Depends(get_db)):
    """
    飞书机器人 Webhook
    """
    print("飞书收到消息:", json.dumps(body, ensure_ascii=False, indent=2))
    
    # ========== URL 验证（首次配置时飞书会发验证请求） ==========
    if body.get("type") == "url_verification":
        challenge = body.get("challenge", "")
        print("URL验证，返回 challenge:", challenge)
        return {"challenge": challenge}
    
    # ========== 解析消息 ==========
    event = body.get("event", {})
    message = event.get("message", {})
    
    # 只处理文本消息
    if message.get("message_type") != "text":
        return {}
    
    # 提取消息内容
    content_str = message.get("content", "{}")
    content_json = json.loads(content_str)
    msg_content = content_json.get("text", "").strip()
    
    if not msg_content:
        return {}
    
    # 提取用户信息
    sender = event.get("sender", {})
    sender_id = sender.get("sender_id", {})
    user_id = sender_id.get("user_id") or sender_id.get("open_id", "unknown")
    
    print(f"飞书用户 {user_id} 发来: {msg_content}")
    
    # ========== 处理消息 ==========
    intent = MessageParser.parse_intent(msg_content)
    print("飞书识别意图:", intent)
    
    crud = TransactionCRUD(db)
    stats = StatisticsService(db)
    reply = ""
    
    if intent["intent"] == "help":
        reply = MessageFormatter.format_help()
    elif intent["intent"] == "delete":
        success = crud.delete_last(user_id)
        if success:
            reply = MessageFormatter.format_delete_success()
        else:
            reply = MessageFormatter.format_delete_fail()
    elif intent["intent"] == "delete_all":
        count = crud.delete_all(user_id)
        if count > 0:
            reply = f"✅ 已删除全部 {count} 条记录"
        else:
            reply = "📊 没有可删除的记录"
    elif intent["intent"] == "query_week":
        report = stats.get_weekly_report(user_id)
        if report['total'] == 0:
            reply = MessageFormatter.format_no_data("本周")
        else:
            reply = MessageFormatter.format_weekly_report(report)
    elif intent["intent"] == "query_month":
        report = stats.get_monthly_report(user_id)
        if report['total'] == 0:
            reply = MessageFormatter.format_no_data("本月")
        else:
            reply = MessageFormatter.format_monthly_report(report)
    elif intent["intent"] == "query_category":
        cat = intent.get("category", "其他")
        report = stats.get_category_report(user_id, cat)
        reply = MessageFormatter.format_category_report(report)
    elif intent["intent"] == "record":
        parsed = MessageParser.parse_transaction(msg_content)
        if "error" in parsed:
            reply = f"❌ {parsed['error']}\n\n发送 /help 查看使用说明"
        else:
            try:
                crud.create(
                    user_id=user_id,
                    amount=parsed["amount"],
                    category=parsed["category"],
                    note=parsed["note"],
                    user_name=user_id,
                    transaction_date=parsed.get("transaction_date", date.today())
                )
                reply = MessageFormatter.format_transaction(
                    parsed["amount"],
                    parsed["category"],
                    parsed["note"]
                )
            except Exception as e:
                print("记账失败:", e)
                reply = "❌ 记账失败，请重试"
    else:
        reply = MessageFormatter.format_unknown()
    
    # ========== 回复消息（后台异步，避免飞书重复推送） ==========
    message_id = message.get("message_id", "")
    if message_id and reply:
        import asyncio
        asyncio.create_task(reply_to_feishu(message_id, reply))
    
    # 立即返回，防止飞书超时重推
    return {}


async def reply_to_feishu(message_id: str, text: str):
    """回复飞书消息"""
    app_id = settings.FEISHU_APP_ID
    app_secret = settings.FEISHU_APP_SECRET
    
    if not app_id or not app_secret:
        print("❌ 未配置飞书 App ID 或 App Secret")
        return
    
    try:
        async with httpx.AsyncClient() as client:
            # 第1步：获取 token
            token_resp = await client.post(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                json={"app_id": app_id, "app_secret": app_secret}
            )
            token_data = token_resp.json()
            token = token_data.get("tenant_access_token", "")
            
            if not token:
                print("❌ 获取 token 失败:", token_data)
                return
            
            # 第2步：发送回复
            reply_data = {
                "content": json.dumps({"text": text}),
                "msg_type": "text"
            }
            
            reply_resp = await client.post(
                f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json=reply_data
            )
            print("飞书回复结果:", reply_resp.json())
            
    except Exception as e:
        print("飞书回复失败:", e)