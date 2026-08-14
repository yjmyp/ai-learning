# -*- coding: utf-8 -*-
"""轻量重排：TF-IDF 字符 n-gram 相关性（离线可用，不依赖大模型下载）"""
from sklearn.feature_extraction.text import TfidfVectorizer


class Reranker:
    def __init__(self, ngram=(2, 3)):
        self.vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=ngram,
            max_features=20000,
            sublinear_tf=True,
        )

    def rerank(self, question, chunks):
        """对候选块按与问题的字符级相似度重排，返回带 rerank_score 的新列表"""
        if len(chunks) <= 1:
            return chunks
        texts = [c["text"] for c in chunks]
        matrix = self.vectorizer.fit_transform(texts + [question])
        question_vec = matrix[-1]
        doc_vecs = matrix[:-1]
        sims = (doc_vecs @ question_vec.T).toarray().ravel()
        order = sorted(range(len(chunks)), key=lambda i: (-sims[i], i))
        ranked = []
        for i in order:
            item = dict(chunks[i])
            item["rerank_score"] = round(float(sims[i]), 4)
            ranked.append(item)
        return ranked
