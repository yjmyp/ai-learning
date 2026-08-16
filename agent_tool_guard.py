# agent_tool_guard.py —— 工具调用守卫：参数校验 + 错误捕获
#
# 要解决的真实问题：模型输出的工具调用可能
#   ① 工具名写错   ② 参数缺失   ③ 参数类型错误   ④ 参数根本不是对象
# 没有守卫时，任何一个都会让 Agent 直接崩掉（KeyError / TypeError）。
# 有守卫后，坏调用变成一条"结构化错误"回填给模型，让它修正重试。
import json


# ===== 1) 每个工具的"参数合同"（JSON Schema 子集） =====
TOOL_SCHEMAS = {
    "add":      {"required": ["a", "b"], "types": {"a": (int, float), "b": (int, float)}},
    "subtract": {"required": ["a", "b"], "types": {"a": (int, float), "b": (int, float)}},
    "multiply": {"required": ["a", "b"], "types": {"a": (int, float), "b": (int, float)}},
}


def safe_call(tools, schemas, name, args):
    """校验并执行一次工具调用；任何问题都返回 {'ok': False}，绝不抛出异常。"""
    try:
        schema = schemas.get(name)
        if schema is None:
            raise ValueError(f"未知工具: {name}")
        if not isinstance(args, dict):
            raise ValueError("args 必须是 JSON 对象")
        for key in schema["required"]:
            if key not in args:
                raise ValueError(f"缺少必填参数: {key}")
        for key, types in schema["types"].items():
            if key in args and not isinstance(args[key], types):
                raise ValueError(f"参数 {key} 类型错误（{type(args[key]).__name__}）")
        result = tools[name](**args)
        return {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    demo_tools = {
        "add": lambda a, b: a + b,
        "subtract": lambda a, b: a - b,
        "multiply": lambda a, b: a * b,
    }
    cases = [
        ("add", {"a": 1, "b": 2}),        # 正常
        ("add", {"a": 1}),                # 缺参数
        ("add", {"a": 1, "b": "x"}),      # 类型错
        ("div", {"a": 1, "b": 2}),        # 未知工具
        ("multiply", {"a": 3, "b": 4}),   # 正常
    ]
    for name, args in cases:
        print(f"{name}{args} -> {safe_call(demo_tools, TOOL_SCHEMAS, name, args)}")
