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
