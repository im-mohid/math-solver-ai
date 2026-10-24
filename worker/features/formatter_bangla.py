from worker.core.base import Feature


class FormatterBangla(Feature):
    """Answer er shape thik kore: shob expected field thakbe, onno kichu bhenge dibe na."""
    name = "formatter_bangla"
    stage = "post"
    order = 90

    def run(self, ctx):
        a = ctx["answer"]
        a.setdefault("understood_question", ctx["question"])
        a.setdefault("steps", [])
        a.setdefault("final_answer", "")
        a.setdefault("confidence", "unknown")
        a.setdefault("sources", [])
        return ctx
