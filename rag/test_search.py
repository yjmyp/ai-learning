# test_search.py —— 亲手把 search 填完整，跑起来看检索结果
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 4 段测试资料：3 段大模型知识 + 1 段"天气"干扰项
chunks = [
    "RAG是检索增强生成，让大模型先查资料再回答。",
    "Token是大模型处理文本的最小单位。",
    "Agent是能自己规划和调用工具的AI。",
    "今天的天气很好，适合出去玩。",
]

def search(chunks, query, top_k=4):
    """把下面 4 步补全（今天学的：翻译→比像→排序→打包）"""
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 3))
    
    # 第 1 步：翻译成数字表格（问题放最后）
    tfidf = vectorizer.fit_transform(chunks + [query])
    # 第 2 步：算"问题"和"每段资料"的相似度
    sims = cosine_similarity(tfidf[-1], tfidf[:-1])[0]
    # 第 3 步：排序，取分数最高的前 3 个下标，反转
    top = sims.argsort()[-top_k:][::-1]
    # 第 4 步：按下标组装 (段落, 分数)，返回
    return [(chunks[i], float(sims[i])) for i in top]

query = "什么是RAG？"
results = search(chunks, query)

print("问题：", query)
print("-" * 40)
print("最相关的4 段：")
for i, (text, score) in enumerate(results):
    print(f"  {i+1}. 相似度 {score:.2f} | {text}")
