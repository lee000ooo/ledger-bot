"""
Webhook 路由
接收企业微信和飞书的消息，处理后返回回复
"""
from decimal import Decimal
from datetime import date
from fastapi import APIRouter, Depends, Request, Body
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.crud import TransactionCRUD
from app.agent.parser import MessageParser
from app.services.statistics import StatisticsService
from app.services.formatter import MessageFormatter

import json
import httpx
from app.config import settings

# 创建路由
router = APIRouter()


# ==================== 企业微信 ====================

@router.get("/webhook/wecom")
async def wecom_verify(
    msg_signature: str = "",
    timestamp: str = "",
    nonce: str = "",
    echostr: str = ""
):
    """企业微信 URL 验证（GET 请求）"""
    import hashlib
    import base64
    import struct
    from Crypto.Cipher import AES

    token = settings.WECOM_TOKEN
    encoding_aes_key = settings.WECOM_ENCODING_AES_KEY

    tmp_list = sorted([token, timestamp, nonce, echostr])
    tmp_str = "".join(tmp_list)
    sign = hashlib.sha1(tmp_str.encode()).hexdigest()

    if sign != msg_signature:
        print("企微验证签名失败")
        return PlainTextResponse(content="signature failed")

    aes_key = base64.b64decode(encoding_aes_key + "=")
    cipher = AES.new(aes_key, AES.MODE_CBC, aes_key[:16])
    plain_text = cipher.decrypt(base64.b64decode(echostr))

    pad = plain_text[-1]
    content = plain_text[16:-pad]
    msg_len = struct.unpack(">I", content[:4])[0]
    msg = content[4:4+msg_len].decode()

    print("企微URL验证成功，返回:", msg)
    return PlainTextResponse(content=msg)


@router.post("/webhook/wecom")
async def wecom_webhook(request: Request, db: Session = Depends(get_db)):
    """企业微信机器人 Webhook（POST 请求）"""
    import hashlib
    import base64
    import struct
    from Crypto.Cipher import AES
    import xml.etree.ElementTree as ET

    params = request.query_params
    msg_signature = params.get("msg_signature", "")
    timestamp = params.get("timestamp", "")
    nonce = params.get("nonce", "")

    body = await request.body()
    root = ET.fromstring(body.decode())
    encrypt_text = root.find("Encrypt").text

    token = settings.WECOM_TOKEN
    encoding_aes_key = settings.WECOM_ENCODING_AES_KEY

    tmp_list = sorted([token, timestamp, nonce, encrypt_text])
    tmp_str = "".join(tmp_list)
    sign = hashlib.sha1(tmp_str.encode()).hexdigest()

    if sign != msg_signature:
        print("企微消息签名验证失败")
        return "signature failed"

    aes_key = base64.b64decode(encoding_aes_key + "=")
    cipher = AES.new(aes_key, AES.MODE_CBC, aes_key[:16])
    plain_text = cipher.decrypt(base64.b64decode(encrypt_text))

    pad = plain_text[-1]
    content = plain_text[16:-pad]
    msg_len = struct.unpack(">I", content[:4])[0]
    msg = content[4:4+msg_len].decode()

    msg_root = ET.fromstring(msg)
    user_id = msg_root.find("FromUserName").text or "unknown"
    user_name = user_id
    msg_type = msg_root.find("MsgType").text or ""

    if msg_type != "text":
        return "success"

    msg_content = msg_root.find("Content").text or ""
    msg_content = msg_content.strip()

    if not msg_content:
        return "success"

    print(f"企微用户 {user_id} 发来: {msg_content}")

    reply = process_message(msg_content, user_id, user_name, db)
    print("回复消息:", reply)

    # 加密回复并返回
    if reply:
        return encrypt_wecom_reply(reply, user_id, nonce, timestamp)
    return "success"


# ==================== 健康检查 ====================

@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "ok",
        "message": "记账助手运行中",
        "tips": "发送 /help 查看使用说明"
    }


# ==================== 飞书 ====================

@router.post("/webhook/feishu")
async def feishu_webhook(body: dict = Body(...), db: Session = Depends(get_db)):
    """
    飞书机器人 Webhook
    """
    print("飞书收到消息:", json.dumps(body, ensure_ascii=False, indent=2))

    if body.get("type") == "url_verification":
        challenge = body.get("challenge", "")
        print("URL验证，返回 challenge:", challenge)
        return {"challenge": challenge}

    event = body.get("event", {})
    message = event.get("message", {})

    if message.get("message_type") != "text":
        return {}

    content_str = message.get("content", "{}")
    content_json = json.loads(content_str)
    msg_content = content_json.get("text", "").strip()

    if not msg_content:
        return {}

    sender = event.get("sender", {})
    sender_id = sender.get("sender_id", {})
    user_id = sender_id.get("user_id") or sender_id.get("open_id", "unknown")

    print(f"飞书用户 {user_id} 发来: {msg_content}")

    reply = process_message(msg_content, user_id, user_id, db)

    message_id = message.get("message_id", "")
    if message_id and reply:
        import asyncio
        asyncio.create_task(reply_to_feishu(message_id, reply))

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
            token_resp = await client.post(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                json={"app_id": app_id, "app_secret": app_secret}
            )
            token_data = token_resp.json()
            token = token_data.get("tenant_access_token", "")

            if not token:
                print("❌ 获取 token 失败:", token_data)
                return

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


# ==================== 通用消息处理 ====================

def process_message(msg_content: str, user_id: str, user_name: str, db: Session) -> str:
    """统一的消息处理逻辑，企微和飞书共用"""

    intent = MessageParser.parse_intent(msg_content)
    print("识别意图:", intent)

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
        month = intent.get("month")
        report = stats.get_monthly_report(user_id, month=month)
        if report['total'] == 0:
            reply = MessageFormatter.format_no_data("本月")
        else:
            reply = MessageFormatter.format_monthly_report(report)

    elif intent["intent"] == "query_category":
        cat = intent.get("category", "其他")
        report = stats.get_category_report(user_id, cat)
        reply = MessageFormatter.format_category_report(report)

    elif intent["intent"] == "batch_record":
        lines = intent["lines"]
        results = []
        for line in lines:
            parsed = MessageParser.parse_transaction(line)
            if "error" not in parsed:
                try:
                    crud.create(
                        user_id=user_id,
                        amount=parsed["amount"],
                        category=parsed["category"],
                        note=parsed["note"],
                        user_name=user_name,
                        transaction_date=parsed.get("transaction_date", date.today())
                    )
                    results.append(parsed)
                except:
                    pass

        if results:
            lines_out = [f"✅ 已记录 {len(results)} 笔：", ""]
            for i, r in enumerate(results, 1):
                emoji = MessageFormatter.CATEGORY_EMOJI.get(r['category'], '📌')
                lines_out.append(f"  {i}. {emoji} {r['category']} ¥{abs(r['amount']):.2f} {r['note']}")
            reply = "\n".join(lines_out)
        else:
            reply = "❌ 没有成功记录任何一笔"

    elif intent["intent"] == "record":
        parsed = MessageParser.parse_transaction(msg_content)

        if "error" in parsed:
            reply = f"❌ {parsed['error']}\n\n发送 /help 查看使用说明"
        else:
            try:
                transaction = crud.create(
                    user_id=user_id,
                    amount=parsed["amount"],
                    category=parsed["category"],
                    note=parsed["note"],
                    user_name=user_name,
                    transaction_date=parsed.get("transaction_date", date.today())
                )
                reply = MessageFormatter.format_transaction(
                    parsed["amount"],
                    parsed["category"],
                    parsed["note"]
                )
                print("记账成功:", transaction)
            except Exception as e:
                print("记账失败:", e)
                reply = f"❌ 记账失败，请重试\n\n发送 /help 查看使用说明"

    else:
        reply = MessageFormatter.format_unknown()

    return reply
    
# ==================== 企微消息加密回复 ====================

def encrypt_wecom_reply(text: str, user_id: str, nonce: str, timestamp: str) -> str:
    """加密企微回复消息"""
    import hashlib
    import base64
    import struct
    import random
    import string
    from Crypto.Cipher import AES
    import xml.etree.ElementTree as ET
    from app.config import settings

    token = settings.WECOM_TOKEN
    encoding_aes_key = settings.WECOM_ENCODING_AES_KEY
    corp_id = settings.WECOM_CORP_ID

    # 构造回复 XML
    reply_xml = f"<xml><ToUserName><![CDATA[{user_id}]]></ToUserName><FromUserName><![CDATA[{corp_id}]]></FromUserName><CreateTime>{int(__import__('time').time())}</CreateTime><MsgType><![CDATA[text]]></MsgType><Content><![CDATA[{text}]]></Content></xml>"

    # 加密
    aes_key = base64.b64decode(encoding_aes_key + "=")
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    msg_len = struct.pack(">I", len(reply_xml.encode()))
    raw = random_str.encode() + msg_len + reply_xml.encode() + corp_id.encode()

    # PKCS7 补位
    pad = 32 - len(raw) % 32
    raw += bytes([pad] * pad)

    cipher = AES.new(aes_key, AES.MODE_CBC, aes_key[:16])
    encrypted = base64.b64encode(cipher.encrypt(raw)).decode()

    # 签名
    tmp_list = sorted([token, timestamp, nonce, encrypted])
    tmp_str = "".join(tmp_list)
    signature = hashlib.sha1(tmp_str.encode()).hexdigest()

    # 返回加密 XML
    return f"""<xml>
<Encrypt><![CDATA[{encrypted}]]></Encrypt>
<MsgSignature><![CDATA[{signature}]]></MsgSignature>
<TimeStamp>{timestamp}</TimeStamp>
<Nonce><![CDATA[{nonce}]]></Nonce>
</xml>"""