import csv
import json
import re
import sys
import time
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup


KEYWORDS = [
    "iPhone 17 续航",
    "iPhone 17 发热",
    "iPhone 17 Pro 拍照",
    "iPhone 17 Pro Max 信号",
    "iPhone 17 Air 手感",
]

REQUEST_INTERVAL = 2
TIMEOUT = 10
MAX_PER_KEYWORD = 10
MAX_TOTAL = 50

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

FIELDNAMES = [
    "platform",
    "keyword",
    "title",
    "content",
    "sentiment",
    "publish_time",
    "url",
    "crawl_time",
]

POSITIVE_WORDS = ["不错", "提升", "流畅", "满意", "优秀", "好用", "稳定", "清晰", "强", "舒服"]
NEGATIVE_WORDS = ["发热", "续航差", "信号差", "贵", "卡顿", "不满意", "问题", "翻车", "差", "失望"]

KNOWN_PLATFORMS = {
    "ithome.com": "IT之家",
    "smzdm.com": "什么值得买",
    "zhihu.com": "知乎",
    "bilibili.com": "B站",
    "weibo.com": "微博",
    "douyin.com": "抖音",
    "toutiao.com": "今日头条",
    "baijiahao.baidu.com": "百度百家号",
    "163.com": "网易",
    "qq.com": "腾讯网",
    "sohu.com": "搜狐",
    "sina.com.cn": "新浪",
    "cnbeta.com.tw": "cnBeta",
    "antutu.com": "安兔兔",
    "36kr.com": "36氪",
    "msn.com": "MSN",
}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def clean_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def request_text(session, url, params=None):
    response = session.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()

    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding

    return response.text


def sleep_between_requests():
    time.sleep(REQUEST_INTERVAL)


def normalize_url(url):
    if not url:
        return ""

    parsed = urlparse(url)

    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        query = parse_qs(parsed.query)
        if query.get("uddg"):
            return unquote(query["uddg"][0])

    if parsed.netloc.endswith("bing.com") and parsed.path.startswith("/news/apiclick.aspx"):
        query = parse_qs(parsed.query)
        if query.get("url"):
            return unquote(query["url"][0])

    return url


def infer_platform(url):
    hostname = urlparse(url).netloc.lower().replace("www.", "")

    for domain, platform in KNOWN_PLATFORMS.items():
        if domain in hostname:
            return platform

    return hostname or "公开网页"


def classify_sentiment(text):
    for word in NEGATIVE_WORDS:
        if word in text:
            return "负面"

    for word in POSITIVE_WORDS:
        if word in text:
            return "正面"

    return "中性"


def is_relevant_result(title, content):
    text = f"{title} {content}".lower()
    return "iphone" in text or "apple" in text or "苹果" in text


def extract_publish_time(text):
    patterns = [
        r"20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}日?",
        r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}",
        r"\d{1,2}月\d{1,2}日",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return (
                match.group(0)
                .replace("年", "-")
                .replace("月", "-")
                .replace("日", "")
                .replace("/", "-")
                .replace(".", "-")
            )

    return ""


def parse_rss_publish_time(pub_date):
    if not pub_date:
        return ""

    try:
        return parsedate_to_datetime(pub_date).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return extract_publish_time(pub_date)


def build_review(keyword, title, content, url, platform="", publish_time=""):
    title = clean_text(title)
    content = clean_text(content)
    url = normalize_url(url)
    merged_text = f"{title} {content}"

    return {
        "platform": clean_text(platform) or infer_platform(url),
        "keyword": keyword,
        "title": title,
        "content": content or title,
        "sentiment": classify_sentiment(merged_text),
        "publish_time": publish_time or extract_publish_time(merged_text),
        "url": url,
        "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def search_bing_news_rss(session, keyword):
    xml_text = request_text(
        session,
        "https://www.bing.com/news/search",
        params={
            "q": f"{keyword} 用户评价 体验",
            "format": "rss",
            "mkt": "zh-CN",
            "setlang": "zh-CN",
        },
    )
    soup = BeautifulSoup(xml_text, "xml")
    reviews = []

    for item in soup.find_all("item"):
        title = item.title.get_text(" ", strip=True) if item.title else ""
        description = item.description.get_text(" ", strip=True) if item.description else ""
        content = BeautifulSoup(description, "lxml").get_text(" ", strip=True)
        link = item.link.get_text(" ", strip=True) if item.link else ""
        source = item.find("News:Source")
        pub_date = item.pubDate.get_text(" ", strip=True) if item.pubDate else ""

        review = build_review(
            keyword=keyword,
            title=title,
            content=content,
            url=link,
            platform=source.get_text(" ", strip=True) if source else "",
            publish_time=parse_rss_publish_time(pub_date),
        )

        if review["title"] and review["url"] and is_relevant_result(review["title"], review["content"]):
            reviews.append(review)

    return reviews


def search_google_news_rss(session, keyword):
    xml_text = request_text(
        session,
        "https://news.google.com/rss/search",
        params={
            "q": f"{keyword} 用户评价 体验",
            "hl": "zh-CN",
            "gl": "CN",
            "ceid": "CN:zh-Hans",
        },
    )
    soup = BeautifulSoup(xml_text, "xml")
    reviews = []

    for item in soup.find_all("item"):
        title = item.title.get_text(" ", strip=True) if item.title else ""
        description = item.description.get_text(" ", strip=True) if item.description else ""
        content = BeautifulSoup(description, "lxml").get_text(" ", strip=True)
        link = item.link.get_text(" ", strip=True) if item.link else ""
        source = item.source
        pub_date = item.pubDate.get_text(" ", strip=True) if item.pubDate else ""

        review = build_review(
            keyword=keyword,
            title=title,
            content=content,
            url=link,
            platform=source.get_text(" ", strip=True) if source else "",
            publish_time=parse_rss_publish_time(pub_date),
        )

        if review["title"] and review["url"] and is_relevant_result(review["title"], review["content"]):
            reviews.append(review)

    return reviews


def search_bing_web(session, keyword):
    html = request_text(
        session,
        "https://www.bing.com/search",
        params={
            "q": f"{keyword} 用户评价 体验",
            "count": str(MAX_PER_KEYWORD),
            "mkt": "zh-CN",
            "setlang": "zh-CN",
        },
    )
    soup = BeautifulSoup(html, "lxml")
    reviews = []

    for item in soup.select("li.b_algo"):
        link = item.select_one("h2 a")
        snippet = item.select_one("p")

        if not link or not link.get("href"):
            continue

        review = build_review(
            keyword=keyword,
            title=link.get_text(" ", strip=True),
            content=snippet.get_text(" ", strip=True) if snippet else "",
            url=link["href"],
        )

        if review["title"] and review["url"] and is_relevant_result(review["title"], review["content"]):
            reviews.append(review)

    return reviews


def search_duckduckgo_html(session, keyword):
    html = request_text(
        session,
        "https://duckduckgo.com/html/",
        params={"q": f"{keyword} 用户评价 体验"},
    )
    soup = BeautifulSoup(html, "lxml")
    reviews = []

    for item in soup.select(".result"):
        link = item.select_one(".result__a")
        snippet = item.select_one(".result__snippet")

        if not link or not link.get("href"):
            continue

        review = build_review(
            keyword=keyword,
            title=link.get_text(" ", strip=True),
            content=snippet.get_text(" ", strip=True) if snippet else "",
            url=link["href"],
        )

        if review["title"] and review["url"] and is_relevant_result(review["title"], review["content"]):
            reviews.append(review)

    return reviews


def deduplicate_reviews(reviews):
    unique_reviews = []
    seen_urls = set()

    for review in reviews:
        url = review.get("url", "")
        if not url or url in seen_urls:
            continue

        seen_urls.add(url)
        unique_reviews.append(review)

    return unique_reviews


def crawl_keyword(session, keyword):
    searchers = [
        ("Bing News RSS", search_bing_news_rss),
        ("Google News RSS", search_google_news_rss),
        ("Bing Web", search_bing_web),
        ("DuckDuckGo HTML", search_duckduckgo_html),
    ]
    keyword_reviews = []

    for source_name, searcher in searchers:
        if len(keyword_reviews) >= MAX_PER_KEYWORD:
            break

        try:
            print(f"正在采集：{keyword}，来源：{source_name}")
            source_reviews = searcher(session, keyword)
            keyword_reviews.extend(source_reviews)
            keyword_reviews = deduplicate_reviews(keyword_reviews)[:MAX_PER_KEYWORD]
            print(f"来源完成：{source_name}，当前关键词累计 {len(keyword_reviews)} 条")
        except Exception as error:
            print(f"采集失败：{keyword}，来源：{source_name}，错误：{error}")

        sleep_between_requests()

    return keyword_reviews


def save_reviews(reviews):
    project_root = Path(__file__).resolve().parents[1]
    data_dir = project_root / "data"
    pages_data_dir = project_root / "docs" / "data"
    json_path = data_dir / "reviews.json"
    csv_path = data_dir / "reviews.csv"
    pages_json_path = pages_data_dir / "reviews.json"

    data_dir.mkdir(parents=True, exist_ok=True)
    pages_data_dir.mkdir(parents=True, exist_ok=True)

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(reviews, file, ensure_ascii=False, indent=2)

    with pages_json_path.open("w", encoding="utf-8") as file:
        json.dump(reviews, file, ensure_ascii=False, indent=2)

    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(reviews)

    return json_path, csv_path


def main():
    start_time = time.time()
    all_reviews = []

    with requests.Session() as session:
        for keyword in KEYWORDS:
            if len(all_reviews) >= MAX_TOTAL:
                break

            all_reviews.extend(crawl_keyword(session, keyword))
            all_reviews = deduplicate_reviews(all_reviews)[:MAX_TOTAL]

    json_path, csv_path = save_reviews(all_reviews)
    elapsed = time.time() - start_time

    print("-" * 48)
    print(f"总采集数量：{len(all_reviews)}")
    print(f"总耗时：{elapsed:.2f} 秒")
    print(f"JSON 保存路径：{json_path}")
    print(f"CSV 保存路径：{csv_path}")


if __name__ == "__main__":
    main()
