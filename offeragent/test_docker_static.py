# -*- coding: utf-8 -*-
"""Docker 配置静态校验（本机没装 Docker，用静态检查兜住低级错误）

检查项：compose 能被解析；build context / dockerfile 路径存在；
Dockerfile 里 COPY 的源文件存在；端口与 HEALTHCHECK 路径与应用一致；
volume 挂载目录存在。

跑法：python offeragent/test_docker_static.py
（装好 Docker 后真正的验收是：docker compose -f offeragent/docker-compose.yml up --build）
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main():
    checks = []
    compose_path = os.path.join(HERE, "docker-compose.yml")
    dockerfile_path = os.path.join(HERE, "Dockerfile")
    checks.append(("docker-compose.yml 存在", os.path.exists(compose_path)))
    checks.append(("Dockerfile 存在", os.path.exists(dockerfile_path)))

    compose_txt = open(compose_path, encoding="utf-8").read() if os.path.exists(compose_path) else ""
    try:
        import yaml
        data = yaml.safe_load(compose_txt)
        svc = (data or {}).get("services", {}).get("offeragent", {})
        checks.append(("compose 能被 YAML 解析且有 offeragent 服务", bool(svc)))
    except Exception as e:
        svc = {}
        checks.append(("compose 能被 YAML 解析", False))
        print("   yaml 解析失败：", e)

    ctx = os.path.abspath(os.path.join(HERE, svc.get("build", {}).get("context", ".")))
    # 注意：dockerfile 是相对 **build context**（仓库根）解析的，不是相对本文件所在目录
    df = os.path.abspath(os.path.join(ctx, svc.get("build", {}).get("dockerfile", "Dockerfile")))
    checks.append(("build context（仓库根）存在", os.path.isdir(ctx)))
    checks.append(("dockerfile 路径解析正确", os.path.abspath(df) == os.path.abspath(dockerfile_path)))
    checks.append(("requirements.txt 在 context 内可 COPY",
                   os.path.exists(os.path.join(ctx, "offeragent", "requirements.txt"))))

    df_txt = open(dockerfile_path, encoding="utf-8").read() if os.path.exists(dockerfile_path) else ""
    # CMD 是多行写法，所以分别检查命令与入口文件
    checks.append(("Dockerfile 里有 streamlit 启动命令",
                   "streamlit" in df_txt and "offer_agent_app.py" in df_txt))
    checks.append(("健康检查指向 /_stcore/health", "/_stcore/health" in df_txt))
    ports = svc.get("ports") or []
    checks.append(("容器端口 8501 与 Streamlit 一致",
                   any(str(p).endswith("8501") for p in ports)))
    vols = svc.get("volumes") or []
    data_vol = [v for v in vols if "data" in str(v)]
    checks.append(("data 目录挂了 volume（重建不丢数据）", bool(data_vol)))
    if data_vol:
        src = str(data_vol[0]).split(":")[0]
        checks.append(("volume 源目录存在（%s）" % src,
                       os.path.isdir(os.path.abspath(os.path.join(HERE, src)))))
    checks.append(("密钥走环境变量而非写死在镜像里",
                   "DEEPSEEK_API_KEY" in compose_txt and "sk-" not in df_txt))

    ok = 0
    for name, good in checks:
        print(("OK  " if good else "FAIL ") + name)
        ok += 1 if good else 0
    print("\n%d/%d 通过（本机无 Docker，这里只做静态校验；真实构建需在有 Docker 的机器上跑）"
          % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
