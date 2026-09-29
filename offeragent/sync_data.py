# -*- coding: utf-8 -*-
"""
sync_data.py —— OfferAgent 数据持久化（Streamlit Cloud 无持久磁盘的根治方案）
============================================================================
问题：Streamlit Cloud 每次重启都回到仓库代码，data/ 里的岗位库/记忆/日志全部丢失。
根治：把 data/ 放进私有 GitHub 仓库（yjmyp/offeragent-data），本地是权威，云端启动自动拉取。

三种模式：
  python sync_data.py push       本地 data/ 打包 → 提交私有仓库（zip 备份，需网络可达 github.com）
  python sync_data.py pull       git 拉取私有仓库 zip 恢复；git 不通自动降级 api_pull
  python sync_data.py api_pull   走 GitHub API 拉 offeragent_data.json 数据包解包（云端推荐）

环境变量（或 .streamlit/secrets.toml）：
  GITHUB_PAT   访问私有仓库的 token（没有时本机走 Git Credential Manager）
  DATA_REPO    私有仓库名（默认 yjmyp/offeragent-data）

敏感隔离：edge_profile（BOSS 登录态 534MB）、shots/、*.png 永不进入仓库。
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SKIP_DIRS = {"edge_profile", "shots", "distill_test", "__pycache__"}
SKIP_EXTS = (".png", ".jpg", ".jpeg")


def _repo_url() -> str:
    pat = os.environ.get("GITHUB_PAT", "")
    repo = os.environ.get("DATA_REPO", "yjmyp/offeragent-data")
    if pat:
        return f"https://{pat}@github.com/{repo}.git"
    return f"https://github.com/{repo}.git"


def _git(*args, cwd=None):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 失败：{r.stderr.strip()[:300]}")
    return r


def _zip_data(dest_dir: Path) -> Path:
    """把 data/ 打包成 zip（排除敏感/超大项；zip 内路径以 offeragent/data/ 开头防逃逸）。"""
    out = dest_dir / f"offeragent_data_{time.strftime('%Y%m%d_%H%M%S')}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(DATA):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fn in files:
                if fn.lower().endswith(SKIP_EXTS):
                    continue
                full = Path(root) / fn
                z.write(full, Path("offeragent") / full.relative_to(HERE))
    return out


def _unzip_data(zip_path: Path, dest: Path = HERE) -> int:
    """只解压 offeragent/data/ 前缀条目到 dest（防路径逃逸）。"""
    restored = 0
    with zipfile.ZipFile(zip_path) as z:
        for n in z.namelist():
            if not n.startswith("offeragent/data/"):
                continue
            target = dest / n
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(n) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            restored += 1
    return restored


def _unzip_data_into(zip_path: Path, repo_dir: Path):
    """解压 zip 的 data 部分到仓库工作区（push 用）。"""
    with zipfile.ZipFile(zip_path) as z:
        for n in z.namelist():
            if not n.startswith("offeragent/data/"):
                continue
            target = repo_dir / n
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(n) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)


def push():
    """本地是权威：打包 data/ → clone 私有仓库 → 覆盖 → push。"""
    pat = os.environ.get("GITHUB_PAT", "")
    if not pat:
        print("ℹ️ 未配置 GITHUB_PAT，改用本机 git 凭据（Git Credential Manager）")
    print("📦 打包本地 data/ …")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        z = _zip_data(tmp)
        repo_dir = tmp / "repo"
        print("⏬ clone 私有仓库 …")
        _git("clone", "--depth", "1", _repo_url(), str(repo_dir))
        bk_dir = repo_dir / "offeragent" / "backups"
        bk_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(z, bk_dir / z.name)
        data_dir = repo_dir / "offeragent" / "data"
        if data_dir.exists():
            for p in data_dir.iterdir():
                if p.name == ".gitkeep":
                    continue
                p.unlink() if p.is_file() else shutil.rmtree(p)
        _unzip_data_into(z, repo_dir)
        _git("add", "-A", cwd=repo_dir)
        _git("commit", "-m", f"data sync {time.strftime('%Y-%m-%d %H:%M:%S')}", cwd=repo_dir)
        print("🚀 push …")
        _git("push", "origin", "HEAD", cwd=repo_dir)
    print("✅ 数据已同步到私有仓库")


def _git_pull():
    """git 模式：clone 私有仓库 → 用最新 zip 恢复。"""
    print("⏬ clone 私有仓库 …")
    with tempfile.TemporaryDirectory() as td:
        repo_dir = Path(td) / "repo"
        _git("clone", "--depth", "1", _repo_url(), str(repo_dir))
        zips = sorted((repo_dir / "offeragent" / "backups").glob("*.zip"))
        if not zips:
            raise RuntimeError("私有仓库里没有数据备份 zip（先在本地跑 push）")
        n = _unzip_data(zips[-1])
        print(f"✅ git 恢复 {n} 个文件")


def _api_pull_data(pat: str) -> int:
    """GitHub Contents API 拉 offeragent_data.json → 解包回 data/（云端推荐，无需 git）。"""
    repo = os.environ.get("DATA_REPO", "yjmyp/offeragent-data")
    url = f"https://api.github.com/repos/{repo}/contents/offeragent_data.json"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {pat}",
                                               "User-Agent": "offeragent"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        meta = json.load(resp)
    pack = json.loads(base64.b64decode(meta["content"]))
    restored = 0
    for rel, content in pack.get("files", {}).items():
        target = HERE / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str) and content.startswith("b64:"):
            target.write_bytes(base64.b64decode(content[4:]))
        else:
            target.write_text(content, encoding="utf-8")
        restored += 1
    return restored


def api_pull():
    pat = os.environ.get("GITHUB_PAT", "")
    if not pat:
        print("❌ api_pull 需要 GITHUB_PAT（Secrets / 环境变量）")
        sys.exit(1)
    print("⬇️ API 拉取数据包 …")
    n = _api_pull_data(pat)
    print(f"✅ 已恢复 {n} 个文件（岗位库/画像/报告/日志）")


def pull():
    """git 优先，失败自动降级 api_pull。"""
    pat = os.environ.get("GITHUB_PAT", "")
    if not pat:
        print("ℹ️ 未配置 GITHUB_PAT，改用本机 git 凭据（Git Credential Manager）")
    try:
        _git_pull()
    except Exception as e:
        print(f"⚠️ git 拉取失败（{str(e)[:100]}），降级 api_pull")
        if pat:
            n = _api_pull_data(pat)
            print(f"✅ API 恢复 {n} 个文件")
        else:
            print("❌ 无 GITHUB_PAT 无法降级：网络恢复后重试，或配置 PAT")
            sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "push":
        push()
    elif len(sys.argv) >= 2 and sys.argv[1] == "pull":
        pull()
    elif len(sys.argv) >= 2 and sys.argv[1] == "api_pull":
        api_pull()
    else:
        print("用法：python sync_data.py push | pull | api_pull\n"
              "环境变量：GITHUB_PAT、DATA_REPO（默认 yjmyp/offeragent-data）")
