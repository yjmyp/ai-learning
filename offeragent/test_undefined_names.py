# -*- coding: utf-8 -*-
"""静态扫一遍：找出「用了但从没定义」的变量名（云端 NameError 的根因）。

为什么需要：线上就是靠这类错误白屏的——page_applications 引用了被删掉的
applied_jobs，浏览器验收脚本没点到那个分支所以没发现。这个脚本不跑页面，秒出结果。

跑法：python offeragent/test_undefined_names.py
"""
import ast
import builtins
import sys
from pathlib import Path

HERE = Path(__file__).parent
TARGETS = sorted(HERE.glob("*.py"))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ALLOW = set(dir(builtins)) | {"st", "self", "cls", "__name__", "__file__"}


SCOPE = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)


def _body_of(scope) -> list:
    if isinstance(scope, ast.Lambda):
        return [scope.body]
    return list(getattr(scope, "body", []) or [])


def _args_of(scope) -> set:
    a = getattr(scope, "args", None)
    if not a:
        return set()
    out = {x.arg for x in (a.posonlyargs + a.args + a.kwonlyargs)}
    if a.vararg:
        out.add(a.vararg.arg)
    if a.kwarg:
        out.add(a.kwarg.arg)
    return out


def _child_scopes(body) -> list:
    """这个作用域里直接嵌套的内层作用域（不再往下钻）。"""
    out = []

    def rec(node):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, SCOPE):
                out.append(child)
                continue
            rec(child)

    for stmt in body:
        if isinstance(stmt, SCOPE):
            out.append(stmt)
            continue
        rec(stmt)
    return out


def _local_defs(body) -> set:
    """这个作用域里定义过的名字（含内层函数名，但不下沉进内层函数体）。"""
    names = set()

    def visit(node):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
            return
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, ast.alias):
            names.add((node.asname or node.name).split(".")[0])
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
        elif isinstance(node, ast.Lambda):
            names.update(_args_of(node))
        for child in ast.iter_child_nodes(node):
            visit(child)

    for stmt in body:
        visit(stmt)
    return names


def _own_loads(scope) -> list:
    """本作用域里读取的 Name（跳过内层作用域的函数体）。"""
    out = []

    def rec(node):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, SCOPE):
                continue
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                out.append(child)
            rec(child)

    for stmt in _body_of(scope):
        if isinstance(stmt, SCOPE):
            continue
        if isinstance(stmt, ast.Name) and isinstance(stmt.ctx, ast.Load):
            out.append(stmt)
        rec(stmt)
    return out


def _walk(scope, outer: set, problems: list):
    body = _body_of(scope)
    avail = outer | _local_defs(body) | _args_of(scope)
    name = getattr(scope, "name", "<lambda>")
    for node in _own_loads(scope):
        if node.id not in avail and node.id not in ALLOW:
            problems.append((name, node.id, node.lineno))
    for child in _child_scopes(body):
        _walk(child, avail, problems)


def _collect_assigns(body, names, depth=0):
    """收集容器内（try/if/with/for）的赋值名，不下钻函数体。"""
    if depth > 2:
        return
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
            continue
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
            continue
        if isinstance(node, (ast.If, ast.Try, ast.With, ast.For, ast.While)):
            _collect_assigns(node.body, names, depth + 1)
            if isinstance(node, ast.Try):
                for h in node.handlers:
                    _collect_assigns(h.body, names, depth + 1)


def _module_top_names(mod_name: str, here: Path, depth: int = 0) -> set:
    """不执行模块，用 ast 收集它顶层定义/导入的名字（处理 import * 误报）。"""
    if depth > 2:
        return set()
    mod_file = here / f"{mod_name}.py"
    if not mod_file.exists():
        return set()
    try:
        tree = ast.parse(mod_file.read_text(encoding="utf-8"))
    except Exception:
        return set()
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Import):
            for a in node.names:
                names.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            for a in node.names:
                if a.name == "*":
                    names |= _module_top_names(node.module, here, depth + 1)
                else:
                    names.add(a.asname or a.name)
    _collect_assigns(tree.body, names)
    return names


def _star_import_extra(tree, here: Path) -> set:
    """`from X import *` 的源模块顶层名字（静态收集，不执行模块）。"""
    extra = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.ImportFrom) and node.module
                and any(a.name == "*" for a in node.names)):
            extra |= _module_top_names(node.module, here)
    return extra


def check_source(src: str):
    tree = ast.parse(src)
    problems = []
    module_scope = _local_defs(tree.body) | _star_import_extra(tree, HERE)
    for stmt in tree.body:
        if isinstance(stmt, SCOPE):
            _walk(stmt, module_scope, problems)
        else:
            for child in _child_scopes([stmt]):
                _walk(child, module_scope, problems)
    return problems


SELF_TEST = """
def a():
    return never_defined_anywhere


def b():
    ok = 1
    return ok
"""


def main():
    self_hits = check_source(SELF_TEST)
    if not any(n == "never_defined_anywhere" for _, n, _ in self_hits):
        print("❌ 自检失败：这个检查器抓不到明显的未定义名，先别信它的结论")
        return 2
    total = 0
    for p in TARGETS:
        if p.name.startswith("test_") or p.name.startswith("_probe"):
            continue
        try:
            probs = check_source(p.read_text(encoding="utf-8"))
        except SyntaxError as e:
            print(f"❌ {p.name} 语法错误：{e}")
            total += 1
            continue
        for fn, name, line in probs:
            print(f"❌ {p.name}:{line} 函数 {fn}() 用了未定义的 `{name}`")
            total += 1
    print(f"\n发现 {total} 处可疑未定义名" if total
          else "✅ 没有发现未定义的变量名（自检也通过）")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
