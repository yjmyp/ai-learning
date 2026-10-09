# -*- coding: utf-8 -*-
"""名片页额度守卫验收：防刷（按访问者 + 每日总额度）。

为什么要有它：名片页免密公开，每次提问都花真实模型额度。
限额逻辑写错的两个方向都很糟——放开（被刷光）或过严（面试官问两下就被拒），
所以边界要用测试钉死。

跑法：python offeragent/test_twin_guard.py
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import twin_guard  # noqa: E402


def main():
    tmp = tempfile.mkdtemp(prefix="oa_twin_")
    twin_guard.QUOTA_PATH = __import__("pathlib").Path(tmp) / "twin_quota.json"
    checks = []

    # 1) 同一 IP 连续提问：前 3 次允许，第 4 次被拒（把单 IP 上限压到 3 便于测边界）
    results = [twin_guard.check("1.1.1.1", per_ip=3, daily=100)[0] for _ in range(4)]
    checks.append(("同一访问者：3 次允许 + 第 4 次拒绝（%s）" % results,
                   results == [True, True, True, False]))

    # 2) 剩余次数递减
    data = json.loads(twin_guard.QUOTA_PATH.read_text(encoding="utf-8"))
    checks.append(("计数落在文件里且当天累加（%s）" % data.get("ips"), data["ips"].get("1.1.1.1") == 3))

    # 3) 换一个 IP 仍然可以问（额度是按人算的，不是全局一刀切）
    ok, _, left = twin_guard.check("2.2.2.2", per_ip=3, daily=100)
    checks.append(("换个访问者不受前一个影响（剩余 %d）" % left, ok and left == 2))

    # 4) 每日总额度封顶：即使一直换 IP，总量也到顶就停
    #    先把状态清干净——当天总额度是跨 IP 累积的，前面几步已经吃掉一部分，
    #    不隔离就会出现"测的是前面积累"的假失败（第一版就踩了）
    twin_guard.QUOTA_PATH.unlink(missing_ok=True)
    r = [twin_guard.check("9.9.9.%d" % i, per_ip=100, daily=2)[0] for i in range(1, 5)]
    checks.append(("每日总额度封顶（%s）" % r, r == [True, True, False, False]))

    # 5) 取不到 IP 时退化为 unknown —— 仍然受限，不能放开
    ok1, _, _ = twin_guard.check("unknown", per_ip=1, daily=100)
    ok2, reason, _ = twin_guard.check("unknown", per_ip=1, daily=100)
    checks.append(("取不到 IP 时依然受限（第 2 次拒绝：%s）" % reason[:20], ok1 is True and ok2 is False))

    # 6) 换天自动清零（避免文件无限增长、避免"昨天刷完了今天还锁着"）
    twin_guard.QUOTA_PATH.write_text(json.dumps(
        {"date": "2000-01-01", "ips": {"1.1.1.1": 99}, "days": {"2000-01-01": 99}}), encoding="utf-8")
    ok, _, left = twin_guard.check("1.1.1.1", per_ip=3, daily=100)
    checks.append(("跨天自动清零（剩余 %d）" % left, ok and left == 2))

    ok_count = sum(1 for _, v in checks if v)
    for name, good in checks:
        print(("✅ " if good else "❌ ") + name)
    print("\n%d/%d 通过" % (ok_count, len(checks)))
    return 0 if ok_count == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
