# chat_learn.py —— chat.py 的逐行讲解版（Key 用占位符，运行请用 chat.py）
# ============================================================

# 导入 requests 库：一个帮你"发网络请求"的工具（去网上给 DeepSeek 送信）
import requests

# 你的 DeepSeek API 密钥：相当于"账号+密码"，证明你是付费用户，千万别泄露
API_KEY = "sk-你的Key粘贴到这里"

# DeepSeek 服务的"门牌号"：请求要发往的网址
url = "https://api.deepseek.com/chat/completions"

# 请求头：告诉服务器"我是谁"（Bearer 后面带 Key 证明身份）
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# messages 列表 = AI 的"记忆"，存着你们所有的对话记录
messages = []

print("DeepSeek 聊天小助手（输入 exit 或 退出 结束）")
print("-" * 40)

# while True = 无限循环：程序会一直等你输入，直到遇到 break 才停
while True:
    # input() = 在终端等你打字，回车后把你输入的内容存进 user_input
    user_input = input("你：")

    # 如果输入的是 exit/退出/quit，就打印再见并 break（跳出循环，结束程序）
    if user_input.strip().lower() in ("exit", "退出", "quit"):
        print("再见！")
        break

    # 把你说的这句话，按 DeepSeek 要求的格式，追加进"记忆"列表
    messages.append({"role": "user", "content": user_input})

    # 组装要发给服务器的"请求体"：指定用哪个模型 + 带上全部对话历史
    data = {
        "model": "deepseek-chat",
        "messages": messages,
    }

    try:
        # 真正发请求！把 data 发给 url，最多等 60 秒，服务器回复存进 r
        r = requests.post(url, headers=headers, json=data, timeout=60)
        # 如果服务器返回错误码（比如 Key 错了），这里会抛异常跳到 except
        r.raise_for_status()
        # 从服务器返回的"大套娃"里，一层一层取出 AI 的回答文字
        reply = r.json()["choices"][0]["message"]["content"]
        # 把 AI 的回答也追加进记忆：下次它还记得自己说过什么
        messages.append({"role": "assistant", "content": reply})
        # 打印 AI 的回答（f 字符串 = 把变量塞进字符串里）
        print(f"AI：{reply}")
    except Exception as e:
        # 任何一步出错都会走到这里，打印错误原因，程序不会崩
        print(f"出错啦：{e}")
