# -*- coding: utf-8 -*-
"""把 OfferAgent 的 8 个工具暴露成 MCP server（stdio + JSON-RPC 2.0）

为什么值得做：MCP 正在成为"工具统一接入协议"——工具不再写死在应用里，而是
任何支持 MCP 的客户端（Claude Desktop / Cursor / Codex 等）都能挂上你的工具。
这个 server 不依赖 `mcp` 官方包（本机没装），手写协议子集，能讲清"协议长什么样"：

    initialize   → 返回协议版本与 capabilities.tools
    tools/list   → 列出工具名 / 描述 / inputSchema（JSON Schema）
    tools/call   → 执行工具，返回 content[].text

启动（stdio，供 MCP 客户端拉起）：
    python offer_agent_mcp.py

自测：
    python offer_agent_mcp.py --selftest     # 不启动服务，直接跑一遍 tools/list + call
"""
import json
import sys

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))

# MCP 走 JSON-RPC，协议规定 UTF-8。Windows 控制台默认 GBK，
# 不强制成 UTF-8 的话，客户端按 utf-8 解码会 UnicodeDecodeError（就是踩过的坑）。
for _stream in (sys.stdin, sys.stdout):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from offer_agent_tools import build_registry

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "offeragent-tools", "version": "1.0.0"}

# 我们工具的参数是 {name: 中文说明}，转成 MCP 需要的 JSON Schema
_TYPE_HINT = {"jd_text": "string", "profile": "string", "text": "string",
              "url": "string", "states_json": "string", "fact": "string",
              "variant": "string"}


def _schema(params):
    props, required = {}, []
    for k, desc in (params or {}).items():
        props[k] = {"type": _TYPE_HINT.get(k, "string"),
                    "description": str(desc)}
        if "可选" not in str(desc):
            required.append(k)
    return {"type": "object", "properties": props, "required": required}


def tool_list():
    reg = build_registry()
    return [{"name": name,
             "description": getattr(t, "description", ""),
             "inputSchema": _schema(getattr(t, "params", {})),
             "annotations": {"humanConfirm": bool(getattr(t, "human_confirm", False))}}
            for name, t in reg.items()]


def call_tool(name, arguments):
    reg = build_registry()
    tool = reg.get(name)
    if tool is None:
        return {"content": [{"type": "text", "text": "未知工具：%s" % name}],
                "isError": True}
    try:
        result = tool.func(**(arguments or {}))
    except Exception as e:
        return {"content": [{"type": "text", "text": "工具执行失败：%s" % str(e)[:200]}],
                "isError": True}
    text = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
    out = {"content": [{"type": "text", "text": text}]}
    if getattr(tool, "human_confirm", False):
        out["_meta"] = {"humanConfirm": True,
                        "note": "执行类工具：MCP 客户端需先让人确认再调用"}
    return out


def handle(req):
    """处理一条 JSON-RPC 请求，返回响应 dict（通知类请求返回 None）。"""
    method = req.get("method")
    rid = req.get("id")
    if method == "initialize":
        result = {"protocolVersion": PROTOCOL_VERSION,
                  "capabilities": {"tools": {"listChanged": False}},
                  "serverInfo": SERVER_INFO}
    elif method in ("tools/list", "tools.list"):
        result = {"tools": tool_list()}
    elif method in ("tools/call", "tools.call"):
        p = req.get("params") or {}
        result = call_tool(p.get("name"), p.get("arguments") or {})
    elif method in ("notifications/initialized", "initialized"):
        return None
    else:
        return {"jsonrpc": "2.0", "id": rid,
                "error": {"code": -32601, "message": "未知方法：%s" % method}}
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def serve():
    """stdio 主循环：一行一条 JSON-RPC。"""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue
        resp = handle(req)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


def selftest():
    tools = tool_list()
    print("工具数 =", len(tools))
    for t in tools:
        print("   %-18s 需人确认=%s" % (t["name"], t["annotations"]["humanConfirm"]))
    init = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    print("initialize →", init["result"]["serverInfo"],
          init["result"]["capabilities"])
    listed = handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    print("tools/list → 返回", len(listed["result"]["tools"]), "个工具")
    called = handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                     "params": {"name": "assess_job",
                                "arguments": {"jd_text": "岗位：AI应用开发实习\n"
                                                         "负责 RAG 与 Agent 应用开发，"
                                                         "要求熟悉 Python、"
                                                         "可用 FastAPI 写接口，"
                                                         "实习 3 个月以上，每周 4 天。"}}})
    txt = called["result"]["content"][0]["text"]
    print("tools/call(assess_job) →", txt[:120])
    print("selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        serve()
