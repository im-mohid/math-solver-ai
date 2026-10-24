from worker.core.base import Feature


class DummySolver(Feature):
    """Kono model on na thakle pipe test korar jonno test answer dey."""
    name = "dummy_solver"
    stage = "solve"
    order = 5

    def should_run(self, ctx):
        return not ctx["models"].any_enabled()

    def run(self, ctx):
        q = ctx["question"]
        ctx["answer"].update({
            "understood_question": q.replace("<document>\n", "").replace("\n</document>", ""),
            "approach": "Phase 0 test: ekhono model connect kora hoyni.",
            "steps": [
                {"title": "Pipe test", "latex": "$e^{i\\pi} + 1 = 0$",
                 "explain": "Page -> Supabase -> Colab -> page loop thik moto kaj korche."},
            ],
            "final_answer": "Test answer (model off). Apnar question/file theke pawa text: " + q[:300],
            "confidence": "none (dummy)",
        })
        return ctx
