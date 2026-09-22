# -*- coding: utf-8 -*-
"""BM25 检索器（从零实现，中文友好，无第三方依赖）

BM25 是关键词检索的经典算法：
- 词频（TF）越高越相关，但有上限（k1 控制饱和）；
- 稀有词权重更大（IDF，逆文档频率）；
- 文档长度越长，分数适当惩罚（b 控制长度归一化强度）。

和向量检索互补：向量管"语义相近"，BM25 管"词面精确命中"。
"""
import math
import re

_WORD_RE = re.compile(r"[a-z0-9_]+")
_CN_RE = re.compile(r"[\u4e00-\u9fff]+")


def tokenize(text):
    """英文/数字按单词，中文按相邻双字（bigram）切分。"""
    text = text.lower()
    tokens = []
    for m in _WORD_RE.finditer(text):
        tokens.append(m.group(0))
    for run in _CN_RE.findall(text):
        n = len(run)
        if n == 1:
            tokens.append(run)
        else:
            tokens.extend(run[i:i + 2] for i in range(n - 1))
    return tokens


class BM25:
    def __init__(self, corpus, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.doc_tokens = [tokenize(doc) for doc in corpus]
        self.doc_len = [len(t) for t in self.doc_tokens]
        self.n_docs = len(self.doc_len)
        self.avg_len = sum(self.doc_len) / max(self.n_docs, 1)

        # 文档频率 df → 逆文档频率 idf
        self.df = {}
        for tokens in self.doc_tokens:
            for term in set(tokens):
                self.df[term] = self.df.get(term, 0) + 1
        self.idf = {
            term: math.log(1 + (self.n_docs - df + 0.5) / (df + 0.5))
            for term, df in self.df.items()
        }

    def score(self, query, doc_idx):
        """单个文档对查询的 BM25 分数。"""
        tokens = self.doc_tokens[doc_idx]
        dl = self.doc_len[doc_idx]
        tf_map = {}
        for t in tokens:
            tf_map[t] = tf_map.get(t, 0) + 1

        total = 0.0
        for term in set(tokenize(query)):
            tf = tf_map.get(term, 0)
            if tf == 0 or term not in self.idf:
                continue
            # 长度归一化分母
            norm = self.k1 * (1 - self.b + self.b * dl / max(self.avg_len, 1e-9))
            total += self.idf[term] * tf * (self.k1 + 1) / (tf + norm)
        return total

    def search(self, query, top_k):
        """返回 [(文档下标, 分数)]，按分数降序。"""
        scored = [(i, self.score(query, i)) for i in range(self.n_docs)]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
