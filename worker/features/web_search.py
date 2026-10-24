import ipaddress
import re
import socket
from urllib.parse import urlparse, urljoin

from worker.core.base import Feature
from worker.core.text import clean_question

MAX_RESULTS = 5
FETCH_TOP = 2            # prothom koyta result er page pura pora hobe
PAGE_CHARS = 2500
MAX_BYTES = 800_000

# Ei shobdo thakle shorashori search (model ke jiggesh na kore)
CUES = re.compile(
    r"(latest|current|currently|recent|today|news|202[4-9]|who is|who won|price|release|version|"
    r"arxiv|journal|search|internet|google|http|সর্বশেষ|এখন|আজ|খবর|দাম|সার্চ|ইন্টারনেট)", re.I)

ROUTER_SYSTEM = (
    "You decide whether a web search is needed to answer the user's latest message reliably. "
    "Answer SEARCH only if it needs up-to-date facts, specific papers/people/events/products, or niche "
    "definitions/theorems you may not know reliably. Pure calculation, standard textbook math, proofs, "
    "greetings and casual chat need NO search. "
    "Reply exactly 'NO' or 'SEARCH: <short English query with math terms>'."
)


def _ddgs():
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS
    return DDGS()


def search_mode(ctx):
    opts = ctx["options"]
    if "search" not in opts:
        return "auto"
    v = opts["search"]
    if v is True or v == "on":
        return "on"
    if v in (False, None, "", "off"):
        return "off"
    return "auto"


# ---------- safe page fetch ----------
def is_public_url(url):
    try:
        p = urlparse(url)
        if p.scheme not in ("http", "https") or not p.hostname:
            return False
        for info in socket.getaddrinfo(p.hostname, p.port or 443):
            ip = ipaddress.ip_address(info[4][0])
            if (ip.is_private or ip.is_loopback or ip.is_link_local
                    or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
                return False
        return True
    except Exception:
        return False


def html_to_text(html):
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for t in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            t.decompose()
        text = soup.get_text(" ", strip=True)
    except ImportError:
        text = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_text(url):
    """Page theke text ane. Private IP / onek boro file / non-text ke skip kore."""
    try:
        import requests
        for _ in range(4):                              # max 3 redirect, prottek bar check
            if not is_public_url(url):
                return ""
            r = requests.get(url, timeout=8, stream=True, allow_redirects=False,
                             headers={"User-Agent": "Mozilla/5.0 (MathSolverBot)"})
            if r.is_redirect or r.status_code in (301, 302, 303, 307, 308):
                url = urljoin(url, r.headers.get("Location", ""))
                continue
            ctype = r.headers.get("Content-Type", "")
            if r.status_code != 200 or not any(x in ctype for x in ("text/html", "text/plain", "xhtml")):
                return ""
            data = b""
            for chunk in r.iter_content(65536):
                data += chunk
                if len(data) > MAX_BYTES:
                    break
            return html_to_text(data.decode(r.encoding or "utf-8", errors="replace"))[:PAGE_CHARS]
    except Exception as e:
        print("[web_search] fetch error:", e)
    return ""


# ---------- main search ----------
def search_web(ctx, query):
    """Search kore ctx['web_context'] ar answer['sources'] set kore. Pele True."""
    try:
        results = list(_ddgs().text(query, max_results=MAX_RESULTS))
    except Exception as e:
        print("[web_search] search error:", e)
        results = []
    if not results:
        ctx["answer"]["search_note"] = "Web e kichu khuje pawa jayni ba search kaj kori ni."
        return False

    blocks, sources = [], []
    for i, r in enumerate(results, 1):
        title = (r.get("title") or "")[:150]
        url = r.get("href") or r.get("url") or ""
        text = (r.get("body") or "")[:400]
        if i <= FETCH_TOP and url:
            page = fetch_text(url)
            if page:
                text = text + "\n" + page
        blocks.append(f"[{i}] {title}\n{text}\n{url}")
        sources.append({"title": title or url, "url": url})
    ctx["web_context"] = "\n\n".join(blocks)
    ctx["sources"] = sources
    ctx["answer"]["sources"] = sources
    ctx["answer"]["search_query"] = query
    ctx["answer"].pop("search_note", None)
    return True


class WebSearch(Feature):
    """Search mode: off / auto / on.
    auto: model nijei bujhe kokhon net e khujte hobe. on: shobshomoy search."""
    name = "web_search"
    stage = "pre"
    order = 30

    def should_run(self, ctx):
        return search_mode(ctx) != "off" and bool(ctx["question"].strip())

    def make_query(self, ctx):
        q = clean_question(ctx["question"]).strip()
        models = ctx["models"]
        if models.has("language"):
            try:
                out = models.generate("language", [
                    {"role": "system", "content": "Write ONE short web search query (max 12 words, English, "
                                                  "include math terms) for the user's request. Output only the query."},
                    {"role": "user", "content": q[:800]},
                ], max_new_tokens=40, thinking=False).strip().strip('"')
                if out:
                    return out.splitlines()[0][:200]
            except Exception as e:
                print("[web_search] query model error:", e)
        return q[:200]

    def decide(self, ctx):
        """auto mode: search lagbe kina. Lagle query, na hole None."""
        q = clean_question(ctx["question"]).strip()
        if CUES.search(q):
            return self.make_query(ctx)
        models = ctx["models"]
        if not models.has("language"):
            return None
        try:
            out = models.generate("language", [
                {"role": "system", "content": ROUTER_SYSTEM},
                {"role": "user", "content": q[:900]},
            ], max_new_tokens=60, thinking=False).strip()
        except Exception as e:
            print("[web_search] router error:", e)
            return None
        m = re.match(r"(?is)\s*SEARCH\s*:\s*(.+)", out)
        return m.group(1).splitlines()[0].strip().strip('"')[:200] if m else None

    def run(self, ctx):
        query = self.make_query(ctx) if search_mode(ctx) == "on" else self.decide(ctx)
        if query:
            print("[web_search] query:", query)
            search_web(ctx, query)
        return ctx
