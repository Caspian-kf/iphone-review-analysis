# iPhone Review Analysis

手机产品口碑分析与可视化平台是一个基于 Python 爬虫思路的静态展示项目，用于演示手机产品评论数据的采集、整理、情感分类和可视化分析流程。当前版本不连接真实网站，不使用后端框架和数据库，仅通过模拟数据展示第一版 GitHub Pages 页面效果。

## 功能模块

- 首页仪表盘：展示总评论数、正面评价、中性评价、负面评价、平台数量和最近采集时间。
- 数据列表：从 `data/reviews.json` 读取评论数据，并支持关键词搜索、情感分类筛选和平台筛选。
- 分析图表：使用 ECharts 展示情感占比、平台评论数量和关键词数量统计。
- 示例爬虫脚本：通过 `crawler/run.py` 生成 JSON 和 CSV 示例数据。

## 技术栈

- Python
- Pandas
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
│   └── reviews.json
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

生成示例数据：

```bash
python crawler/run.py
```

启动本地静态服务后访问 `docs/index.html`。例如在项目根目录运行：

```bash
python -m http.server 8000
```

然后打开：

```text
http://localhost:8000/docs/index.html
```

## GitHub Pages 部署方式

1. 将代码推送到 GitHub 仓库。
2. 打开仓库的 `Settings`。
3. 进入 `Pages` 设置。
4. 在 `Build and deployment` 中选择 `Deploy from a branch`。
5. 分支选择 `main`，目录选择 `/docs`。
6. 保存后等待 GitHub Pages 自动部署。

部署完成后即可访问 GitHub Pages 提供的网址。

## 后续优化方向

- 接入真实公开页面采集逻辑，增加请求限速和异常处理。
- 增加数据清洗、去重和关键词提取能力。
- 引入更完善的中文情感分析模型。
- 增加品牌、机型、价格区间等更多维度的筛选。
- 增加词云、时间趋势图和评论详情页。
- 增加自动化数据更新流程。

## 免责声明

本项目仅用于学习与研究，采集公开页面信息，不用于商业用途。实际采集时请遵守目标网站的 robots 协议、用户协议和相关法律法规。
