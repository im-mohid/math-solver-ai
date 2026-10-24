def compose_question(ctx):
    """User er question + document text ek kore ctx['question'] banay."""
    q = ctx.get("user_question", "")
    doc = ctx.get("document_text", "").strip()
    if doc:
        q = (q + "\n\n" if q else "") + "<document>\n" + doc + "\n</document>"
    ctx["question"] = q
    return q


def extract_final(text, limit=600):
    marker = "Final answer:"
    if marker in text:
        return text.rsplit(marker, 1)[-1].strip()[:limit]
    return ""


def history_messages(ctx, limit=10):
    """Page theke asha ager chat message gulo (validate kore)."""
    out = []
    for m in (ctx["options"].get("history") or [])[-limit:]:
        if isinstance(m, dict) and m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str):
            out.append({"role": m["role"], "content": m["content"][:4000]})
    return out


def full_user(ctx):
    """Current question + (thakle) web search result. Web result 'data', instruction na."""
    text = ctx["question"]
    web = ctx.get("web_context")
    if web:
        text += "\n\n<web_results>\n" + web + "\n</web_results>"
    return text


def build_messages(ctx, system, user=None):
    return ([{"role": "system", "content": system}]
            + history_messages(ctx)
            + [{"role": "user", "content": user if user is not None else full_user(ctx)}])


def clean_question(q):
    return q.replace("<document>\n", "").replace("\n</document>", "")
