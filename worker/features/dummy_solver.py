from worker.core.base import Feature


class DummySolver(Feature):
    """Phase 0: pipe kaj korche kina test korar jonno. Phase 1 e config e off koro."""
    name = "dummy_solver"
    stage = "solve"
    order = 10

    def run(self, ctx):
        q = ctx["question"]
        ctx["answer"].update({
            "understood_question": q,
            "approach": "Phase 0 test: ekhono model connect kora hoyni.",
            "steps": [
                {"title": "Pipe test", "latex": "$e^{i\\pi} + 1 = 0$",
                 "explain": "Page -> Supabase -> Colab -> page loop thik moto kaj korche."},
            ],
            "final_answer": "Test answer (model off). Apnar question: " + q[:200],
            "confidence": "none (dummy)",
        })
        return ctx
