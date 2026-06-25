# 慧见 WISESIGHT 外链收录自动检测

每天自动检测各平台是否收录了慧见的产品页面，结果自动推送到本仓库。

## 📊 最新检测结果

查看 [README.md](./README.md) 获取最新检测报告。

历史检测结果在 `results/` 目录下，按日期命名：`results/YYYY-MM-DD.json`。

## 🔧 配置

### 使用 Google Custom Search API（推荐，更准确）

在 GitHub 仓库 Settings → Secrets and variables → Actions 里添加：

- `GOOGLE_API_KEY` — [申请地址](https://console.cloud.google.com/apis/credentials)
- `GOOGLE_CSE_ID` — [创建自定义搜索引擎](https://programmablesearchengine.google.com/)

免费额度：100 次/天，足够检测 ~20 个平台。

### 不使用 API（默认 DuckDuckGo）

无需配置，直接使用 DuckDuckGo 搜索检测（免费，但准确性略低）。

## 📅 自动运行时间

- **每天 UTC 01:00**（北京时间 09:00）
- 也可在 Actions 页面手动触发（Run workflow）

## 📦 本地运行

```bash
pip install -r requirements.txt
python check_index.py
```
