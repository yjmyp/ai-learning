# -*- coding: utf-8 -*-
"""隐私与数据工具：导出 / 清空用户自己的数据（上线给陌生人用之前的合规硬要求）。

三条原则：
  1. 数据只落在本机 `offeragent/data/`，不上传到我们的服务器；只有调用模型时，
     相关文本会发给 DeepSeek API。
  2. 用户随时能导出全部数据（zip）。
  3. 用户随时能清空。清空是不可逆操作，所以只允许作用在"看起来确实是我们的数据目录"上，
     防止某个调用方把路径指到别处，把用户别的文件删了。
"""
import io
import os
import shutil
import time
import zipfile

# 浏览器登录态 / 缓存目录：体积能到 1GB+（实测 edge_profile 1064MB / 5971 文件），
# 既不是"求职数据"，也不该被打包（会撑爆内存）或清空（会把用户从 BOSS 登出）。
SKIP_DIRS = ("edge_profile",)
MAX_FILE_MB = 50          # 单个文件超过这个大小不进 zip（备份说明里会列清楚）


def data_dir():
    """数据目录的唯一权威源：优先用 store.DATA_DIR，取不到再退回默认相对路径。"""
    try:
        from store import DATA_DIR
        return str(DATA_DIR)
    except Exception:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def _check_target(d, allow_any=False):
    p = os.path.abspath(d)
    if not os.path.isdir(p):
        raise ValueError("目标目录不存在：%s" % p)
    if allow_any:
        return p
    norm = p.replace("\\", "/").rstrip("/").lower()
    if not norm.endswith("offeragent/data"):
        raise ValueError("拒绝操作：目标路径不像 OfferAgent 数据目录（%s）" % p)
    return p


def data_summary(d=None, allow_any=False):
    """看一眼数据目录里有什么、多大：给"删之前先让人确认"用。"""
    p = _check_target(d or data_dir(), allow_any=allow_any)
    files, total = 0, 0
    for full in _iter_files(p):
        files += 1
        try:
            total += os.path.getsize(full)
        except Exception:
            pass
    skipped = [d for d in SKIP_DIRS if os.path.isdir(os.path.join(p, d))]
    return {"dir": p, "files": files, "bytes": total,
            "mb": round(total / 1048576, 2),
            "exists": os.path.isdir(p), "skipped_dirs": skipped}


def _iter_files(p):
    """遍历要算作"我的数据"的文件：跳过浏览器登录态等目录。"""
    for root, dirs, fnames in os.walk(p):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in fnames:
            yield os.path.join(root, fn)


def export_bytes(d=None, allow_any=False):
    """把数据目录打包成 zip 的字节流（可直接给 st.download_button）。

    跳过大文件与浏览器登录态目录，并在包里放一份"备份说明.txt"说明跳过了什么
    ——备份少东西还不告诉用户，是比不备份更糟的事。
    """
    p = _check_target(d or data_dir(), allow_any=allow_any)
    buf = io.BytesIO()
    skipped, n_files = [], 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for full in _iter_files(p):
            rel = os.path.relpath(full, p)
            try:
                if os.path.getsize(full) > MAX_FILE_MB * 1048576:
                    skipped.append("%s（>%dMB）" % (rel, MAX_FILE_MB))
                    continue
                z.write(full, rel)
                n_files += 1
            except Exception:
                skipped.append("%s（读取失败）" % rel)
        lines = ["OfferAgent 数据备份说明",
                 "生成时间：%s" % time.strftime("%Y-%m-%d %H:%M:%S"),
                 "已打包文件：%d 个" % n_files,
                 "未打包目录：%s" % ("、".join(SKIP_DIRS) + "（浏览器登录态/缓存，不属于求职数据）"),
                 "未打包文件："]
        lines += (["  - " + s for s in skipped] or ["  （无）"])
        z.writestr("备份说明.txt", "\n".join(lines) + "\n")
    return buf.getvalue()


def export_filename(prefix="offeragent-data", now=None):
    ts = (now or time.localtime())
    return "%s-%s.zip" % (prefix, time.strftime("%Y%m%d-%H%M%S", ts))


def purge(d=None, allow_any=False, keep=("config.json",) + SKIP_DIRS):
    """清空数据目录里的个人数据（保留目录本身）。返回 (删除文件数, 删除目录数)。

    keep：不删的顶层文件/目录名。默认保留 config.json（本机配置：API Key、主题、每日目标）
    和 edge_profile（浏览器登录态）——删掉它们只会让人重新配一遍、重新登一次 BOSS，
    属于"清数据顺手把人家的设置和登录也清了"的坏设计。
    """
    p = _check_target(d or data_dir(), allow_any=allow_any)
    keep = {k.lower() for k in (keep or ())}
    n_files = n_dirs = 0
    for name in os.listdir(p):
        if name.lower() in keep:
            continue
        full = os.path.join(p, name)
        try:
            if os.path.isdir(full):
                n_files += sum(len(fs) for _r, _d, fs in os.walk(full))
                n_dirs += 1
                shutil.rmtree(full)
            else:
                os.remove(full)
                n_files += 1
        except Exception:
            continue
    return n_files, n_dirs
