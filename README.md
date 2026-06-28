# 基于 Python 爬虫的苹果全系列产品口碑采集与可视化分析平台

本项目是一个面向 GitHub Pages 的静态展示平台，用于演示苹果多产品线公开网页数据的采集、整理、情感分类与可视化分析流程。当前版本覆盖 iPhone、Apple Watch、iPad 与 MacBook 四类产品，采集公开页面中的标题、摘要、链接和发布时间等信息，不访问需要登录的网站，也不采集个人隐私信息。

## 在线访问地址

GitHub Pages 部署后可通过仓库 Pages 地址访问：

```text
https://caspian-kf.github.io/iphone-review-analysis/
```

## 功能模块

- 首页仪表盘：展示总数据量、各产品类别数据量、情感数量、平台数量和最近采集时间。
- 数据列表：展示采集数据，支持按产品类别、平台、情感和关键词筛选。
- 分析图表：使用 ECharts 展示情感占比、产品类别分布、平台分布、关键词分布和各产品类别情感对比。
- 数据采集：使用 Python `requests + BeautifulSoup` 采集公开 RSS/搜索结果中的结构化信息。

## 覆盖产品范围

- 手机：iPhone 系列手机
- 手表：Apple Watch 系列手表
- 平板：iPad 系列平板
- 电脑：MacBook 系列笔记本电脑

## 技术栈

- Python
- requests
- BeautifulSoup4
- HTML5
- CSS3
- JavaScript
- ECharts
- GitHub Pages

## 项目目录结构

```text
iphone-review-analysis/
├── README.md
├── requirements.txt
├── .gitignore
├── crawler/
│   └── run.py
├── data/
│   ├── reviews.json
│   └── reviews.csv
└── docs/
    ├── index.html
    ├── data.html
    ├── analysis.html
    ├── css/
    │   └── style.css
    └── js/
        └── main.js
```

## 本地运行方式

安装依赖：

```bash
pip install -r requirements.txt
```

运行采集脚本：

```bash
python crawler/run.py
```

启动本地静态服务：

```bash
python -m http.server 8000
```

访问页面：

```text
http://localhost:8000/docs/index.html
```

## 数据采集流程

1. 在 `crawler/run.py` 中按产品类别维护关键词。
2. 通过公开 RSS/搜索结果页获取标题、摘要、链接和发布时间。
3. 使用简单关键词规则判断情感分类。
4. 将结果保存到 `data/reviews.json` 和 `data/reviews.csv`。
5. 前端页面通过 `../data/reviews.json` 读取数据并渲染表格与图表。

## GitHub Pages 部署方式

1. 将代码推送到 GitHub 仓库。
2. 打开仓库的 `Settings`。
3. 进入 `Pages` 设置。
4. 在 `Build and deployment` 中选择 `Deploy from a branch`。
5. 分支选择 `main`，目录选择 `/docs`。
6. 保存后等待 GitHub Pages 自动部署。

## 后续优化方向

- 引入更稳定的数据源配置和采集日志。
- 增加数据去重、清洗和异常摘要过滤。
- 使用更精细的中文情感分析模型。
- 增加时间趋势、平台趋势、产品型号对比等图表。
- 支持按日期范围、产品型号和平台组合筛选。
- 通过 GitHub Actions 定时更新公开数据。

## 免责声明

本项目仅用于学习与研究，采集公开页面信息，不用于商业用途；不采集隐私信息，不绕过登录、验证码或反爬机制。实际使用时请遵守目标网站的 robots 协议、用户协议和相关法律法规。
