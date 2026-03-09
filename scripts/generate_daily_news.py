#!/usr/bin/env python3
import json
import os
import re
import html
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import List, Dict, Any, Tuple

PROJECT_DIR = "/Users/marcus/projects/pageDalliy"
TMP_DIR = os.path.join(PROJECT_DIR, "tmp")
RSS_DIR = os.path.join(TMP_DIR, "rss")
LOG_DIR = os.path.join(PROJECT_DIR, "logs")
OUT_DIR = os.path.join(PROJECT_DIR, "output")
RES_DIR = os.path.join(PROJECT_DIR, "res")

RAW_FILE = os.path.join(TMP_DIR, "raw_news.json")
TRANS_FILE = os.path.join(TMP_DIR, "translated_news.json")
EDIT_FILE = os.path.join(TMP_DIR, "edited_news.json")
OUT_HTML = os.path.join(OUT_DIR, "index.html")

RUN_TAG = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
PIPE_LOG = os.path.join(LOG_DIR, f"pipeline_{RUN_TAG}.log")
RETRY_LOG = os.path.join(LOG_DIR, f"retry_{RUN_TAG}.json")

CATEGORY_ORDER = ["国际", "时政", "军事", "科技", "财经", "商业", "健康", "科学", "中国", "体育", "文化", "娱乐"]
TAB_CONFIG: List[Dict[str, str]] = [
    {"id": "top10", "tab": "综合热点", "title": "每日热点", "subtitle": "全平台综合热度Top10"},
    {"id": "world", "tab": "国际", "title": "国际新闻", "subtitle": "来自全球各地的重要新闻"},
    {"id": "politics", "tab": "时政", "title": "时政", "subtitle": "政策与政治动态"},
    {"id": "military", "tab": "军事", "title": "军事", "subtitle": "全球军事动态与国防新闻"},
    {"id": "tech", "tab": "科技", "title": "科技", "subtitle": "科技创新与产业动态"},
    {"id": "finance", "tab": "财经", "title": "财经", "subtitle": "金融市场、货币与宏观经济"},
    {"id": "business", "tab": "商业", "title": "商业", "subtitle": "公司、产业与商业趋势"},
    {"id": "health", "tab": "健康", "title": "健康", "subtitle": "公共卫生与医学动态"},
    {"id": "science", "tab": "科学", "title": "科学", "subtitle": "科研前沿与科学进展"},
    {"id": "china", "tab": "中国", "title": "中国", "subtitle": "中国相关新闻"},
    {"id": "sports", "tab": "体育", "title": "体育", "subtitle": "体育赛事与产业动态"},
    {"id": "culture", "tab": "文化", "title": "文化", "subtitle": "文化艺术与社会生活"},
    {"id": "entertainment", "tab": "娱乐", "title": "娱乐", "subtitle": "影视文娱与名人动态"},
]
TAB_CATEGORY_MAP: Dict[str, List[str]] = {
    "world": ["国际"],
    "politics": ["时政"],
    "military": ["军事"],
    "tech": ["科技"],
    "finance": ["财经"],
    "business": ["商业"],
    "health": ["健康"],
    "science": ["科学"],
    "china": ["中国"],
    "sports": ["体育"],
    "culture": ["文化"],
    "entertainment": ["娱乐"],
}
HEAT_WEIGHT = {"recency": 0.35, "keyword": 0.25, "source": 0.20, "coverage": 0.12, "category": 0.08}
SOURCE_WEIGHT = {
    "路透社": 0.95,
    "Reuters": 0.95,
    "纽约时报": 0.94,
    "BBC": 0.93,
    "卫报": 0.90,
    "华尔街日报": 0.92,
    "金融时报": 0.91,
    "CNN": 0.89,
    "Al Jazeera": 0.88,
    "半岛电视台": 0.88,
    "新华社": 0.84,
    "新华网": 0.84,
    "The Verge": 0.86,
    "TechCrunch": 0.86,
    "Wired": 0.86,
    "Ars": 0.87,
    "Nature": 0.90,
    "Science": 0.90,
    "ESPN": 0.85,
}
CATEGORY_WEIGHT = {
    "国际": 0.95,
    "时政": 0.94,
    "军事": 0.93,
    "科技": 0.89,
    "财经": 0.88,
    "商业": 0.86,
    "健康": 0.86,
    "科学": 0.84,
    "中国": 0.82,
    "体育": 0.78,
    "文化": 0.72,
    "娱乐": 0.70,
}
HOT_KEYWORDS: Dict[str, float] = {
    "war": 0.90,
    "conflict": 0.70,
    "attack": 0.80,
    "election": 0.70,
    "market": 0.65,
    "inflation": 0.70,
    "recession": 0.80,
    "oil": 0.60,
    "ai": 0.70,
    "chip": 0.60,
    "vaccine": 0.75,
    "pandemic": 0.90,
    "earthquake": 0.90,
    "战争": 0.90,
    "冲突": 0.70,
    "袭击": 0.80,
    "选举": 0.70,
    "市场": 0.65,
    "通胀": 0.70,
    "经济衰退": 0.80,
    "油价": 0.60,
    "人工智能": 0.70,
    "芯片": 0.60,
    "疫苗": 0.75,
    "疫情": 0.90,
    "地震": 0.90,
}
KEYWORD_CATEGORY_HINTS: List[Tuple[str, str]] = [
    ("军事", r"(军|导弹|防务|国防|nato|missile|army|defense)"),
    ("体育", r"(体育|比赛|联赛|奥运|冠军|nba|fifa|football|soccer|tennis)"),
    ("财经", r"(财经|汇率|股市|债券|货币|通胀|利率|央行|market|stock|bond|currency|inflation|gdp|fed)"),
    ("娱乐", r"(娱乐|电影|明星|剧集|票房|music|movie|celebrity|tv show)"),
    ("文化", r"(文化|艺术|展览|博物馆|文学|heritage|culture|art|museum)"),
    ("健康", r"(健康|医疗|医院|疾病|病毒|vaccine|health|medical|covid|flu)"),
    ("科学", r"(科学|研究|实验|论文|science|study|research|nature)"),
    ("科技", r"(科技|技术|ai|openai|chip|software|hardware|apple|google|meta)"),
    ("时政", r"(时政|政府|总统|议会|立法|外交|election|parliament|policy|minister)"),
    ("中国", r"(中国|北京|上海|国务院|人大|中国队|china|beijing)"),
]

WEEKDAY_ZH = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(PIPE_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def ensure_dirs() -> None:
    for d in [TMP_DIR, RSS_DIR, LOG_DIR, OUT_DIR]:
        os.makedirs(d, exist_ok=True)


def strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def first_text(elem: ET.Element, tags: List[str]) -> str:
    for tag in tags:
        node = elem.find(tag)
        if node is not None and node.text:
            return node.text.strip()
    return ""


def parse_time(item: ET.Element) -> datetime:
    for tag in ["pubDate", "{http://purl.org/dc/elements/1.1/}date", "updated", "published"]:
        node = item.find(tag)
        if node is not None and node.text:
            t = node.text.strip()
            try:
                if tag == "pubDate":
                    return parsedate_to_datetime(t).replace(tzinfo=None)
                return datetime.fromisoformat(t.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                continue
    return datetime.now()


def parse_published_at(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.now()


def source_weight(source: str) -> float:
    for key, score in SOURCE_WEIGHT.items():
        if key.lower() in source.lower():
            return score
    return 0.75


def sort_sources_for_display(sources: List[str]) -> List[str]:
    return sorted(sources, key=lambda s: source_weight(s), reverse=True)


def normalize_topic_key(title: str) -> str:
    # 去掉大部分符号后保留主要语义片段，作为同题覆盖度统计键
    key = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "", title.lower())
    return key[:32]


def infer_category(raw_category: str, source: str, title: str, summary: str) -> str:
    text = f"{source} {title} {summary}".lower()
    for cat, pattern in KEYWORD_CATEGORY_HINTS:
        if re.search(pattern, text):
            return cat
    if raw_category in CATEGORY_ORDER:
        return raw_category
    return "国际"


def recency_score(published_at: str) -> float:
    dt = parse_published_at(published_at)
    hours = max((datetime.now() - dt).total_seconds() / 3600.0, 0.0)
    if hours <= 6:
        return 1.0
    if hours <= 24:
        return 0.86
    if hours <= 48:
        return 0.72
    if hours <= 72:
        return 0.58
    return 0.35


def fetch_url(url: str, timeout: int = 8) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36"
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        encoding = resp.headers.get_content_charset() or "utf-8"
        return data.decode(encoding, errors="ignore")


def fetch_with_retry(url: str, retries: int = 1) -> str:
    fail_reasons = []
    for i in range(retries + 1):
        try:
            return fetch_url(url)
        except Exception as e:
            reason = f"attempt={i+1}, error={type(e).__name__}: {e}"
            fail_reasons.append(reason)
            log(f"fetch failed: {url} | {reason}")
            if i < retries:
                time.sleep(1.2)
    raise RuntimeError("; ".join(fail_reasons))


def collect_rss() -> Dict[str, Any]:
    with open(os.path.join(RES_DIR, "rss_list.json"), "r", encoding="utf-8") as f:
        feeds = json.load(f).get("rss", [])

    all_items: List[Dict[str, Any]] = []
    retry_records = []

    max_total_items = 180
    for idx, feed in enumerate(feeds, start=1):
        title = feed.get("title", "")
        url = feed.get("url", "")
        cat = feed.get("category", "国际")
        try:
            xml_text = fetch_with_retry(url, retries=1)
        except Exception as e:
            retry_records.append({"feed": title, "url": url, "reason": str(e)})
            continue

        safe_name = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff_-]", "_", title)[:80]
        with open(os.path.join(RSS_DIR, f"{idx:02d}_{safe_name}.xml"), "w", encoding="utf-8") as xf:
            xf.write(xml_text)

        try:
            root = ET.fromstring(xml_text)
        except Exception as e:
            retry_records.append({"feed": title, "url": url, "reason": f"xml parse: {e}"})
            continue

        candidates = root.findall(".//item")
        if not candidates:
            candidates = root.findall(".//{http://www.w3.org/2005/Atom}entry")

        picked = 0
        for item in candidates:
            title_txt = first_text(item, ["title", "{http://www.w3.org/2005/Atom}title"])
            if not title_txt:
                continue
            link_txt = first_text(item, ["link", "{http://www.w3.org/2005/Atom}link"])
            if not link_txt:
                lnode = item.find("{http://www.w3.org/2005/Atom}link")
                if lnode is not None:
                    link_txt = lnode.attrib.get("href", "")
            desc_txt = first_text(item, ["description", "summary", "{http://www.w3.org/2005/Atom}summary"]) or title_txt
            desc_txt = strip_html(desc_txt)
            pub_dt = parse_time(item)
            all_items.append(
                {
                    "source": title,
                    "source_url": url,
                    "category": cat if cat in CATEGORY_ORDER else "国际",
                    "title": strip_html(title_txt),
                    "summary": desc_txt[:360],
                    "url": link_txt,
                    "published_at": pub_dt.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
            picked += 1
            if picked >= 4:
                break
        if len(all_items) >= max_total_items:
            break

    all_items.sort(key=lambda x: x.get("published_at", ""), reverse=True)

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(all_items),
        "items": all_items,
    }
    with open(RAW_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    with open(RETRY_LOG, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "retry_count": len(retry_records),
                "records": retry_records,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    log(f"collected items={len(all_items)}, failed_feeds={len(retry_records)}")
    return payload


def translate_text_to_zh(text: str) -> str:
    if not text:
        return ""
    if re.search(r"[\u4e00-\u9fff]", text):
        return text

    q = urllib.parse.quote(text[:480])
    url = (
        "https://translate.googleapis.com/translate_a/single"
        f"?client=gtx&sl=auto&tl=zh-CN&dt=t&q={q}"
    )
    try:
        raw = fetch_with_retry(url, retries=1)
        data = json.loads(raw)
        segs = data[0] if isinstance(data, list) and data else []
        zh = "".join(seg[0] for seg in segs if seg and seg[0])
        return zh.strip() or text
    except Exception:
        # 回退：保留原文并标注
        return f"{text}（原文）"


def translate_news(raw_payload: Dict[str, Any]) -> Dict[str, Any]:
    out_items = []
    max_translate_items = 150
    for it in raw_payload.get("items", [])[:max_translate_items]:
        title_zh = translate_text_to_zh(it.get("title", ""))
        summary_zh = translate_text_to_zh(it.get("summary", ""))
        out_items.append(
            {
                **it,
                "title_zh": title_zh,
                "summary_zh": summary_zh,
            }
        )

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(out_items),
        "items": out_items,
    }
    with open(TRANS_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    log(f"translated items={len(out_items)}")
    return payload


def score_item(it: Dict[str, Any], topic_counts: Dict[str, int]) -> Tuple[float, Dict[str, float]]:
    title = it.get("title_zh", it.get("title", ""))
    summary = it.get("summary_zh", it.get("summary", ""))
    txt = f"{title} {summary}".lower()
    category = it.get("category", "国际")
    source = it.get("source", "")

    keyword_raw = 0.0
    for kw, score in HOT_KEYWORDS.items():
        if kw in txt:
            keyword_raw += score
    keyword_norm = min(keyword_raw / 3.0, 1.0)

    topic_key = normalize_topic_key(title)
    topic_coverage = min(topic_counts.get(topic_key, 1), 4) / 4.0
    source_norm = source_weight(source)
    category_norm = CATEGORY_WEIGHT.get(category, 0.75)
    recency_norm = recency_score(it.get("published_at", ""))

    final_norm = (
        HEAT_WEIGHT["recency"] * recency_norm
        + HEAT_WEIGHT["keyword"] * keyword_norm
        + HEAT_WEIGHT["source"] * source_norm
        + HEAT_WEIGHT["coverage"] * topic_coverage
        + HEAT_WEIGHT["category"] * category_norm
    )
    final_score = max(0.0, min(round(final_norm * 10, 1), 9.9))
    detail = {
        "recency": round(recency_norm, 3),
        "keyword": round(keyword_norm, 3),
        "source": round(source_norm, 3),
        "coverage": round(topic_coverage, 3),
        "category": round(category_norm, 3),
    }
    return final_score, detail


def edit_news(trans_payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized_items = []
    topic_counts: Dict[str, int] = {}
    topic_sources: Dict[str, set] = {}
    for it in trans_payload.get("items", []):
        title_zh = it.get("title_zh", it.get("title", ""))[:90]
        summary_zh = it.get("summary_zh", it.get("summary", ""))[:180]
        category = infer_category(it.get("category", "国际"), it.get("source", ""), title_zh, summary_zh)
        topic_key = normalize_topic_key(title_zh)
        topic_counts[topic_key] = topic_counts.get(topic_key, 0) + 1
        topic_sources.setdefault(topic_key, set()).add(it.get("source", "未知信源"))
        normalized_items.append(
            {
                **it,
                "category": category,
                "title_zh": title_zh,
                "summary_zh": summary_zh,
                "topic_key": topic_key,
            }
        )

    items = []
    for it in normalized_items:
        score, detail = score_item(it, topic_counts)
        topic_key = it.get("topic_key", "")
        ver_sources = sort_sources_for_display(list(topic_sources.get(topic_key, set())))
        if len(ver_sources) >= 2:
            verif = "✅ 多源验证"
        else:
            verif = "⚠️ 单一信源"
        items.append(
            {
                "heat_score": score,
                "verification_status": verif,
                "category": it.get("category", "国际"),
                "title": it.get("title_zh", it.get("title", "")),
                "summary": it.get("summary_zh", it.get("summary", "")),
                "url": it.get("url", ""),
                "source": it.get("source", "未知信源"),
                "published_at": it.get("published_at", ""),
                "heat_detail": detail,
                "verification_sources": ver_sources[:5],
            }
        )

    items.sort(key=lambda x: (x["heat_score"], x["published_at"]), reverse=True)

    for i, it in enumerate(items, start=1):
        it["rank"] = i

    by_cat: Dict[str, List[Dict[str, Any]]] = {c: [] for c in CATEGORY_ORDER}
    for it in items:
        c = it.get("category", "国际")
        if c not in by_cat:
            c = "国际"
        if len(by_cat[c]) < 10:
            by_cat[c].append(it)

    headlines = items[:10]
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_candidates": len(items),
        "headlines": headlines,
        "categories": by_cat,
        "heat_weight_rule": {
            "formula": "热度 = 10 * (时效*0.35 + 关键词*0.25 + 信源*0.20 + 同题覆盖*0.12 + 分类影响*0.08)",
            "weights": HEAT_WEIGHT,
        },
    }
    with open(EDIT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    log(f"edited items={len(items)}")
    return payload


def article_html(story: Dict[str, Any], idx: int, show_category: bool = True) -> str:
    title = html.escape(story.get("title", "未命名新闻"))
    summary = html.escape(story.get("summary", ""))
    source = html.escape(story.get("source", "信源"))
    url = html.escape(story.get("url") or "#")
    cat = html.escape(story.get("category", ""))
    heat = story.get("heat_score", 0)
    ver = html.escape(story.get("verification_status", ""))
    tstr = html.escape(story.get("published_at", ""))
    ver_sources = story.get("verification_sources", [])
    tooltip_text = "验证信源：" + ("、".join(ver_sources) if ver_sources else "暂无")
    tooltip_attr = html.escape(tooltip_text)

    category_block = f'<div class="category-tag">{cat}</div>' if show_category else ""
    return (
        '<article class="story-card">'
        f'<span class="rank-badge">#{idx}</span>'
        f'<span class="heat-score">{heat} 热度</span>'
        f'<span class="verification-status" data-tooltip="{tooltip_attr}" title="{tooltip_attr}">{ver}</span>'
        f'{category_block}'
        f'<h3 class="story-title"><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a></h3>'
        f'<p class="story-summary">{summary}</p>'
        f'<div class="story-meta"><a href="{url}" class="source-tag" target="_blank" rel="noopener noreferrer">{source}</a> | {tstr}</div>'
        '</article>'
    )


def section_html(tab_id: str, title: str, subtitle: str, stories: List[Dict[str, Any]], active: bool = False) -> str:
    cards = "\n".join(article_html(s, i + 1, show_category=True) for i, s in enumerate(stories[:10]))
    if not cards:
        cards = '<article class="story-card"><h3 class="story-title">暂无可展示新闻</h3><p class="story-summary">当前分类暂无足够内容，请稍后刷新。</p></article>'
    active_cls = " active" if active else ""
    return (
        f'<div id="{tab_id}" class="tab-content{active_cls}">' 
        '<div class="section-header">'
        f'<h2 class="section-title">{html.escape(title)}</h2>'
        f'<div class="section-meta">{html.escape(subtitle)}</div>'
        '</div>'
        '<div class="news-grid-list">'
        f'{cards}'
        '</div>'
        '</div>'
    )


def render_html(edited_payload: Dict[str, Any]) -> None:
    with open(os.path.join(RES_DIR, "template.html"), "r", encoding="utf-8") as f:
        tpl = f.read()

    # 复用模板样式和抽屉/脚本，同时由代码动态生成头部、导航和各分类区块
    head_end = tpl.find("</head>")
    footer_start = tpl.find('<footer class="footer">')
    script_start = tpl.find("<script>")
    script_end = tpl.find("</script>", script_start)
    if min(head_end, footer_start, script_start, script_end) < 0:
        raise RuntimeError("template.html 结构不符合预期")

    head_part = tpl[:head_end + len("</head>")]
    footer_part = tpl[footer_start:script_start]
    script_part = tpl[script_start:script_end + len("</script>")]

    now = datetime.now()
    date_s = now.strftime("%Y年%m月%d日")
    weekday_s = WEEKDAY_ZH[now.weekday()]
    update_s = now.strftime("%Y-%m-%d %H:%M")

    headlines = edited_payload.get("headlines", [])
    categories = edited_payload.get("categories", {})
    weight_hint = "热度权重：时效35% + 关键词25% + 信源20% + 同题覆盖12% + 分类影响8%"

    header_html = (
        '<header class="masthead">'
        '<h1 class="masthead-title"><a href="#">每日新闻</a></h1>'
        '<div class="masthead-date">{{GENERATE_DATE}} {{WEEKDAY}}'
        '<span class="lunar-full">'
        '<span class="lunar-ganzhi">{{GANZHI_YEAR}}</span>'
        '<span class="lunar-date">农历{{LUNAR_DATE}}</span>'
        '<span class="lunar-shengxiao">{{SHENGXIAO}}年</span>'
        "</span></div></header>"
    )
    nav_items = []
    for i, tab in enumerate(TAB_CONFIG):
        active_cls = " active" if i == 0 else ""
        nav_items.append(
            f'<li><a href="#" class="tab-link{active_cls}" data-tab="{tab["id"]}">{html.escape(tab["tab"])}</a></li>'
        )
    nav_html = '<nav class="tab-nav"><ul class="tab-list">' + "".join(nav_items) + "</ul></nav>"

    sections = [
        section_html(
            "top10",
            "每日热点",
            f"全平台最重要的10条新闻 | 更新时间：{update_s} | {weight_hint}",
            headlines,
            active=True,
        )
    ]

    for tab in TAB_CONFIG:
        tab_id = tab["id"]
        if tab_id == "top10":
            continue
        tab_categories = TAB_CATEGORY_MAP.get(tab_id, [])
        stories: List[Dict[str, Any]] = []
        for c in tab_categories:
            stories.extend(categories.get(c, []))
        stories.sort(key=lambda x: (x.get("heat_score", 0), x.get("published_at", "")), reverse=True)
        sections.append(section_html(tab_id, tab["title"], tab["subtitle"], stories[:10]))

    container = '<div class="container">' + "\n".join(sections) + "\n" + footer_part + "</div>"
    out = head_part + "\n<body>\n" + header_html + "\n" + nav_html + "\n" + container + "\n" + script_part + "\n</body>\n</html>\n"
    out = out.replace("{{GENERATE_DATE}}", date_s)
    out = out.replace("{{WEEKDAY}}", weekday_s)
    out = out.replace("{{GANZHI_YEAR}}", "乙巳")
    out = out.replace("{{LUNAR_DATE}}", "二月二十")
    out = out.replace("{{SHENGXIAO}}", "蛇")
    out = out.replace("{{UPDATE_TIME}}", update_s)
    out = out.replace("{{TIME_RELATIVE}}", "刚刚")

    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(out)

    log(f"html generated: {OUT_HTML}")


def validate_html() -> None:
    with open(OUT_HTML, "r", encoding="utf-8") as f:
        content = f.read()
    needed = ['id="top10"', 'id="world"', 'id="finance"', 'id="culture"', 'id="entertainment"', "tab-link", "每日热点"]
    missed = [k for k in needed if k not in content]
    if missed:
        raise RuntimeError(f"html validation failed, missing={missed}")


def cleanup_tmp_files() -> None:
    for root, _, files in os.walk(TMP_DIR):
        for name in files:
            p = os.path.join(root, name)
            try:
                os.remove(p)
            except FileNotFoundError:
                pass
    log("tmp files cleaned (directories kept)")


def main() -> int:
    ensure_dirs()
    try:
        raw = collect_rss()
        trans = translate_news(raw)
        edited = edit_news(trans)
        render_html(edited)
        validate_html()
        cleanup_tmp_files()
        report = {
            "processed_count": edited.get("total_candidates", 0),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "success": True,
            "retry_log": RETRY_LOG,
        }
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except Exception as e:
        log(f"pipeline failed: {type(e).__name__}: {e}")
        report = {
            "processed_count": 0,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "success": False,
            "error": str(e),
            "retry_log": RETRY_LOG,
        }
        print(json.dumps(report, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
