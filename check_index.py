#!/usr/bin/env python3
"""
慧见 WISESIGHT 外链收录自动检测
每天运行，检测各平台是否收录了慧见的产品页面
结果写入 results/YYYY-MM-DD.json 和 README.md
"""

import json
import os
import time
import random
import re
import datetime
from pathlib import Path

# ── 配置 ──────────────────────────────────────────
PRODUCT_NAME   = "慧见 WISESIGHT"
PRODUCT_DOMAIN = "wisesme.cn"
SEARCH_ENGINE  = "duckduckgo"   # duckduckgo | google_custom | google_html

# Google Custom Search API（可选，填了则用 API，否则用 DuckDuckGo）
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID", "")

# 平台列表（和 HTML 工具里的 PLATFORMS 对应）
PLATFORMS = [
    # AI 工具目录（高优先级）
    {"name": "There's An AI For That", "url": "https://theresanaiforthat.com",   "cat": "AI"},
    {"name": "Futurepedia",             "url": "https://www.futurepedia.io",     "cat": "AI"},
    {"name": "ListMyAI",               "url": "https://listmyai.net",            "cat": "AI"},
    {"name": "Uneed",                   "url": "https://www.uneed.best",         "cat": "AI"},
    {"name": "AI Tools Directory",       "url": "https://www.aitoolsdirectory.com","cat": "AI"},
    {"name": "Supertools",              "url": "https://supertools.ai",           "cat": "AI"},
    {"name": "All Things AI",           "url": "https://allthingsai.com",        "cat": "AI"},
    {"name": "GPTs Hunter",             "url": "https://www.gptshunter.com",     "cat": "AI"},
    {"name": "AIGC Open",              "url": "https://www.aigc.cn",            "cat": "AI"},
    {"name": "AITOP100",                "url": "https://www.aitop100.cn",        "cat": "AI"},
    # 中文导航站
    {"name": "AI工具集",    "url": "https://ai-bot.cn/tools",     "cat": "中文AI"},
    {"name": "Toolify中文版", "url": "https://www.toolify.ai/zh",  "cat": "中文AI"},
    {"name": "办公人导航",   "url": "https://www.bgrdh.com",       "cat": "中文AI"},
    {"name": "AIBase",      "url": "https://www.aibase.com",       "cat": "中文AI"},
    # Startup 目录
    {"name": "Product Hunt",    "url": "https://www.producthunt.com", "cat": "Startup"},
    {"name": "G2",              "url": "https://www.g2.com",              "cat": "SaaS"},
    {"name": "AlternativeTo",    "url": "https://alternativeto.net",      "cat": "Tool"},
    {"name": "SourceForge",     "url": "https://sourceforge.net",        "cat": "Developer"},
    {"name": "Capterra",        "url": "https://www.capterra.com",      "cat": "SaaS"},
    # 知乎（已发布文章）
    {"name": "知乎专栏", "url": "https://www.zhihu.com", "cat": "内容", "article_url": "https://www.zhihu.com/answer/2053180865660850816"},
]

# ── 检测核心 ────────────────────────────────────────
def check_google_custom(platform_url: str) -> dict:
    """用 Google Custom Search API 检测（最可靠，需 API key）"""
    import requests
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        return {"method": "google_custom", "error": "NO_API_KEY", "found": None}
    query = f"site:{platform_url.replace('https://','').replace('http://','').rstrip('/')} {PRODUCT_NAME}"
    try:
        resp = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={"key": GOOGLE_API_KEY, "cx": GOOGLE_CSE_ID, "q": query, "num": 5},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        found = len(items) > 0
        urls = [it["link"] for it in items[:3]]
        return {"method": "google_custom", "found": found, "count": len(items), "urls": urls}
    except Exception as e:
        return {"method": "google_custom", "error": str(e), "found": None}


def check_duckduckgo(platform_url: str) -> dict:
    """用 DuckDuckGo HTML 搜索检测（免费，无需 API key）"""
    import requests
    from urllib.parse import quote
    domain = platform_url.replace("https://", "").replace("http://", "").rstrip("/")
    query = f"site:{domain} {PRODUCT_NAME}"
    try:
        resp = requests.get(
            f"https://html.duckduckgo.com/html/?q={quote(query)}",
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            timeout=15,
        )
        resp.raise_for_status()
        html = resp.text
        # 简单判断：搜索结果里是否出现了产品域名
        found = PRODUCT_DOMAIN in html
        # 尝试提取结果链接
        urls = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"', html)
        return {"method": "duckduckgo", "found": found, "count": len(urls), "urls": urls[:3]}
    except Exception as e:
        return {"method": "duckduckgo", "error": str(e), "found": None}


def check_google_html(platform_url: str) -> dict:
    """直接请求 Google 搜索页（不稳定，仅备用）"""
    import requests
    from urllib.parse import quote
    domain = platform_url.replace("https://", "").replace("http://", "").rstrip("/")
    query = f"site:{domain} {PRODUCT_NAME}"
    try:
        resp = requests.get(
            f"https://www.google.com/search?q={quote(query)}&num=5",
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            timeout=15,
        )
        resp.raise_for_status()
        html = resp.text
        found = PRODUCT_DOMAIN in html
        return {"method": "google_html", "found": found, "count": None, "urls": []}
    except Exception as e:
        return {"method": "google_html", "error": str(e), "found": None}


def check_platform(p: dict) -> dict:
    """检测单个平台"""
    result = {
        "platform": p["name"],
        "platform_url": p["url"],
        "product": PRODUCT_NAME,
        "product_domain": PRODUCT_DOMAIN,
        "checked_at": datetime.datetime.utcnow().isoformat() + "Z",
    }
    if "article_url" in p:
        result["article_url"] = p["article_url"]

    # 选择检测方法
    if SEARCH_ENGINE == "google_custom" and GOOGLE_API_KEY:
        r = check_google_custom(p["url"])
    elif SEARCH_ENGINE == "duckduckgo":
        r = check_duckduckgo(p["url"])
    else:
        r = check_google_html(p["url"])

    result["method"]   = r["method"]
    result["found"]    = r["found"]
    result["count"]    = r.get("count")
    result["found_urls"] = r.get("urls", [])
    if "error" in r:
        result["error"] = r["error"]

    return result


# ── 主流程 ────────────────────────────────────────
def main():
    today = datetime.date.today().isoformat()
    print(f"🔍 开始检测 {today}  |  产品: {PRODUCT_NAME}  |  方法: {SEARCH_ENGINE}")

    results = []
    for i, p in enumerate(PLATFORMS):
        print(f"  [{i+1}/{len(PLATFORMS)}] {p['name']} ... ", end="", flush=True)
        r = check_platform(p)
        status = "✅ 已收录" if r["found"] else ("❌ 未收录" if r["found"] is False else "⚠️ 检测失败")
        print(status)
        results.append(r)
        # 随机延迟，避免被限流
        if i < len(PLATFORMS) - 1:
            time.sleep(random.uniform(3, 7))

    # 保存 JSON
    out_file = Path("results") / f"{today}.json"
    out_file.parent.mkdir(exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"date": today, "product": PRODUCT_NAME, "results": results}, f, ensure_ascii=False, indent=2)
    print(f"\n📦 JSON 结果已保存: {out_file}")

    # 生成 Markdown 报告
    md = build_markdown(today, results)
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(md)
    print("📝 README.md 已更新")

    # 统计
    found    = sum(1 for r in results if r["found"] is True)
    not_found = sum(1 for r in results if r["found"] is False)
    errors    = sum(1 for r in results if r["found"] is None)
    print(f"\n📊 统计: 已收录 {found} | 未收录 {not_found} | 检测失败 {errors}")


def build_markdown(date: str, results: list) -> str:
    """生成 README.md 报告"""
    found     = [r for r in results if r["found"] is True]
    not_found = [r for r in results if r["found"] is False]
    errors     = [r for r in results if r["found"] is None]

    lines = [
        f"# 慧见 WISESIGHT 外链收录检测报告",
        "",
        f"> 自动检测日期: **{date}**  |  产品官网: [{PRODUCT_DOMAIN}](https://{PRODUCT_DOMAIN})",
        "",
        "## 📊 检测结果汇总",
        "",
        f"| 状态 | 数量 |",
        f"|------|------|",
        f"| ✅ 已收录 | **{len(found)}** |",
        f"| ❌ 未收录 | **{len(not_found)}** |",
        f"| ⚠️ 检测失败 | **{len(errors)}** |",
        f"| 合计 | **{len(results)}** |",
        "",
        "## ✅ 已收录平台",
        "",
    ]
    if found:
        for r in found:
            urls_str = "、".join(r.get("found_urls", [])[:2]) if r.get("found_urls") else "—"
            lines.append(f"- **{r['platform']}** — 找到 {r.get('count', '?')} 条结果")
            if urls_str != "—":
                lines.append(f"  收录链接: {urls_str}")
    else:
        lines.append("（暂无）")

    lines += ["", "## ❌ 未收录平台（需跟进）", ""]
    if not_found:
        for r in not_found:
            lines.append(f"- {r['platform']} ({r['platform_url']})")
    else:
        lines.append("（全部已收录！🎉）")

    if errors:
        lines += ["", "## ⚠️ 检测失败（需手动复核）", ""]
        for r in errors:
            err = r.get("error", "未知错误")
            lines.append(f"- {r['platform']}: {err}")

    lines += ["", "---", f"*由 GitHub Actions 自动生成，最后更新: {date}*", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
