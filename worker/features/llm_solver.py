from worker.core.base import Feature

SYSTEM_PROMPT = (
    "Tumi ekjon math tutor. Question ta step-by-step Bangla te solve koro. "
    "Math expression LaTeX e likho ($...$). Shesh e 'Final answer:' likhe uttor dao. "
    "Nishchit na hole shetao bolo."
)


class LLMSolver(Feature):
    """Phase 1: asol model diye solve. config e model.enabled ar features.llm_solver true koro.

    NOTE: ei code ta ekhono Colab GPU te test kora hoyni. Prothom bar chalaye
    model er chat template / generate setting adjust korte hobe.
    """
    name = "llm_solver"
    stage = "solve"
    order = 10

    def should_run(self, ctx):
        return ctx.get("model") is not None

    def run(self, ctx):
        tok, model = ctx["model"]
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": ctx["question"]},
        ]
        text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tok([text], return_tensors="pt").to(model.device)
        out = model.generate(**inputs, max_new_tokens=1500, do_sample=False)
        reply = tok.decode(out[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        ctx["answer"].update({
            "understood_question": ctx["question"],
            "steps": [{"title": "Solution", "explain": reply}],
            "final_answer": reply.split("Final answer:")[-1].strip() if "Final answer:" in reply else "",
            "confidence": "unverified",
        })
        return ctx
