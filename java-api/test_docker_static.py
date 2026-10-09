# -*- coding: utf-8 -*-
"""java-api Docker 配置静态校验（本机没装 Docker，用静态检查兜住低级错误）

为什么要有它：Dockerfile / compose 写错，本地没 Docker 就只能在别人机器上炸。
这里把"能静态查出来的错"全查一遍：多阶段构建、非 root、healthcheck、
compose 里 depends_on 是否等健康、环境变量是否齐、构建上下文对不对、
以及**YAML 重复键**（我写过一次重复的 environment，后一个会静默覆盖前一个）。

跑法：python java-api/test_docker_static.py
真构建验收在有 Docker 的机器上跑：docker compose -f java-api/docker-compose.yml up --build
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


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def strict_load(text):
    """用严格的 YAML 加载器解析：**同一个 mapping 里出现重复 key 直接报错**。

    为什么需要：PyYAML 默认对重复键是"后者覆盖前者"且不吭声。
    我写 compose 时就踩过——java-api 服务下写了两个 environment 块，
    结果数据源配置被静默丢掉，容器起来连不上库，排查半天。
    这个检查在没有 Docker 的机器上也能跑，属于"静态就能查出来的错"。
    """
    import yaml

    class StrictLoader(yaml.SafeLoader):
        pass

    def no_duplicates(loader, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in mapping:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping", node.start_mark,
                    "发现重复键 %r（YAML 会用后一个覆盖前一个，配置会被静默丢掉）" % key,
                    key_node.start_mark)
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    StrictLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, no_duplicates)
    return yaml.load(text, Loader=StrictLoader)


def main():
    checks = []
    dockerfile = os.path.join(HERE, "Dockerfile")
    compose = os.path.join(HERE, "docker-compose.yml")
    ignore = os.path.join(HERE, ".dockerignore")

    checks.append(("Dockerfile 存在", os.path.exists(dockerfile)))
    checks.append(("docker-compose.yml 存在", os.path.exists(compose)))
    checks.append((".dockerignore 存在", os.path.exists(ignore)))

    df = read(dockerfile) if os.path.exists(dockerfile) else ""
    checks.append(("多阶段构建（build + 运行两个 FROM）", len(re.findall(r"^FROM ", df, re.M)) >= 2))
    checks.append(("先拷 pom 再拷源码（依赖层可缓存）",
                   df.find("COPY java-api/pom.xml") < df.find("COPY java-api/src")
                   and "COPY java-api/pom.xml" in df))
    checks.append(("不以 root 运行（USER 非 root）",
                   bool(re.search(r"^USER (?!root)\S+", df, re.M))))
    checks.append(("有 HEALTHCHECK", "HEALTHCHECK" in df))
    checks.append(("暴露 8080", "EXPOSE 8080" in df))
    checks.append(("JVM 容器感知参数", "UseContainerSupport" in df or "MaxRAMPercentage" in df))
    checks.append(("密钥不写死在 Dockerfile 里",
                   not re.search(r"(?i)(api[_-]?key|password)\s*=\s*[\"'][^\"']{6,}", df)))

    ig = read(ignore) if os.path.exists(ignore) else ""
    checks.append((".dockerignore 排除 target/（否则镜像里塞 60MB jar）", "target/" in ig))
    checks.append((".dockerignore 排除 .git/", ".git/" in ig))

    cp = read(compose) if os.path.exists(compose) else ""
    dup_msg = "无"
    try:
        doc = strict_load(cp)
        checks.append(("compose 没有重复键（严格加载通过）", True))
    except ImportError:
        doc = None
        checks.append(("compose 没有重复键（缺 pyyaml，跳过）", None))
    except Exception as e:
        doc = None
        first = str(e).strip().splitlines()
        dup_msg = next((l for l in first if "重复键" in l), first[-1] if first else str(e))
        checks.append(("compose 没有重复键（%s）" % dup_msg[:80], False))
    for svc in ["mysql", "redis", "java-api"]:
        checks.append(("compose 定义了 %s 服务" % svc, re.search(r"^  %s:" % re.escape(svc), cp, re.M) is not None))
    checks.append(("java-api 等 mysql/redis 健康后再启动",
                   "condition: service_healthy" in cp))
    checks.append(("mysql 有数据卷（容器重建不丢库）", "oa-mysql-data:/var/lib/mysql" in cp))
    checks.append(("API Key 通过环境变量注入（不写死）",
                   "OFFERAGENT_API_KEY: ${" in cp and "dev-local-key" not in cp))
    checks.append(("构建上下文是仓库根且指向 java-api/Dockerfile",
                   "context: .." in cp and "dockerfile: java-api/Dockerfile" in cp))

    # 用上面的严格解析结果继续做结构断言
    try:
        if doc is None:
            import yaml
            doc = yaml.safe_load(cp)
        services = (doc or {}).get("services", {})
        checks.append(("compose YAML 可解析，服务=%s" % list(services), len(services) >= 3))
        env = services.get("java-api", {}).get("environment", {})
        checks.append(("java-api 环境变量含数据源/Redis/Key/JDS 四项",
                       all(k in env for k in ["SPRING_DATASOURCE_URL", "SPRING_DATA_REDIS_HOST",
                                              "OFFERAGENT_API_KEY", "OFFERAGENT_JDS_DIR"])))
    except Exception as e:
        checks.append(("compose YAML 可解析（%s）" % str(e)[:60], False))

    ok = sum(1 for _, v in checks if v is True)
    skipped = [n for n, v in checks if v is None]
    for name, good in checks:
        print(("✅ " if good is True else ("⏭️ " if good is None else "❌ ")) + name)
    print("\n%d 通过 / %d 跳过 / 共 %d" % (ok, len(skipped), len(checks)))
    return 0 if ok == len(checks) - len(skipped) else 1


if __name__ == "__main__":
    sys.exit(main())
