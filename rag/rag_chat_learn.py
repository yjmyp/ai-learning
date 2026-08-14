# rag_chat_learn.py —— rag_chat.py 的逐行讲解版（Key 用占位符，运行请用 rag_chat.py）
# 整条流水线：读资料 -> 切块 -> 检索 -> 拼提示词 -> 问AI
# ============================================================

# os：负责文件路径操作（拼接路径等）
import os
# glob：用通配符搜索文件，比如 *.txt = 找到所有 txt 文件
import glob
# requests：发网络请求，给 DeepSeek 送信
import requests
# 从 sklearn 导入 TF-IDF 工具：把文字变成"数字"，方便算相似度
from sklearn.feature_extraction.text import TfidfVectorizer
# 从 sklearn 导入余弦相似度：算两段文字有多像（0=不像，1=一模一样）
from sklearn.metrics.pairwise import cosine_similarity

API_KEY = "sk-你的Key粘贴到这里"
url = "https://api.deepseek.com/chat/completions"
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


# ========== 第 1 块：读资料（把 txt 文件变成一段段文字） ==========
def load_notes(folder="notes"):
    """读取 notes 文件夹里所有 .txt，按段落切成小块"""
    chunks = []  # 准备一个空列表，用来装所有段落
    for path in glob.glob(os.path.join(folder, "*.txt")):  # 找到 notes 里所有 txt 文件
        with open(path, encoding="utf-8-sig") as f:  # 打开文件（utf-8-sig 兼容 Windows 编码）
            text = f.read()  # 把整个文件内容读成一个字符串
        for para in text.split("\n\n"):  # 按"空行"把文本切成一段一段
            para = para.strip()  # 去掉每段前后的空格
            if len(para) >= 20:  # 太短的段落丢掉（比如空行碎片）
                chunks.append(para)  # 合格的段落装进列表
    return chunks  # 返回所有段落 —— 这就是你的"知识库"


# ========== 第 2 块：检索（从知识库里挑出和问题最相关的3段） ==========
def search(chunks, query, top_k=3):
    """用字符 n-gram（2~3 字一组）找出和问题最相关的 3 段资料"""
    # 创建"文字转数字"工具，按 2~3 个字一组切（中文没有空格，所以按字切）
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 3))
    # 把"资料 + 问题"一起转成数字矩阵（最后一行 = 问题）
    tfidf = vectorizer.fit_transform(chunks + [query])
    # 算"问题"和"每段资料"的相似度，得到一个分数列表
    sims = cosine_similarity(tfidf[-1], tfidf[:-1])[0]
    # 找出分数最高的前 3 段的下标（从小到大排序，取后 3 个，再倒过来变从大到小）
    top = sims.argsort()[-top_k:][::-1]
    # 返回 [(段落内容, 相似度), ...] 的列表
    return [(chunks[i], float(sims[i])) for i in top]


# ========== 第 3 块：生成（把检索结果拼进提示词，让AI回答） ==========
def ask(chunks, question):
    results = search(chunks, question)  # 先检索，拿到最相关的 3 段
    # 把 3 段资料拼成一段带编号的文字（join = 用"\n\n"把列表连成一个字符串）
    context = "\n\n".join(f"[资料{i+1}] {c}" for i, (c, s) in enumerate(results))
    # 拼出完整提示词：指示 + 资料 + 问题
    prompt = (
        "请只根据下面提供的资料回答问题。"
        "如果资料里没有答案，就回答'资料里没找到相关答案'。\n\n"
        f"资料：\n{context}\n\n"
        f"问题：{question}"
    )
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],  # 把拼好的提示词发给 AI
    }
    r = requests.post(url, headers=headers, json=data, timeout=60)  # 发请求
    r.raise_for_status()  # 出错就抛异常
    return r.json()["choices"][0]["message"]["content"]  # 取出回答并返回


# ========== 第 4 块：入口（程序从这里开始跑） ==========
def main():
    chunks = load_notes()  # 启动时先把资料全部加载好
    print(f"已加载 {len(chunks)} 段资料，开始问答（输入 exit 或 退出 结束）")
    print("-" * 40)
    while True:
        q = input("你：").strip()  # 等输入，去掉首尾空格
        if not q:
            continue  # 输入是空的就重新问
        if q.lower() in ("exit", "退出"):
            print("再见！")
            break
        print(f"AI：{ask(chunks, q)}")  # 检索+生成一步完成，打印回答
        print("-" * 40)


# 只有"直接运行本文件"时才执行 main()（被别的文件 import 时不会执行）
if __name__ == "__main__":
    main()
