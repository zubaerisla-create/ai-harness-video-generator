import re
import html
import logging
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional, Tuple
import httpx

logger = logging.getLogger("ai_harness.online_researcher")

# Category topic RSS feeds
CATEGORY_RSS_URLS = {
    "ai_news": "https://news.google.com/rss/search?q=artificial+intelligence+OR+LLM+OR+robotics+OR+OpenAI+when:3d&hl=en-US&gl=US&ceid=US:en",
    "business_strategy": "https://news.google.com/rss/search?q=business+strategy+OR+corporate+market+OR+billion+acquisition+when:3d&hl=en-US&gl=US&ceid=US:en",
    "emerging_tech": "https://news.google.com/rss/search?q=emerging+technology+OR+semiconductor+OR+fusion+OR+quantum+computing+when:5d&hl=en-US&gl=US&ceid=US:en",
    "sci_fi_concept": "https://news.google.com/rss/search?q=NASA+OR+astronomy+OR+space+exploration+OR+deep+space+when:7d&hl=en-US&gl=US&ceid=US:en",
    "future_predictions": "https://news.google.com/rss/search?q=future+technology+trends+OR+automation+economy+OR+clean+energy+when:7d&hl=en-US&gl=US&ceid=US:en"
}

TOPIC_SECTION_RSS = {
    "technology": "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en",
    "business": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en",
    "science": "https://news.google.com/rss/headlines/section/topic/SCIENCE?hl=en-US&gl=US&ceid=US:en"
}

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, application/json, text/xml;q=0.9, */*;q=0.8"
}

def clean_html_tags(raw_html: str) -> str:
    """Removes HTML markup and unescapes entities."""
    if not raw_html:
        return ""
    clean_text = re.sub(r'<[^>]+>', ' ', raw_html)
    clean_text = html.unescape(clean_text)
    return " ".join(clean_text.split())

class OnlineResearcher:
    """
    Real-Time Online Information & Intelligence Research Engine.
    Fetches the latest online news, statistics, milestones, and authoritative context
    before writing scripts and planning video scenes.
    """
    def __init__(self, timeout: float = 8.0):
        self.timeout = timeout

    async def research_topic(self, topic: str, style: str = "business_strategy") -> Dict[str, Any]:
        """
        Gathers live real-world information, recent breaking articles, and background
        facts about a given topic to ground the script in authentic, current reality.
        """
        clean_topic = topic.replace("\n", " ").strip()
        # Extract main search terms
        search_terms = self._extract_search_query(clean_topic)

        logger.info(f"Researching live online data for topic: '{clean_topic}' (query: '{search_terms}')")

        news_items = await self._fetch_google_news_search(search_terms)
        
        # If specific search returned few results, try broader terms
        if len(news_items) < 2 and len(search_terms.split()) > 3:
            simplified = " ".join(search_terms.split()[:3])
            more_items = await self._fetch_google_news_search(simplified)
            news_items.extend(more_items)

        wiki_summary = await self._fetch_wikipedia_summary(search_terms)

        headline_facts = []
        entities = set()
        sources = []

        for item in news_items[:5]:
            title = item.get("title", "")
            pub_date = item.get("pub_date", "")
            publisher = item.get("publisher", "")
            
            # Format headline fact
            clean_t = title
            if " - " in clean_t:
                clean_t, publisher = clean_t.rsplit(" - ", 1)
            
            headline_facts.append(f"{clean_t.strip()} ({publisher.strip()}, {pub_date[:16]})")
            sources.append({"title": clean_t.strip(), "source": publisher.strip(), "date": pub_date})

            # Extract potential entities (capitalized phrases)
            caps = re.findall(r'\b[A-Z][a-zA-Z0-9_\-\.]{2,}\b', clean_t)
            for c in caps:
                if c.lower() not in ["the", "how", "why", "what", "and", "new", "all", "its", "are", "for"]:
                    entities.add(c)

        # Context summary
        context_parts = []
        if wiki_summary:
            context_parts.append(wiki_summary)
        if headline_facts:
            context_parts.append("Recent Developments: " + "; ".join(headline_facts[:3]))

        full_context = "\n\n".join(context_parts) if context_parts else f"Documentary analysis on {clean_topic}."

        return {
            "query": search_terms,
            "topic": clean_topic,
            "context_summary": full_context,
            "headline_facts": headline_facts,
            "entities": list(entities)[:10],
            "sources": sources[:4],
            "wikipedia_extract": wiki_summary
        }

    async def get_trending_topics(self, pillar: str = "business_strategy", limit: int = 5) -> List[Tuple[str, str, Dict[str, Any]]]:
        """
        Discovers the latest real-time trending news topics directly from live online RSS feeds.
        Returns tuples of (title, description, metadata_dossier) for auto-pilot generation.
        """
        rss_url = CATEGORY_RSS_URLS.get(pillar) or TOPIC_SECTION_RSS.get("technology")
        logger.info(f"Fetching real-time trending topics for pillar '{pillar}' from {rss_url}")

        items = await self._parse_rss_feed(rss_url, max_items=limit * 2)

        if not items and pillar in ["ai_news", "emerging_tech"]:
            items = await self._parse_rss_feed(TOPIC_SECTION_RSS["technology"], max_items=limit * 2)
        elif not items and pillar == "business_strategy":
            items = await self._parse_rss_feed(TOPIC_SECTION_RSS["business"], max_items=limit * 2)
        elif not items:
            items = await self._parse_rss_feed(TOPIC_SECTION_RSS["science"], max_items=limit * 2)

        trending = []
        for it in items:
            raw_title = it.get("title", "")
            publisher = ""
            if " - " in raw_title:
                raw_title, publisher = raw_title.rsplit(" - ", 1)
            raw_title = raw_title.strip()

            if len(raw_title) < 15:
                continue

            # Format documentary title and engaging description
            desc = it.get("description", "") or f"Investigative documentary breakdown on {raw_title} reported by {publisher}."
            desc = clean_html_tags(desc)[:220]

            meta = {
                "headline": raw_title,
                "publisher": publisher.strip(),
                "pub_date": it.get("pub_date", ""),
                "link": it.get("link", ""),
                "pillar": pillar
            }
            trending.append((raw_title, desc, meta))
            if len(trending) >= limit:
                break

        return trending

    def _extract_search_query(self, prompt: str) -> str:
        """Extracts clean keyword tokens suitable for news and wiki searches."""
        clean = prompt.split(":")[0] if ":" in prompt else prompt
        # Strip conversational prefix
        clean = re.sub(r'(?i)^(create|make|generate|produce|write|explain)\s+(a\s+)?(video\s+about\s+|story\s+about\s+)?', '', clean)
        clean = re.sub(r'[^\w\s\-\.]', ' ', clean)
        words = clean.split()
        return " ".join(words[:6]).strip()

    async def _fetch_google_news_search(self, query: str) -> List[Dict[str, str]]:
        if not query:
            return []
        encoded = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
        return await self._parse_rss_feed(url, max_items=6)

    async def _parse_rss_feed(self, url: str, max_items: int = 6) -> List[Dict[str, str]]:
        results = []
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(url, headers=HTTP_HEADERS)
                if resp.status_code != 200:
                    logger.debug(f"RSS fetch status {resp.status_code} for {url}")
                    return []

                content = resp.text
                root = ET.fromstring(content)
                channel = root.find("channel")
                if channel is None:
                    channel = root

                items = channel.findall("item")[:max_items]
                for item in items:
                    title_elem = item.find("title")
                    link_elem = item.find("link")
                    pub_date_elem = item.find("pubDate")
                    desc_elem = item.find("description")

                    title = title_elem.text if title_elem is not None and title_elem.text else ""
                    link = link_elem.text if link_elem is not None and link_elem.text else ""
                    pub_date = pub_date_elem.text if pub_date_elem is not None and pub_date_elem.text else ""
                    desc = clean_html_tags(desc_elem.text if desc_elem is not None and desc_elem.text else "")

                    if title:
                        results.append({
                            "title": title,
                            "link": link,
                            "pub_date": pub_date,
                            "description": desc
                        })
        except Exception as e:
            logger.debug(f"RSS parse error for {url}: {e}")
        return results

    async def _fetch_wikipedia_summary(self, query: str) -> Optional[str]:
        if not query:
            return None
        # Clean query for wikipedia title lookup
        title = query.split()[0:3]
        wiki_title = "_".join(title)
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(wiki_title)}"
        
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "AIStoryHarness/2.0 (investigative documentary engine)"})
                if resp.status_code == 200:
                    data = resp.json()
                    extract = data.get("extract", "")
                    if extract and len(extract) > 40:
                        return extract.strip()
        except Exception as e:
            logger.debug(f"Wikipedia lookup error for {query}: {e}")
        return None

online_researcher = OnlineResearcher()
