"""
测试脚本 - 模拟企业微信发送消息
"""
import requests
import json

# 服务器地址
#URL = "http://localhost:8000/api/v1/webhook/wecom"
URL = "https://grip-latino-transit-enjoy.trycloudflare.com/api/v1/webhook/wecom"

def send_message(content, userid="xiaoming", name="小明"):
    """发送一条消息给机器人"""
    data = {
        "text": {
            "content": content
        },
        "from": {
            "userid": userid,
            "name": name
        }
    }
    
    print("=" * 50)
    print(f"发送消息: {content}")
    print("-" * 50)
    
    response = requests.post(URL, json=data)
    result = response.json()
    
    print("机器人回复:")
    print(result["text"]["content"])
    print("=" * 50)
    print()

# ====== 开始测试 ======

print("\n🧪 开始测试记账机器人\n")

# 测试1：记账
send_message("午餐 68 肯德基")
send_message("打车 25 去公司")
send_message("买衣服 299")
send_message("工资 15000 到账")
send_message("咖啡 35")

# 测试2：周统计
send_message("/周统计")

# 测试3：月统计
send_message("/月统计")

# 测试4：分类统计
send_message("餐饮统计")

# 测试5：帮助
send_message("/help")

# 测试6：删除
send_message("/删除")

# 测试7：再查一次周统计
send_message("/周统计")

print("\n✅ 所有测试完成！")