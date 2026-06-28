import csv
import html
import json
import random
import re
import sys
import time
import warnings
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qs, unquote, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning


PRODUCT_KEYWORDS = {
    "手机": [
        "iPhone 17 续航",
        "iPhone 17 发热",
        "iPhone 17 Pro 拍照",
        "iPhone 17 Pro Max 信号",
        "iPhone 17 Air 手感",
        "iPhone 17 价格",
        "iPhone 17 信号",
        "iPhone 17 拍照",
    ],
    "手表": [
        "Apple Watch Series 11 健康功能",
        "Apple Watch Series 11 运动体验",
        "Apple Watch SE 3 续航",
        "Apple Watch SE 3 通讯功能",
        "Apple Watch 耐摔",
        "Apple Watch 睡眠监测",
        "Apple Watch 运动记录",
    ],
    "平板": [
        "iPad Air 11 英寸 体验",
        "iPad Pro 11 英寸 性能",
        "iPad Air 学习 办公",
        "iPad Pro 绘画 体验",
        "iPad 续航",
        "iPad 学生党",
        "iPad Pro 发热",
    ],
    "电脑": [
        "MacBook Air 续航",
        "MacBook Pro 性能",
        "MacBook Neo 体验",
        "MacBook Air 学生 购买建议",
        "MacBook Pro 剪辑 发热",
        "MacBook Air 轻薄",
        "MacBook Pro 价格",
    ],
}

CATEGORY_QUERY_TERMS = {
    "手机": ["iPhone", "iPhone 17", "iPhone battery", "iPhone camera", "iPhone price", "iPhone signal"],
    "手表": ["Apple Watch", "Apple Watch Series", "Apple Watch health", "Apple Watch workout", "Apple Watch battery"],
    "平板": ["iPad", "iPad Air", "iPad Pro", "iPad battery", "iPad drawing", "iPad student"],
    "电脑": ["MacBook", "MacBook Air", "MacBook Pro", "MacBook battery", "MacBook performance", "MacBook price"],
}

RSS_FEEDS = [
    ("IT之家", "https://www.ithome.com/rss/"),
    ("cnBeta", "https://www.cnbeta.com.tw/backend.php"),
    ("爱范儿", "https://www.ifanr.com/feed"),
    ("9to5Mac", "https://9to5mac.com/feed/"),
    ("MacRumors", "https://www.macrumors.com/macrumors.xml"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ("Engadget", "https://www.engadget.com/rss.xml"),
]

TARGET_TOTAL = 2000
CATEGORY_TARGET = TARGET_TOTAL // len(PRODUCT_KEYWORDS)
BATCH_SIZE = 100
REQUEST_INTERVAL_MIN = 2
REQUEST_INTERVAL_MAX = 5
TIMEOUT = 10
MAX_RESULTS_PER_KEYWORD = 100
MAX_RETRIES = 2

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
    "category",
    "platform",
    "keyword",
    "title",
    "content",
    "sentiment",
    "publish_time",
    "url",
    "crawl_time",
]

POSITIVE_WORDS = ["不错", "提升", "流畅", "满意", "优秀", "好用", "稳定", "清晰", "强", "舒服", "方便", "轻薄", "省电", "顺滑", "值得", "推荐"]
NEGATIVE_WORDS = ["发热", "续航差", "信号差", "贵", "卡顿", "不满意", "问题", "翻车", "差", "失望", "重", "掉电", "延迟", "闪退", "不值得"]

RELEVANT_TERMS = ["apple", "iphone", "ipad", "macbook", "apple watch", "苹果", "手表", "平板", "电脑"]
CATEGORY_TERMS = {
    "手机": ["iphone", "苹果手机"],
    "手表": ["apple watch", "watch", "苹果手表", "手表"],
    "平板": ["ipad", "平板"],
    "电脑": ["macbook", "mac", "笔记本", "电脑"],
}

KNOWN_PLATFORMS = {
    "ithome.com": "IT之家",
    "cnbeta.com.tw": "cnBeta",
    "ifanr.com": "爱范儿",
    "9to5mac.com": "9to5Mac",
    "macrumors.com": "MacRumors",
    "theverge.com": "The Verge",
    "engadget.com": "Engadget",
    "hn.algolia.com": "Hacker News",
}

CAPTCHA_MARKERS = [
    "captcha",
    "verify you are human",
    "unusual traffic",
    "too many requests",
    "访问过于频繁",
    "验证码",
    "人机验证",
    "安全验证",
]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

ROBOTS_CACHE = {}
BLOCKED_HOSTS = set()


def project_paths():
    project_root = Path(__file__).resolve().parents[1]
    data_dir = project_root / "data"
    pages_data_dir = project_root / "docs" / "data"
    return {
        "data_dir": data_dir,
        "pages_data_dir": pages_data_dir,
        "json": data_dir / "reviews.json",
        "csv": data_dir / "reviews.csv",
        "pages_json": pages_data_dir / "reviews.json",
    }


def clean_text(text):
    if not text:
        return ""
    decoded = html.unescape(str(text))
    if "<" in decoded and ">" in decoded:
        decoded = BeautifulSoup(decoded, "lxml").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", decoded).strip()


def random_sleep(multiplier=1.0):
    delay = random.uniform(REQUEST_INTERVAL_MIN, REQUEST_INTERVAL_MAX) * multiplier
    time.sleep(delay)


def robots_allowed(session, url):
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return True

    base_url = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = urljoin(base_url, "/robots.txt")

    if base_url not in ROBOTS_CACHE:
        parser = RobotFileParser()
        try:
            response = session.get(robots_url, headers=HEADERS, timeout=TIMEOUT)
            if response.status_code == 200:
                parser.parse(response.text.splitlines())
                ROBOTS_CACHE[base_url] = parser
            else:
                ROBOTS_CACHE[base_url] = None
                print(f"[robots] 无法确认 robots.txt，继续谨慎访问：{robots_url}，状态码：{response.status_code}")
        except requests.RequestException as error:
            ROBOTS_CACHE[base_url] = None
            print(f"[robots] 读取失败，继续谨慎访问：{robots_url}，错误：{error}")

    parser = ROBOTS_CACHE[base_url]
    if parser is None:
        return True

    allowed = parser.can_fetch(HEADERS["User-Agent"], url)
    if not allowed:
        print(f"[robots] robots.txt 不允许采集，跳过：{url}")
    return allowed


def looks_blocked(text):
    lower_text = text.lower()
    return any(marker in lower_text for marker in CAPTCHA_MARKERS)


def request_text(session, url, params=None, retries=MAX_RETRIES):
    full_url = requests.Request("GET", url, params=params).prepare().url
    hostname = urlparse(full_url).netloc.lower()

    if hostname in BLOCKED_HOSTS:
        raise RuntimeError(f"来源已被暂停访问：{hostname}")

    if not robots_allowed(session, full_url):
        BLOCKED_HOSTS.add(hostname)
        raise RuntimeError("robots.txt 不允许采集")

    last_error = None
    for attempt in range(retries + 1):
        try:
            print(f"[请求] {full_url}，重试：{attempt}/{retries}")
            response = session.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)

            if response.status_code in {403, 429}:
                BLOCKED_HOSTS.add(hostname)
                print(f"[限制] {hostname} 返回 {response.status_code}，暂停该来源访问")
                random_sleep(multiplier=4)
                raise RuntimeError(f"访问受限：HTTP {response.status_code}")

            response.raise_for_status()

            if not response.encoding or response.encoding.lower() == "iso-8859-1":
                response.encoding = response.apparent_encoding

            content_type = response.headers.get("Content-Type", "").lower()
            should_check_block_page = "text/html" in content_type

            if should_check_block_page and looks_blocked(response.text):
                BLOCKED_HOSTS.add(hostname)
                print(f"[限制] 疑似验证码或频率限制，暂停该来源访问：{hostname}")
                random_sleep(multiplier=4)
                raise RuntimeError("疑似验证码或频率限制页面")

            return response.text
        except (requests.Timeout, requests.ConnectionError) as error:
            last_error = error
            print(f"[重试] 网络异常：{error}")
            random_sleep(multiplier=2)
        except requests.RequestException as error:
            last_error = error
            print(f"[失败] 请求异常：{error}")
            break
        except RuntimeError as error:
            last_error = error
            break

    raise RuntimeError(f"请求失败：{last_error}")


def request_json(session, url, params=None):
    return json.loads(request_text(session, url, params=params))


def normalize_url(url):
    if not url:
        return ""

    parsed = urlparse(url)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        query = parse_qs(parsed.query)
        if query.get("uddg"):
            return unquote(query["uddg"][0])

    return url


def infer_platform(url):
    hostname = urlparse(url).netloc.lower().replace("www.", "")
    for domain, platform in KNOWN_PLATFORMS.items():
        if domain in hostname:
            return platform
    return hostname or "公开网页"


def classify_sentiment(text):
    positive_hits = sum(text.count(word) for word in POSITIVE_WORDS)
    negative_hits = sum(text.count(word) for word in NEGATIVE_WORDS)

    if negative_hits > positive_hits:
        return "负面"
    if positive_hits > negative_hits:
        return "正面"
    return "中性"


def is_relevant_result(category, title, content):
    text = f"{title} {content}".lower()
    return any(term in text for term in RELEVANT_TERMS) and any(term in text for term in CATEGORY_TERMS[category])


def parse_date(value):
    if not value:
        return "未知"

    value = clean_text(value)
    try:
        if value.endswith("Z"):
            return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        return parsedate_to_datetime(value).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        pass

    patterns = [
        r"20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}日?",
        r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}",
        r"\d{1,2}月\d{1,2}日",
    ]
    for pattern in patterns:
        match = re.search(pattern, value)
        if match:
            return (
                match.group(0)
                .replace("年", "-")
                .replace("月", "-")
                .replace("日", "")
                .replace("/", "-")
                .replace(".", "-")
            )
    return "未知"


def build_review(category, keyword, title, content, url, platform="", publish_time=""):
    title = clean_text(title)
    content = clean_text(content) or title
    url = normalize_url(url)
    merged_text = f"{title} {content}"

    return {
        "category": category,
        "platform": clean_text(platform) or infer_platform(url),
        "keyword": keyword,
        "title": title,
        "content": content,
        "sentiment": classify_sentiment(merged_text),
        "publish_time": parse_date(publish_time),
        "url": url,
        "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def record_key(review):
    url = clean_text(review.get("url", ""))
    if url:
        return f"url::{url}"
    return f"text::{clean_text(review.get('title', ''))}::{clean_text(review.get('content', ''))}"


def is_valid_review(review):
    if not review.get("title") or not review.get("content"):
        return False
    return is_relevant_result(review["category"], review["title"], review["content"])


def normalize_existing_review(review):
    normalized = {field: clean_text(review.get(field, "")) for field in FIELDNAMES}
    normalized["content"] = normalized["content"] or normalized["title"]
    normalized["publish_time"] = normalized["publish_time"] or "未知"
    return normalized


def load_existing_reviews(json_path):
    if not json_path.exists():
        return []

    try:
        with json_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        reviews = [normalize_existing_review(item) for item in data if isinstance(item, dict)]
        print(f"[断点] 已读取历史数据：{len(reviews)} 条")
        return reviews
    except (json.JSONDecodeError, OSError) as error:
        print(f"[断点] 读取历史数据失败，将从空数据开始：{error}")
        return []


def deduplicate_reviews(reviews):
    unique_reviews = []
    seen_keys = set()
    for review in reviews:
        key = record_key(review)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique_reviews.append(review)
    return unique_reviews


def save_reviews(reviews, paths, batch_id):
    paths["data_dir"].mkdir(parents=True, exist_ok=True)
    paths["pages_data_dir"].mkdir(parents=True, exist_ok=True)

    with paths["json"].open("w", encoding="utf-8") as file:
        json.dump(reviews, file, ensure_ascii=False, indent=2)

    with paths["pages_json"].open("w", encoding="utf-8") as file:
        json.dump(reviews, file, ensure_ascii=False, indent=2)

    with paths["csv"].open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(reviews)

    print(f"[保存] 批次 {batch_id}，当前总量 {len(reviews)}，JSON：{paths['json']}，CSV：{paths['csv']}")


def add_reviews(existing_reviews, new_reviews, seen_keys, target_total, category_counts):
    added = 0
    for review in new_reviews:
        if len(existing_reviews) >= target_total:
            break
        if category_counts.get(review["category"], 0) >= CATEGORY_TARGET:
            continue
        if not is_valid_review(review):
            continue
        key = record_key(review)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        existing_reviews.append(review)
        category_counts[review["category"]] = category_counts.get(review["category"], 0) + 1
        added += 1
    return added


def parse_rss_feed(xml_text, category, keyword, fallback_platform):
    soup = BeautifulSoup(xml_text, "xml")
    items = soup.find_all("item") or soup.find_all("entry")
    reviews = []

    for item in items:
        title_node = item.title
        content_node = item.description or item.summary or item.find("content:encoded") or item.content
        link_node = item.link
        date_node = item.pubDate or item.published or item.updated
        source_node = item.source

        if link_node and link_node.get("href"):
            url = link_node.get("href")
        else:
            url = link_node.get_text(" ", strip=True) if link_node else ""

        review = build_review(
            category=category,
            keyword=keyword,
            title=title_node.get_text(" ", strip=True) if title_node else "",
            content=content_node.get_text(" ", strip=True) if content_node else "",
            url=url,
            platform=source_node.get_text(" ", strip=True) if source_node else fallback_platform,
            publish_time=date_node.get_text(" ", strip=True) if date_node else "",
        )
        if is_valid_review(review):
            reviews.append(review)

    return reviews


def search_rss_feed(session, category, keyword, feed_name, feed_url):
    xml_text = request_text(session, feed_url)
    return parse_rss_feed(xml_text, category, keyword, feed_name)


def search_9to5mac(session, category, keyword, query, page):
    data = request_json(
        session,
        "https://9to5mac.com/wp-json/wp/v2/search",
        params={
            "search": query,
            "per_page": str(MAX_RESULTS_PER_KEYWORD),
            "page": str(page + 1),
        },
    )
    reviews = []

    for item in data:
        review = build_review(
            category=category,
            keyword=keyword,
            title=item.get("title", ""),
            content=item.get("title", ""),
            url=item.get("url", ""),
            platform="9to5Mac",
            publish_time="未知",
        )
        if is_valid_review(review):
            reviews.append(review)

    return reviews


def search_hacker_news(session, category, keyword, query, page):
    data = request_json(
        session,
        "https://hn.algolia.com/api/v1/search_by_date",
        params={
            "query": query,
            "tags": "story",
            "hitsPerPage": str(MAX_RESULTS_PER_KEYWORD),
            "page": str(page),
        },
    )
    reviews = []

    for item in data.get("hits", []):
        url = item.get("url") or f"https://news.ycombinator.com/item?id={item.get('objectID', '')}"
        title = item.get("title") or item.get("story_title") or ""
        review = build_review(
            category=category,
            keyword=keyword,
            title=title,
            content=title,
            url=url,
            platform="Hacker News",
            publish_time=item.get("created_at", ""),
        )
        if is_valid_review(review):
            reviews.append(review)

    return reviews


def query_variants(category, keyword):
    seen = set()
    candidates = [*CATEGORY_QUERY_TERMS[category], keyword]
    for query in candidates:
        normalized = query.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        yield query


def source_plan():
    return [
        ("9to5Mac Search", range(0, 5)),
        ("Hacker News Search", range(0, 5)),
        ("Public RSS", [None]),
    ]


def crawl_source(session, source_name, category, keyword, query, page):
    if source_name == "9to5Mac Search":
        return search_9to5mac(session, category, keyword, query, page or 0)
    if source_name == "Hacker News Search":
        return search_hacker_news(session, category, keyword, query, page or 0)
    if source_name == "Public RSS":
        all_reviews = []
        for feed_name, feed_url in RSS_FEEDS:
            try:
                all_reviews.extend(search_rss_feed(session, category, keyword, feed_name, feed_url))
            except Exception as error:
                print(f"[RSS失败] {feed_name}：{error}")
            random_sleep()
        return all_reviews
    raise ValueError(f"未知来源：{source_name}")


def print_progress(category, keyword, source_name, query, page, total_seen, dedup_total, batch_id, message):
    page_text = "RSS" if page is None else str(page + 1)
    print(
        f"[进度] 类别={category} | 关键词={keyword} | 来源={source_name} | "
        f"页码={page_text} | 查询={query} | 当前累计={total_seen} | "
        f"去重后={dedup_total} | 保存批次={batch_id} | {message}"
    )


def crawl_all(session, reviews, paths):
    seen_keys = {record_key(review) for review in reviews}
    existing_count = len(reviews)
    new_since_save = 0
    batch_id = 0
    total_seen = existing_count
    category_counts = {category: 0 for category in PRODUCT_KEYWORDS}

    for review in reviews:
        if review["category"] in category_counts:
            category_counts[review["category"]] += 1

    if existing_count >= TARGET_TOTAL:
        print(f"[完成] 历史数据已达到目标：{existing_count}/{TARGET_TOTAL}")
        return 0

    for category, keywords in PRODUCT_KEYWORDS.items():
        if category_counts[category] >= CATEGORY_TARGET:
            print(f"[跳过] {category} 已达到类别目标：{category_counts[category]}/{CATEGORY_TARGET}")
            continue

        for keyword in keywords:
            for query in query_variants(category, keyword):
                if len(reviews) >= TARGET_TOTAL:
                    return len(reviews) - existing_count
                if category_counts[category] >= CATEGORY_TARGET:
                    break

                for source_name, pages in source_plan():
                    for page in pages:
                        if len(reviews) >= TARGET_TOTAL:
                            return len(reviews) - existing_count
                        if category_counts[category] >= CATEGORY_TARGET:
                            break

                        if source_name == "Public RSS" and page is not None:
                            continue

                        try:
                            print_progress(category, keyword, source_name, query, page, total_seen, len(reviews), batch_id, "开始请求")
                            source_reviews = crawl_source(session, source_name, category, keyword, query, page)
                            total_seen += len(source_reviews)
                            added = add_reviews(reviews, source_reviews, seen_keys, TARGET_TOTAL, category_counts)
                            new_since_save += added
                            print_progress(category, keyword, source_name, query, page, total_seen, len(reviews), batch_id, f"新增 {added} 条")

                            if page == 0 and not source_reviews:
                                print_progress(category, keyword, source_name, query, page, total_seen, len(reviews), batch_id, "第一页无结果，停止该查询翻页")
                                break

                            if new_since_save >= BATCH_SIZE:
                                batch_id += 1
                                save_reviews(reviews, paths, batch_id)
                                new_since_save = 0
                        except Exception as error:
                            print_progress(category, keyword, source_name, query, page, total_seen, len(reviews), batch_id, f"失败原因：{error}")

                        random_sleep()

    return len(reviews) - existing_count


def print_summary(reviews, new_count, paths, elapsed):
    category_counts = {category: 0 for category in PRODUCT_KEYWORDS}
    sentiment_counts = {"正面": 0, "中性": 0, "负面": 0}

    for review in reviews:
        if review["category"] in category_counts:
            category_counts[review["category"]] += 1
        if review["sentiment"] in sentiment_counts:
            sentiment_counts[review["sentiment"]] += 1

    print("-" * 60)
    print(f"本次新增数量：{new_count}")
    print(f"总数据量：{len(reviews)}")
    print(f"手机数量：{category_counts['手机']}")
    print(f"手表数量：{category_counts['手表']}")
    print(f"平板数量：{category_counts['平板']}")
    print(f"电脑数量：{category_counts['电脑']}")
    print(f"正面/中性/负面数量：{sentiment_counts['正面']} / {sentiment_counts['中性']} / {sentiment_counts['负面']}")
    print(f"JSON 保存路径：{paths['json']}")
    print(f"CSV 保存路径：{paths['csv']}")
    print(f"总耗时：{elapsed:.2f} 秒")


def main():
    start_time = time.time()
    paths = project_paths()
    reviews = deduplicate_reviews(load_existing_reviews(paths["json"]))
    initial_count = len(reviews)
    new_count = 0

    try:
        with requests.Session() as session:
            new_count = crawl_all(session, reviews, paths)
    except KeyboardInterrupt:
        print("[中断] 收到手动中断，正在保存已采集数据")
    except Exception as error:
        print(f"[异常] 程序遇到异常，正在保存已采集数据：{error}")
    finally:
        new_count = len(reviews) - initial_count
        save_reviews(reviews, paths, batch_id="final")
        elapsed = time.time() - start_time
        print_summary(reviews, new_count, paths, elapsed)


if __name__ == "__main__":
    main()
