from worker.core.base import Feature
from worker.core.text import compose_question

OCR_PROMPT = ("Transcribe all the text and math in this image exactly. "
              "Write math in LaTeX ($...$). Output only the transcription.")


class OcrVL(Feature):
    """Photo / scanned PDF theke text ber kore (models.ocr on thakle)."""
    name = "ocr_vl"
    stage = "pre"
    order = 20

    def should_run(self, ctx):
        return bool(ctx["images"]) and ctx["models"].has("ocr")

    def run(self, ctx):
        parts = [ctx["models"].read_image(img, OCR_PROMPT) for img in ctx["images"]]
        text = "\n\n".join(p for p in parts if p)
        ctx["document_text"] = (ctx["document_text"] + "\n\n" + text).strip()
        compose_question(ctx)
        return ctx
