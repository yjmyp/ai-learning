# -*- coding: utf-8 -*-
"""
sync_data.py —— OfferAgent 数据持久化（Streamlit Cloud 无持久磁盘的根治方案）
============================================================================
问题：Streamlit Cloud 每次重启都回到仓库代码，data/ 里的岗位库/记忆/日志全部丢失。
根治：把 data/ 放进一个**私有 GitHub 仓库**，本地是权威，云端启动时自动拉取。

用法（本地）：
  python sync_data.py push        # 本地 data/ 打包 → 提交私有仓库（本地是权威）
  python sync_data.py pull        # 私有仓库 → 解压覆盖本地 data/
环境变量（或 .streamlit/secrets.toml）：
  GITHUB_PAT   读/写私有仓库的 Personal Access Token（需 repo 权限）
  DATA_REPO    私有仓库名，如 yjmyp/offeragent-data（默认）

云端：Streamlit Cloud Secrets 里配 GITHUB_PAT + DATA_REPO，
      app 启动时检测岗位库为空会自动 pull（见 offer_agent_app.py 启动钩子）。
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"


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
    """把 data/ 打包成 zip（zip 内路径以 offeragent/data/ 开头，防恢复时路径逃逸）。"""
    out = dest_dir / f"offeragent_data_{time.strftime('%Y%m%d_%H%M%S')}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _dirs, files in os.walk(DATA):
            for fn in files:
                full = Path(root) / fn
                arc = Path("offeragent") / full.relative_to(HERE)
                z.write(full, str(arc))
    return out


def _unzip_data(zip_path: Path):
    """只解压 offeragent/data/ 前缀的条目到项目根（防路径逃逸）。"""
    restored = 0
    with zipfile.ZipFile(zip_path) as z:
        for n in z.namelist():
            if not n.startswith("offeragent/data/"):
                continue
            target = HERE / n
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(n) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            restored += 1
    print(f"✅ 解压 {restored} 个文件")


def push():
    pat = os.environ.get("GITHUB_PAT", "")
    if not pat:
        print("❌ 未配置 GITHUB_PAT：push 私有仓库需要 token（GitHub → Settings → Developer settings → "
              "Personal access tokens，勾 repo 权限）")
        sys.exit(1)
    print("📦 打包本地 data/ …")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        z = _zip_data(tmp)
        repo_dir = tmp / "repo"
        print("⏬ clone 私有仓库 …")
        _git("clone", "--depth", "1", _repo_url(), str(repo_dir))
        # ① 备份 zip 放进仓库 backups/（供云端/换机 pull 恢复）
        bk_dir = repo_dir / "offeragent" / "backups"
        bk_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(z, bk_dir / z.name)
        # ② 清掉仓库里的旧 data（保留 .gitkeep），再解压新的
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


def _unzip_data_into(zip_path: Path, repo_dir: Path):
    with zipfile.ZipFile(zip_path) as z:
        for n in z.namelist():
            if not n.startswith("offeragent/data/"):
                continue
            target = repo_dir / n
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(n) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)


def pull():
    pat = os.environ.get("GITHUB_PAT", "")
    if not pat:
        print("❌ 未配置 GITHUB_PAT：私有仓库需要 token 才能读")
        sys.exit(1)
    print("⏬ clone 私有仓库 …")
    with tempfile.TemporaryDirectory() as td:
        repo_dir = Path(td) / "repo"
        _git("clone", "--depth", "1", _repo_url(), str(repo_dir))
        zips = sorted((repo_dir / "offeragent" / "backups").glob("*.zip")) if (repo_dir / "offeragent" / "backups").exists() else []
        if not zips:
            print("❌ 仓库里没有数据备份 zip（先在本地跑 python sync_data.py push）")
            sys.exit(1)
        print(f"📦 找到 {len(zips)} 份备份，用最新一份恢复 …")
        _unzip_data(zips[-1])
    print("✅ 已从私有仓库恢复 data/（岗位库 / 记忆 / 日志）")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "push":
        push()
    elif len(sys.argv) >= 2 and sys.argv[1] == "pull":
        pull()
    else:
        print("用法：python sync_data.py push | pull\n"
              "环境变量：GITHUB_PAT（必填）、DATA_REPO（默认 yjmyp/offeragent-data）")
