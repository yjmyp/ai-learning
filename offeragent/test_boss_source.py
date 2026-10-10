# -*- coding: utf-8 -*-
"""BOSS 来源的离线验收：字段映射 + 城市过滤 + 接口 JS 拼装。**不联网、不开浏览器。**

背景（真实事故，2026-10-10）：用户搜「AI + 南京」，BOSS直聘返回 **0 条**。
根因有两条，这个测试把它们钉住：
  ① BOSS 前端会用它自己记的"上次选中城市"覆盖 URL 里的 city 参数 → 返回的是德阳岗位
     → 客户端严格城市过滤把结果全砍掉 → 0 条。改法：走 BOSS 页面自己调的那个搜索接口
     （city 由参数决定，不会被打扮覆盖），再自己把 JSON 映射成字段。
  ② 老的"抓页面文本 → 大模型抽"这条路在城市被覆盖时必然抽到别的城市，所以只留作兜底。

跑法：python offeragent/test_boss_source.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import job_sources as js  # noqa: E402

# 真实接口返回的一条（字段名照抄线上，值做了替换）
SAMPLE = [{
    "jobName": "AI应用开发工程师", "salaryDesc": "15-25K",
    "cityName": "南京", "areaDistrict": "雨花台区", "businessDistrict": "安德门",
    "skills": ["Python", "RAG", "大模型"], "jobLabels": ["3-5年", "本科"],
    "welfareList": ["五险一金", "年终奖"], "brandName": "南京迈特望",
    "brandIndustry": "人工智能", "brandScaleName": "100-499人",
    "bossName": "张女士", "bossTitle": "招聘者", "encryptJobId": "abc123xyz",
}, {
    "jobName": "AI产品经理", "salaryDesc": "20-30K",
    "cityName": "上海", "areaDistrict": "浦东新区", "businessDistrict": "",
    "skills": [], "jobLabels": ["经验不限"], "welfareList": [],
    "brandName": "某上海公司", "encryptJobId": "sh001",
}]


def test_map_fields():
    d = {}
    jobs = js._boss_map(SAMPLE, ["ai"], ["南京"], diag=d)
    j = jobs[0]
    return (j["title"] == "AI应用开发工程师"
            and j["salary"] == "15-25K"
            and j["company"] == "南京迈特望"
            and j["city"] == "南京·雨花台区·安德门"
            and j["url"] == "https://www.zhipin.com/job_detail/abc123xyz.html"
            and j["source"] == "BOSS直聘"
            and "Python" in j["jd"] and "五险一金" in j["jd"]
            and d["raw"] == 2 and d["kept"] == 2
            and d["source_api"].startswith("站点搜索接口"))


def test_city_flag_and_sort():
    """南京命中、上海不命中；命中排前面（城市过滤靠这个标志）。"""
    jobs = js._boss_map(SAMPLE, ["ai"], ["南京"])
    by_city = {j["city"].split("·")[0]: j["city_hit"] for j in jobs}
    return by_city == {"南京": True, "上海": False} and jobs[0]["city"].startswith("南京")


def test_city_hit_helper():
    """city_hit 要认得「南京·雨花台区·安德门」这种带区县的写法。"""
    return (js.city_hit("南京·雨花台区·安德门", ["南京"]) is True
            and js.city_hit("上海·浦东新区", ["南京"]) is False)


def test_api_js_shape():
    """接口 JS 里必须带对城市码、页数、每页条数（不然又会搜到别的城市）。"""
    src = js._boss_api_js("101190100", "AI", 5, 30)
    return (js.BOSS_API in src and "101190100" in src
            and "p <= 5" in src and "pageSize=30" in src
            and "query=AI" in src and "credentials: 'include'" in src)


def test_boss_city_code_table():
    """常见城市的 BOSS 城市码要和线上一致（南京/北京/深圳这几个最常用）。"""
    return (js.BOSS_CITY_CODES.get("南京") == "101190100"
            and js.BOSS_CITY_CODES.get("北京") == "101010100"
            and js.BOSS_CITY_CODES.get("深圳") == "101280600"
            and len(js.BOSS_CITY_CODES) >= 30)


def main():
    checks = [
        ("接口 JSON → 我们的字段（标题/薪资/公司/城市/链接/JD 摘要）", test_map_fields()),
        ("城市命中标志：南京 True、上海 False，且命中排前面", test_city_flag_and_sort()),
        ("city_hit 认得「南京·雨花台区·安德门」", test_city_hit_helper()),
        ("接口 JS 带对城市码/页数/每页条数/登录 cookie", test_api_js_shape()),
        ("BOSS 城市码表与线上一致（南京=101190100 等）", test_boss_city_code_table()),
    ]
    ok_n = sum(1 for _, v in checks if v)
    for name, good in checks:
        print(("✅ " if good else "❌ ") + name)
    print("\n%d/%d 通过" % (ok_n, len(checks)))
    return 0 if ok_n == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
