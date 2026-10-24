import io

from worker.core.base import Feature
from worker.core.errors import UserError
from worker.core.text import compose_question

MAX_CHARS = 20000
MAX_PDF_PAGES = 15
MAX_SCAN_PAGES = 5


class FileReader(Feature):
    """Upload kora txt / md / tex / pdf / image pore ctx e rakhe."""
    name = "file_reader"
    stage = "pre"
    order = 10

    def should_run(self, ctx):
        return bool(ctx["job"].get("file_url"))

    def run(self, ctx):
        path = ctx["job"]["file_url"]
        ext = path.rsplit(".", 1)[-1].lower()
        data = ctx["download"](path)

        if ext in ("txt", "md", "tex"):
            text = data.decode("utf-8", errors="replace")
        elif ext == "pdf":
            text = self._read_pdf(data, ctx)
        elif ext in ("png", "jpg", "jpeg", "webp"):
            from PIL import Image
            img = Image.open(io.BytesIO(data)).convert("RGB")
            img.thumbnail((1600, 1600))                 # boro photo GPU memory khay
            ctx["images"] = [img]
            text = ""
        else:
            raise UserError("Ei file type support kora hoy na.")

        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS] + "\n[... baki ongsho kete deya hoyeche]"
        ctx["document_text"] = text.strip()

        if ctx["images"] and not ctx["models"].has("ocr"):
            raise UserError("Photo ba scanned PDF porar jonno OCR model ekhono on kora nai. "
                            "Text PDF ba TXT file upload koro, ba question type koro.")
        if not ctx["document_text"] and not ctx["images"] and not ctx["user_question"]:
            raise UserError("File theke kono text pawa jayni.")

        if ext == "pdf" and ctx["document_text"]:
            ctx["answer"]["read_text"] = ctx["document_text"][:3000]
        compose_question(ctx)
        return ctx

    @staticmethod
    def _read_pdf(data, ctx):
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz
        doc = fitz.open(stream=data, filetype="pdf")
        n = min(len(doc), MAX_PDF_PAGES)
        text = "\n".join(doc[i].get_text() for i in range(n)).strip()

        if len(text) < 40 * max(n, 1):             # prai kono text nai -> scanned PDF
            from PIL import Image
            imgs = []
            for i in range(min(len(doc), MAX_SCAN_PAGES)):
                pix = doc[i].get_pixmap(dpi=150)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                img.thumbnail((1600, 1600))
                imgs.append(img)
            ctx["images"] = imgs
        return text
