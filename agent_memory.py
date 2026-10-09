# agent_memory.py —— Agent 记忆模块（v2 · SQLite 持久化）
# 对应客观差距清单：Agent 无记忆、无多轮 → 短期（对话历史）+ 长期（事实表）
#
# 设计（面试可讲）：
#   短期记忆 = 最近 N 轮对话，注入 system prompt（窗口滑动，超长可压缩）
#   长期记忆 = 规则抽取"关键事实"（我是谁/想投什么/做过什么），**跨会话保留**
#   持久化   = 传入 db_path 时写入 SQLite（facts / turns 两张表），下次会话自动加载
#             —— 这就是"从进程内记忆 → 跨会话记忆"的升级点
import os
import re
import sqlite3


class Memory:
    def __init__(self, max_turns=6, db_path=None):
        self.turns = []            # [(user_text, assistant_text), ...] 短期
        self.facts = []            # [str, ...] 长期事实
        self.max_turns = max_turns
        self.db_path = db_path
        if db_path:
            self._load_db()

    # ---------- SQLite 持久化 ----------
    def _connect(self):
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS facts (id INTEGER PRIMARY KEY AUTOINCREMENT, fact TEXT UNIQUE)")
        conn.execute("CREATE TABLE IF NOT EXISTS turns (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, assistant TEXT, created TEXT DEFAULT (datetime('now','localtime')))")
        return conn

    def _load_db(self):
        conn = self._connect()
        try:
            self.facts = [r[0] for r in conn.execute("SELECT fact FROM facts ORDER BY id").fetchall()]
            rows = conn.execute("SELECT user, assistant FROM turns ORDER BY id DESC LIMIT ?", (self.max_turns,)).fetchall()
            self.turns = list(reversed([(u, a) for u, a in rows]))
        finally:
            conn.close()

    # ---- 记录一轮对话（内存 + DB） ----
    def add_turn(self, user, assistant):
        self.turns.append((user, assistant))
        # 窗口滑动：只保留最近 N 轮，防止上下文无限膨胀
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]
        if self.db_path:
            conn = self._connect()
            try:
                conn.execute("INSERT INTO turns (user, assistant) VALUES (?, ?)", (user, assistant))
                conn.commit()
            finally:
                conn.close()

    # ---- 短期记忆：最近几轮文本 ----
    def recent(self, limit=None):
        limit = limit or self.max_turns
        lines = []
        for u, a in self.turns[-limit:]:
            lines.append(f"用户说：{u}\n助手答：{a[:100]}")
        return "\n".join(lines)

    # ---- 长期记忆：规则抽取事实 ----
    FACT_PATTERNS = [
        (r"(?:我叫|我是|我的名字叫)\s*([\u4e00-\u9fa5A-Za-z0-9]{2,6})", "用户名叫：{0}"),
        (r"(?:我来自|我是)\s*([\u4e00-\u9fa5]{2,12}?)\s*(?:大学|学院)", "学校：{0}"),
        (r"([\u4e00-\u9fa5]{2,12}?)\s*届", "{0}届学生"),
        (r"(?:我想投|我要投|目标岗位|求职方向)[:：是]?\s*([^，。\n]{2,30})", "求职方向：{0}"),
        (r"(?:我做过|我做了|我开发了|我实现了)\s*([^，。\n]{2,30})", "做过项目：{0}"),
    ]

    def extract_facts(self, text):
        """从用户输入里抽取事实并去重存入长期记忆（内存 + DB）。"""
        for pat, fmt in self.FACT_PATTERNS:
            for m in re.findall(pat, text):
                fact = fmt.format(m)
                if fact not in self.facts:
                    self.facts.append(fact)
                    if self.db_path:
                        conn = self._connect()
                        try:
                            conn.execute("INSERT OR IGNORE INTO facts (fact) VALUES (?)", (fact,))
                            conn.commit()
                        finally:
                            conn.close()
        return self.facts

    def forget(self, fact: str) -> bool:
        """删除一条记忆事实（长期记忆可纠错）。返回是否删除成功。"""
        removed = False
        if fact in self.facts:
            self.facts.remove(fact)
            removed = True
        if self.db_path:
            conn = self._connect()
            try:
                cur = conn.execute("DELETE FROM facts WHERE fact = ?", (fact,))
                conn.commit()
                removed = removed or cur.rowcount > 0
            finally:
                conn.close()
        return removed

    # ---- 注入 system prompt 的上下文 ----
    def to_context(self):
        parts = []
        if self.facts:
            parts.append("【我记住的关于你的事实】" + "；".join(self.facts))
        if self.turns:
            parts.append("【最近对话】" + self.recent())
        return "\n".join(parts)

    def __repr__(self):
        return f"<Memory turns={len(self.turns)} facts={len(self.facts)} db={self.db_path}>"


if __name__ == "__main__":
    import tempfile
    db = os.path.join(tempfile.gettempdir(), "mem_test.db")
    if os.path.exists(db):
        os.remove(db)
    print("=== 第一次会话（写入）===")
    m1 = Memory(db_path=db)
    m1.extract_facts("我是余剑，南京邮电大学2027届，我想投AI应用开发实习岗，我做过RAG知识库问答系统")
    m1.add_turn("我的简历怎么改？", "加量化数字。")
    for f in m1.facts:
        print(" -", f)
    print("\n=== 第二次会话（跨会话加载）===")
    m2 = Memory(db_path=db)
    for f in m2.facts:
        print(" -", f)
    print("最近对话:", m2.recent())
    assert m2.facts and m2.turns, "跨会话记忆失败"
    print("\n✅ 跨会话记忆 OK")
