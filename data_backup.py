# -*- coding: utf-8 -*-
"""
data_backup.py —— OfferAgent 数据备份 / 恢复
============================================================================
岗位库、画像、记忆、投递日志都在 offeragent/data/（且被 gitignore，不会进仓库），
本脚本把它们打包成 zip，或从 zip 恢复 —— 换电脑 / 上线前 / 误删时用。

用法：
  python data_backup.py backup                  → 生成 offeragent/backups/offeragent_data_<时间戳>.zip
  python data_backup.py restore <zip路径>        → 从备份恢复 data/ 全部内容
"""
import os
import shutil
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "offeragent", "data")
BACKUP_DIR = os.path.join(HERE, "offeragent", "backups")


def backup() -> str:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    out = os.path.join(BACKUP_DIR, f"offeragent_data_{ts}.zip")
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _dirs, files in os.walk(DATA):
            for fn in files:
                full = os.path.join(root, fn)
                z.write(full, os.path.relpath(full, HERE))
                n += 1
    print(f"✅ 已备份 {n} 个文件：{out}（{os.path.getsize(out) / 1024:.0f} KB）")
    return out


def restore(zip_path: str) -> None:
    if not os.path.isfile(zip_path):
        print(f"❌ 备份文件不存在：{zip_path}")
        return
    restored = 0
    with zipfile.ZipFile(zip_path) as z:
        for n in z.namelist():
            if not n.startswith("offeragent/data/"):
                continue          # 只恢复本项目 data/，不碰其他路径
            target = os.path.join(HERE, n)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(n) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            restored += 1
    print(f"✅ 已恢复 {restored} 个文件，来源：{zip_path}")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "backup":
        backup()
    elif len(sys.argv) >= 3 and sys.argv[1] == "restore":
        restore(sys.argv[2])
    else:
        print("用法：python data_backup.py backup  |  python data_backup.py restore <zip路径>")
