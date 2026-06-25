#!/usr/bin/env python3
"""
慧见 WISESIGHT 外链收录自动检测
每天运行，检测各平台是否收录了慧见的产品页面
结果写入 results/YYYY-MM-DD.json 和 README.md

检测方法（按优先级）：
1. Bing HTML 搜索（免费，无需 Key，准确率高）
2. DuckDuckGo HTML 搜索（免费，无需 Key，备用）
3. Google Custom Search API（需配置 Secrets，最准确）
"""

import json
import os
import time
import random
import re
import datetime
import urllib.parse
from pathlib import Path

# ── 配置 ──────────────────────────────────────────
PRODUCT_NAME   = "慧见 WISESIGHT"
PRODUCT_DOMAIN = "wisesme.cn"

# 选择检测方法："bing"（推荐，无需 Key）| "duckduckgo" | "google_custom"
SEARCH_ENGINE = os.environ.get("SEARCH_ENGINE", "bing")

# Google Custom Search API（可选）
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID", "")

# 平台列表
PLATFORMS = [
    {"name": "There's An AI For That", "url": "https://theresanaiforthat.com",   "cat": "AI"},
    {"name": "Futurepedia",             "url": "https://www.futurepedia.io",     "cat": "AI"},
    {"name": "ListMyAI",               "url": "https://listmyai.net",            "cat": "AI"},
    {"name": "Uneed",                   "url": "https://www.uneed.best",         "cat": "AI"},
    {"name": "AI Tools Directory",       "url": "https://www.aitoolsdirectory.com","cat": "AI"},
    {"name": "Supertools",              "url": "https://supertools.ai",           "cat": "AI"},
    {"name": "All Things AI",           "url": "https://allthingsai.com",        "cat": "AI"},
    {"name": "GPTs Hunter",             "url": "https://www.gptshunter.com",     "cat": "AI"},
    {"name": "AIGC Open",              "url": "https://www.aigc.cn",            "cat": "AI"},
    {"name": "AITOP100",                "url": "https://www.aitop100.cn",        "cat": "中文AI"},
    {"name": "AI工具集",    "url": "https://ai-bot.cn/tools",     "cat": "中文AI"},
    {"name": "Toolify中文版", "url": "https://www.toolify.ai/zh",  "cat": "中文AI"},
    {"name": "办公人导航",   "url": "https://www.bgrdh.com",       "cat": "中文AI"},
    {"name": "AIBase",      "url": "https://www.aibase.com",       "cat": "中文AI"},
    {"name": "Product Hunt",  "url": "https://www.producthunt.com", "cat": "Startup"},
    {"name": "G2",           "url": "https://www.g2.com",           "cat": "SaaS"},
    {"name": "AlternativeTo", "url": "https://alternativeto.net",     "cat": "Tool"},
    {"name": "SourceForge",  "url": "https://sourceforge.net",       "cat": "Developer"},
    {"name": "Capterra",     "url": "https://www.capterra.com",     "cat": "SaaS"},
    {"name": "知乎专栏", "url": "https://www.zhihu.com", "cat": "内容",
     "article_url": "https://www.zhihu.com/answer/2053180865660850816"},
]


# ── 检测核心 ────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def _get(domain: str, path: str, headers: dict = None, timeout: int = 15) -> "requests.Response | None":
    """带重试的 GET 请求"""
    import requests
    for attempt in range(3):
        try:
            h = {"User-Agent": random.choice(USER_AGENTS)}
            if headers:
                h.update(headers)
            resp = requests.get(f"https://{domain}{path}", headers=h, timeout=timeout)
            return resp
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                raise e
    return None


def check_bing(platform_url: str) -> dict:
    """用 Bing 搜索检测（免费，无需 API Key，准确率高）"""
    domain = urllib.parse.urlparse(platform_url).netloc or platform_url.replace("https://", "").replace("http://", "").rstrip("/")
    query = f"site:{domain} {PRODUCT_NAME}"
    path = f"/search?q={urllib.parse.quote(query)}&count=5"

    try:
        resp = _get("www.bing.com", path)
        if resp is None:
            return {"method": "bing", "error": "ALL_RETRIES_FAILED", "found": None}
        resp.raise_for_status()
        html = resp.text

        # 判断：搜索结果里是否出现了产品域名
        found = PRODUCT_DOMAIN in html

        # 提取结果链接
        urls = re.findall(r'<li class="b_algo[^"]*"[^>]*>.*?<a href="([^"]+)"', html, re.DOTALL)
        # 备用提取
        if not urls:
            urls = re.findall(r'<a href="(https?://[^"]+)"[^>]*class="[^"]*tilk[^"]*"', html)

        return {"method": "bing", "found": found, "count": len(urls), "urls": urls[:3]}
    except Exception as e:
        return {"method": "bing", "error": str(e), "found": None}


def check_duckduckgo(platform_url: str) -> dict:
    """用 DuckDuckGo HTML 搜索检测"""
    domain = urllib.parse.urlparse(platform_url).netloc or platform_url.replace("https://", "").replace("http://", "").rstrip("/")
    query = f"site:{domain} {PRODUCT_NAME}"
    path = f"/html/?q={urllib.parse.quote(query)}"

    try:
        resp = _get("html.duckduckgo.com", path)
        if resp is None:
            return {"method": "duckduckgo", "error": "ALL_RETRIES_FAILED", "found": None}
        resp.raise_for_status()
        html = resp.text
        found = PRODUCT_DOMAIN in html
        urls = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"', html)
        return {"method": "duckduckgo", "found": found, "count": len(urls), "urls": urls[:3]}
    except Exception as e:
        return {"method": "duckduckgo", "error": str(e), "found": None}


def check_google_custom(platform_url: str) -> dict:
    """用 Google Custom Search API 检测（需 API key）"""
    import requests
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        return {"method": "google_custom", "error": "NO_API_KEY", "found": None}
    domain = urllib.parse.urlparse(platform_url).netloc or platform_url.replace("https://", "").replace("http://", "").rstrip("/")
    query = f"site:{domain} {PRODUCT_NAME}"
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


def detect_method() -> str:
    """自动选择检测方法"""
    if GOOGLE_API_KEY and GOOGLE_CSE_ID:
        return "google_custom"
    return SEARCH_ENGINE  # 默认 "bing"


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

    method = detect_method()

    if method == "google_custom":
        r = check_google_custom(p["url"])
    elif method == "duckduckgo":
        r = check_duckduckgo(p["url"])
    else:  # bing
        r = check_bing(p["url"])
        # Bing 失败时自动降级到 DuckDuckGo
        if r.get("error") and not r.get("found"):
            r2 = check_duckduckgo(p["url"])
            if not r2.get("error"):
                r = {**r2, "method": "bing→duckduckgo (fallback)"}

    result["method"]     = r["method"]
    result["found"]      = r["found"]
    result["count"]      = r.get("count")
    result["found_urls"] = r.get("urls", [])
    if "error" in r:
        result["error"] = r["error"]

    return result


# ── 主流程 ────────────────────────────────────────
def main():
    today  = datetime.date.today().isoformat()
    method = detect_method()
    print(f"🔍 开始检测 {today} | 产品: {PRODUCT_NAME} | 方法: {method}")

    results = []
    for i, p in enumerate(PLATFORMS):
        print(f"  [{i+1}/{len(PLATFORMS)}] {p['name']} ... ", end="", flush=True)
        r = check_platform(p)
        if r["found"] is True:
            status = "✅ 已收录"
        elif r["found"] is False:
            status = "❌ 未收录"
        else:
            status = f"⚠️ 检测失败: {r.get('error', '未知')[:50]}"
        print(status)
        results.append(r)
        if i < len(PLATFORMS) - 1:
            time.sleep(random.uniform(3, 7))

    # 保存 JSON
    out_file = Path("results") / f"{today}.json"
    out_file.parent.mkdir(exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"date": today, "product": PRODUCT_NAME, "method": method, "results": results},
                  f, ensure_ascii=False, indent=2)
    print(f"\n📦 JSON 结果已保存: {out_file}")

    # 生成 Markdown 报告
    md = build_markdown(today, results, method)
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(md)
    print("📝 README.md 已更新")

    # 统计
    found     = sum(1 for r in results if r["found"] is True)
    not_found = sum(1 for r in results if r["found"] is False)
    errors     = sum(1 for r in results if r["found"] is None)
    print(f"\n📊 统计: 已收录 {found} | 未收录 {not_found} | 检测失败 {errors}")


def build_markdown(date: str, results: list, method: str) -> str:
    found     = [r for r in results if r["found"] is True]
    not_found = [r for r in results if r["found"] is False]
    errors     = [r for r in results if r["found"] is None]

    lines = [
        f"# 慧见 WISESIGHT 外链收录检测报告",
        "",
        f"> 自动检测日期: **{date}**  |  检测方法: **{method}**  |  产品官网: [{PRODUCT_DOMAIN}](https://{PRODUCT_DOMAIN})",
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
            lines.append(f"- **{r['platform']}** — 找到 {r.get('count', '?')} 条结果  ")
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
            lines.append(f"- {r['platform']}: `{err[:80]}`")

    lines += ["", "---", f"*由 GitHub Actions 自动生成，最后更新: {date} | 方法: {method}*", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
