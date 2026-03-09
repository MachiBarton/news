# Codex CLI 定时日报

## 已提供文件
- `scripts/run_daily_news.sh`：定时入口（优先执行本地流水线脚本）
- `scripts/generate_daily_news.py`：本地新闻流水线（RSS 抓取/翻译/编辑/HTML 生成）
- `prompts/daily_news_codex_prompt.md`：给 codex exec 的自动化任务指令
- `launchd/com.marcus.pagedaily.news.plist`：macOS 每日 08:00 定时任务

## 手动执行一次
```bash
cd /Users/marcus/projects/pageDalliy
./scripts/run_daily_news.sh
```

## 安装定时任务（macOS）
```bash
mkdir -p /Users/marcus/projects/pageDalliy/logs
cp /Users/marcus/projects/pageDalliy/launchd/com.marcus.pagedaily.news.plist ~/Library/LaunchAgents/
launchctl unload ~/Library/LaunchAgents/com.marcus.pagedaily.news.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.marcus.pagedaily.news.plist
```

## 立即触发一次（不等到 08:00）
```bash
launchctl start com.marcus.pagedaily.news
```

## 查看状态和日志
```bash
launchctl list | rg pagedaily
ls -lt /Users/marcus/projects/pageDalliy/logs | head
```

常见日志文件：
- `logs/run_YYYY-MM-DD_HH-MM-SS.log`
- `logs/launchd.out.log`
- `logs/launchd.err.log`

## 修改执行时间
编辑 `~/Library/LaunchAgents/com.marcus.pagedaily.news.plist` 中：
- `Hour`
- `Minute`

然后重载：
```bash
launchctl unload ~/Library/LaunchAgents/com.marcus.pagedaily.news.plist
launchctl load ~/Library/LaunchAgents/com.marcus.pagedaily.news.plist
```
