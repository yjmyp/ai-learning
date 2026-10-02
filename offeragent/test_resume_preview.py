# -*- coding: utf-8 -*-
"""简历模板预览的验收：三套模板有没有被裁 / 留大片空白，照片样式有没有生效。

为什么专门测这个：预览用「缩放进 Streamlit」实现，踩过两个坑——
  ① 用 transform: scale 缩放：容器按未缩放高度撑开 → 缩略图下面一大片空白
  ② 作用域 class 带了点（class=".oa-pv-classic"）→ 预览样式全失效，
     照片按原图 600x800 撑开，看起来就是"排版乱 + 图片不对"

这个脚本直接量 DOM：容器高度 vs 内容视觉高度、页脚在不在框内、照片渲染尺寸。

跑法：python offeragent/test_resume_preview.py（需要 localhost:8501 在跑）
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import browser_fetch as bf  # noqa: E402

# 每套模板打印态的照片尺寸（CSS 里写死的），用来验证 CSS 真的生效了
PHOTO_RULE = {"classic": (104, 140), "sidebar": (120, 158), "compact": (96, 128)}

MEASURE_JS = """
(function(){
  function measure(wrap){
    var inner = wrap.firstElementChild;
    var wr = wrap.getBoundingClientRect();
    var ir = inner.getBoundingClientRect();
    var foot = inner.querySelector('.foot');
    var fr = foot ? foot.getBoundingClientRect() : null;
    return {
      cls: wrap.className,
      zoom: getComputedStyle(inner).zoom,
      wrap_h: Math.round(wr.height),
      inner_visual_h: Math.round(ir.height),
      blank: Math.round(wr.height - ir.height),
      clipped: Math.round(ir.height) > Math.round(wr.height) + 2,
      foot_visible: fr ? (fr.bottom <= wr.bottom + 2) : null
    };
  }
  var out = {tpls: {}, photos: []};
  ['classic','sidebar','compact'].forEach(function(t){
    // 类名现在带实例后缀（-grid / -zoom），按前缀选
    var wraps = [].slice.call(document.querySelectorAll('[class^="oa-pv-wrap-' + t + '"]'));
    out.tpls[t] = wraps.map(measure);
  });
  document.querySelectorAll('img[alt="照片"]').forEach(function(im){
    var r = im.getBoundingClientRect();
    out.photos.push({w: Math.round(r.width), h: Math.round(r.height),
                     natW: im.naturalWidth, natH: im.naturalHeight,
                     loaded: im.complete && im.naturalWidth > 0});
  });
  return JSON.stringify(out);
})()
"""


def main():
    if not bf.launch(headless=True):
        raise SystemExit("Edge 启动失败")
    ws = bf._new_tab("http://localhost:8501/resume")
    cdp = bf._CDP(ws)
    cdp.call("Page.enable")
    cdp.call("Emulation.setDeviceMetricsOverride", {
        "width": 1500, "height": 1100, "deviceScaleFactor": 1, "mobile": False})
    time.sleep(15)
    raw = cdp.call("Runtime.evaluate", {"expression": MEASURE_JS, "returnByValue": True},
                   timeout=60).get("result", {}).get("value")
    cdp.close()
    d = json.loads(raw)

    bad = []
    print("== 每套模板的每个预览块（缩略 + 放大） ==")
    for t, items in d["tpls"].items():
        if not items:
            print(f"❌ {t}: 没找到预览容器")
            bad.append(f"{t}:容器缺失")
            continue
        for i, m in enumerate(items, 1):
            head = f"{t}#{i}(zoom={m['zoom']})"
            if m["clipped"]:
                print(f"❌ {head} 被裁：内容 {m['inner_visual_h']} > 容器 {m['wrap_h']}")
                bad.append(f"{t}#{i}:被裁")
            elif m["blank"] > 24:
                print(f"❌ {head} 留白 {m['blank']}px（容器 {m['wrap_h']} > 内容 "
                      f"{m['inner_visual_h']}）")
                bad.append(f"{t}#{i}:留白")
            elif m["foot_visible"] is False:
                print(f"❌ {head} 页脚不可见（应显示到脚注）")
                bad.append(f"{t}#{i}:页脚不可见")
            else:
                print(f"✅ {head} 容器 {m['wrap_h']}px = 内容 {m['inner_visual_h']}px，页脚可见")

    print()
    print("== 照片（CSS 生效的话应该是 模板尺寸 × zoom） ==")
    if not d["photos"]:
        print("ℹ️ 预览里没有照片（本机 简历/照片.jpg 不存在）——放一张再测更准")
    for p in d["photos"]:
        ratio = round(p["h"] / p["w"], 3) if p["w"] else 0
        ok = p["loaded"] and 1.3 < ratio < 1.4 and p["w"] < 200
        print(("✅ " if ok else "❌ ")
              + f"{p['w']}x{p['h']}（原图 {p['natW']}x{p['natH']}，比例 {ratio}）")
        if not ok:
            bad.append("照片尺寸不对")

    print()
    if bad:
        print("❌ 有问题：", bad)
        return 1
    print("✅ 三套模板预览都完整、照片样式生效")
    return 0


if __name__ == "__main__":
    sys.exit(main())
