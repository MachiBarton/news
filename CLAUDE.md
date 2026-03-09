# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **news-daily** project - an automated news aggregation system that collects news from RSS feeds, translates, edits, and generates an HTML news page. It uses a multi-agent workflow coordinated through Claude Code's task system.

## Directory Structure

```
/Users/marcus/projects/pageDalliy/          <- Working root directory (NOT .claude/)
├── .claude/
│   ├── agents/                             <- Agent configurations (JSON)
│   │   ├── news-collector.json
│   │   ├── news-translator.json
│   │   ├── news-editor.json
│   │   ├── editor-in-chief.json
│   │   └── frontend-developer.json
│   └── skills/news-daily/SKILL.md          <- Workflow documentation
├── res/                                    <- Resources (inputs)
│   ├── rss_list.json                       <- RSS feed configurations
│   ├── template.json                       <- Data structure template
│   └── template.html                       <- HTML page template
├── tmp/                                    <- Temporary/cache (intermediate files)
│   ├── raw_news.json                       <- Collected raw news
│   ├── translated_news.json                <- Translated news
│   ├── edited_news.json                    <- Edited news
│   └── rss/                                <- Downloaded RSS XML files
└── output/                                 <- Output directory
    └── index.html                          <- Final generated HTML page
```

## Agent Workflow

The system uses 5 specialized agents in sequence:

1. **news-collector**: Reads `res/rss_list.json`, downloads RSS feeds to `tmp/rss/`, extracts metadata, outputs `tmp/raw_news.json`
2. **news-translator**: Reads `tmp/raw_news.json`, translates foreign content, outputs `tmp/translated_news.json`
3. **news-editor**: Reads `tmp/translated_news.json`, polishes content, adds heat scores, outputs `tmp/edited_news.json`
4. **editor-in-chief**: Reads `tmp/edited_news.json`, final review, selects top 10 per category + top 10 headlines, coordinates frontend-dev
5. **frontend-developer**: Reads `res/template.html` and final JSON, generates `output/index.html`

## Common Commands

### Run Complete Workflow
```bash
claude task "生成今日新闻" --agent editor-in-chief
```

### Run Individual Steps
```bash
claude task "采集RSS新闻" --agent news-collector
claude task "翻译外文新闻" --agent news-translator
claude task "编辑润色新闻" --agent news-editor
claude task "终审并生成HTML" --agent editor-in-chief
```

### Clean Up Intermediate Files
```bash
rm -rf tmp/* output/*
```

## Key Files Reference

- **RSS Sources**: `res/rss_list.json` - Contains 50+ RSS feeds categorized by topic (国际, 科技, 商业, 时政, etc.)
- **Data Template**: `res/template.json` - Defines the news article schema with fields: rank, heat_score, verification_status, title, summary, key_facts, sources_breakdown, controversy_note, category, why_matters, timestamp_range
- **HTML Template**: `res/template.html` - Newspaper-style responsive HTML template with CSS

## Data Flow

```
res/rss_list.json → tmp/raw_news.json → tmp/translated_news.json → tmp/edited_news.json → output/index.html
     ↓                    ↓                      ↓                       ↓
  RSS feeds          Collected            Translated              Edited
  (50+ sources)      (20-30 items)        (Chinese)               (Final selection)
```

## News Selection Rules

- **Per Category**: Top 10 stories by heat_score from each category (国际, 中国, 科技, 财经, 军事, 体育, 时政, 健康, 科学)
- **Headlines**: Top 10 stories by heat_score across all categories, shown in "头条" tab
- Final JSON structure: `{ "headlines": [...], "categories": { "国际": [...], ... } }`

## Cleanup Rules

- After successful HTML generation, delete all files in `tmp/` directory
- Keep `res/` directory intact (input templates)
- Keep `output/index.html` (final output)
