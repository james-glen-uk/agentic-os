# News Oracle

Fetches the configured RSS/Atom feeds, de-duplicates entries, and clusters
headlines into ranked trending topics.

**This is a code-backed skill.** The scheduler job (`News Oracle Refresh`,
daily at 07:00) and the `POST /api/news/refresh` endpoint run
`news_oracle.py` directly — no agent tokens needed. Results are stored in
`data/news/YYYY-MM-DD.json` and shown on the News page, where every topic
card offers one-click **SEO article** and **Social drafts** actions.

## Configuration (data/settings.json)

```json
{
  "news": {
    "feeds": ["https://hnrss.org/frontpage", "..."],
    "max_topics": 10,
    "use_llm": false
  }
}
```

- `feeds` — RSS/Atom URLs (defaults to a tech/AI starter set)
- `use_llm` — when true, an agent (research chain: Gemini primary, with
  fallback) writes a one-line summary per topic; heuristic clustering
  still works with every agent offline

Primary: gemini
