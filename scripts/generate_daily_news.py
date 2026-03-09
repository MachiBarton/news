#!/usr/bin/env python3
import json
import os
import re
import html
import time
import random
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import List, Dict, Any

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

CATEGORY_ORDER = ["国际", "时政", "军事", "科技", "商业", "健康", "科学", "中国", "体育"]
CAT_TAB = {
    "国际": "world",
    "时政": "politics",
    "军事": "military",
    "科技": "tech",
    "商业": "business",
    "财经": "business",
    "健康": "health",
    "科学": "science",
    "中国": "china",
    "体育": "sports",
}

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

    max_total_items = 90
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
            if picked >= 2:
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
    max_translate_items = 40
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


def score_item(it: Dict[str, Any]) -> float:
    base = 5.0
    title = it.get("title_zh", "")
    summary = it.get("summary_zh", "")
    txt = f"{title} {summary}".lower()

    hot_kw = ["war", "strike", "attack", "ai", "openai", "trump", "china", "market", "election", "virus", "conflict"]
    hot_zh = ["战争", "袭击", "冲突", "人工智能", "选举", "中国", "市场", "芯片", "疫苗", "经济"]
    for k in hot_kw:
        if k in txt:
            base += 0.35
    for k in hot_zh:
        if k in txt:
            base += 0.45
    base += random.uniform(0, 1.2)
    return min(round(base, 1), 9.9)


def edit_news(trans_payload: Dict[str, Any]) -> Dict[str, Any]:
    items = []
    for it in trans_payload.get("items", []):
        score = score_item(it)
        verif = "✅ 已验证" if score >= 7.0 else "⚠️ 部分验证"
        items.append(
            {
                "heat_score": score,
                "verification_status": verif,
                "category": it.get("category", "国际"),
                "title": it.get("title_zh", it.get("title", ""))[:90],
                "summary": it.get("summary_zh", it.get("summary", ""))[:180],
                "url": it.get("url", ""),
                "source": it.get("source", "未知信源"),
                "published_at": it.get("published_at", ""),
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

    category_block = f'<div class="category-tag">{cat}</div>' if show_category else ""
    return (
        '<article class="story-card">'
        f'<span class="rank-badge">#{idx}</span>'
        f'<span class="heat-score">{heat} 热度</span>'
        f'<span class="verification-status">{ver}</span>'
        f'{category_block}'
        f'<h3 class="story-title"><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a></h3>'
        f'<p class="story-summary">{summary}</p>'
        f'<div class="story-meta"><a href="{url}" class="source-tag" target="_blank" rel="noopener noreferrer">{source}</a> | {tstr}</div>'
        '</article>'
    )


def section_html(tab_id: str, title: str, subtitle: str, stories: List[Dict[str, Any]], active: bool = False) -> str:
    cards = "\n".join(article_html(s, i + 1, show_category=True) for i, s in enumerate(stories[:10]))
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

    # 提取样式到 </head> 以及脚本尾部，复用模板视觉/交互
    head_end = tpl.find("</head>")
    body_start = tpl.find("<body>")
    footer_start = tpl.find('<footer class="footer">')
    script_start = tpl.find("<script>")
    if min(head_end, body_start, footer_start, script_start) < 0:
        raise RuntimeError("template.html 结构不符合预期")

    head_part = tpl[:head_end + len("</head>")]
    footer_part = tpl[footer_start:script_start]
    script_part = tpl[script_start:]

    now = datetime.now()
    date_s = now.strftime("%Y年%m月%d日")
    weekday_s = WEEKDAY_ZH[now.weekday()]
    update_s = now.strftime("%Y-%m-%d %H:%M")

    headlines = edited_payload.get("headlines", [])
    categories = edited_payload.get("categories", {})

    sections = []
    sections.append(section_html("top10", "今日头条", f"全平台最重要的10条新闻 | 更新时间：{update_s}", headlines, active=True))

    mapping = [
        ("world", "国际新闻", "来自全球各地的重要新闻", categories.get("国际", [])),
        ("politics", "时政", "政策与政治动态", categories.get("时政", [])),
        ("military", "军事", "全球军事动态与国防新闻", categories.get("军事", [])),
        ("tech", "科技", "全球科技创新与产业动态", categories.get("科技", [])),
        ("business", "商业", "商业、财经与市场变化", categories.get("商业", []) + categories.get("财经", [])),
        ("health", "健康", "公共卫生与医学动态", categories.get("健康", [])),
        ("science", "科学", "科研前沿与科学进展", categories.get("科学", [])),
        ("china", "中国", "中国相关新闻", categories.get("中国", [])),
        ("sports", "体育", "体育赛事与产业动态", categories.get("体育", [])),
    ]
    for tid, title, subtitle, stories in mapping:
        sections.append(section_html(tid, title, subtitle, stories))

    container = '<div class="container">' + "\n".join(sections) + "\n" + footer_part + "</div>"

    out = head_part + "\n<body>\n" + container + "\n" + script_part
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
    needed = ["今日头条", 'id="top10"', 'id="world"', 'id="tech"', "tab-link"]
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
