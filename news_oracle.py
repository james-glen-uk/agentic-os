"""News Oracle — fetch RSS/Atom feeds and cluster into trending topics.

Deterministic keyword clustering by default (works offline-ish, $0);
optional LLM enrichment is layered on by the server when
settings news.use_llm is true.
"""
import os
import re
from pathlib import Path

# Root of all runtime state; AGENTIC_OS_HOME overrides for tests/custom installs
ROOT_DIR = Path(os.environ.get("AGENTIC_OS_HOME") or Path(__file__).parent).resolve()
NEWS_DIR = ROOT_DIR / "data" / "news"

DEFAULT_FEEDS = [
    "https://hnrss.org/frontpage",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://feeds.arstechnica.com/arstechnica/index",
]

_STOPWORDS = {
    "this", "that", "with", "from", "have", "will", "your", "about", "into",
    "over", "after", "before", "their", "there", "what", "when", "where",
    "which", "while", "would", "could", "should", "than", "then", "them",
    "they", "been", "being", "were", "does", "just", "like", "more", "most",
    "some", "such", "only", "also", "here", "make", "made", "gets", "goes",
    "says", "said", "show", "shows", "year", "years", "week", "today", "still",
    "first", "last", "next", "best", "every", "how", "why", "who", "its",
    "are", "was", "has", "had", "the", "and", "for", "not", "you", "all",
    "can", "her", "his", "one", "our", "out", "day", "get", "use", "new",
    "now", "way", "may", "say",
}

MAX_ENTRIES_PER_FEED = 30
MIN_KEYWORD_OVERLAP = 2


def fetch_entries(feeds: list) -> list:
    """Pull entries from each feed; a broken feed never fails the run."""
    import feedparser
    entries = []
    seen_links = set()
    for url in feeds:
        try:
            parsed = feedparser.parse(url)
            source = parsed.feed.get("title", url)
            for e in parsed.entries[:MAX_ENTRIES_PER_FEED]:
                link = e.get("link", "")
                if not e.get("title") or link in seen_links:
                    continue
                seen_links.add(link)
                entries.append({
                    "title": e.get("title", "").strip(),
                    "link": link,
                    "source": source,
                    "published": e.get("published", e.get("updated", "")),
                })
        except Exception:
            continue
    return entries


def _keywords(title: str) -> set:
    tokens = re.findall(r"[a-z0-9']+", title.lower())
    return {t for t in tokens if len(t) > 3 and t not in _STOPWORDS}


def cluster_topics(entries: list, max_topics: int = 10) -> list:
    """Greedy keyword-overlap clustering, ranked by cluster size."""
    clusters = []
    for e in entries:
        kws = _keywords(e["title"])
        if not kws:
            continue
        best, best_overlap = None, 0
        for c in clusters:
            overlap = len(kws & c["keywords"])
            if overlap >= MIN_KEYWORD_OVERLAP and overlap > best_overlap:
                best, best_overlap = c, overlap
        if best:
            best["entries"].append(e)
            best["keywords"] |= kws
        else:
            clusters.append({"keywords": set(kws), "entries": [e]})

    clusters.sort(key=lambda c: len(c["entries"]), reverse=True)
    topics = []
    for rank, c in enumerate(clusters[:max_topics], 1):
        if len(c["entries"]) == 1:
            title = c["entries"][0]["title"]
        else:
            # Name multi-story topics by their most shared title words
            counts = {}
            for e in c["entries"]:
                for k in _keywords(e["title"]):
                    counts[k] = counts.get(k, 0) + 1
            top = sorted(counts, key=lambda k: (-counts[k], k))[:4]
            title = " ".join(w.capitalize() for w in top)
        topics.append({
            "rank": rank,
            "title": title,
            "summary": "",
            "keywords": sorted(c["keywords"])[:8],
            "count": len(c["entries"]),
            "headlines": c["entries"][:6],
        })
    return topics
