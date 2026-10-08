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
    for root, _dirs, fnames in os.walk(p):
        for fn in fnames:
            files += 1
            try:
                total += os.path.getsize(os.path.join(root, fn))
            except Exception:
                pass
    return {"dir": p, "files": files, "bytes": total,
            "mb": round(total / 1048576, 2),
            "exists": os.path.isdir(p)}


def export_bytes(d=None, allow_any=False):
    """把数据目录打包成 zip 的字节流（可直接给 st.download_button）。"""
    p = _check_target(d or data_dir(), allow_any=allow_any)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _dirs, fnames in os.walk(p):
            for fn in fnames:
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, p)
                try:
                    z.write(full, rel)
                except Exception:
                    continue
    return buf.getvalue()


def export_filename(prefix="offeragent-data", now=None):
    ts = (now or time.localtime())
    return "%s-%s.zip" % (prefix, time.strftime("%Y%m%d-%H%M%S", ts))


def purge(d=None, allow_any=False, keep=("config.json",)):
    """清空数据目录里的个人数据（保留目录本身）。返回 (删除文件数, 删除目录数)。

    keep：不删的顶层文件名。默认保留 config.json ——那是本机配置（API Key、主题、每日目标），
    不是用户的求职数据，删掉只会让人重新配一遍，属于"清数据顺手把人家设置也清了"的坏设计。
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
