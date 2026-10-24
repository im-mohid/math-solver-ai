import gc
import re

THINK_RE = re.compile(r"<think>.*?(</think>|$)", re.DOTALL)


class ModelManager:
    """language / expert / ocr model gulo manage kore.

    resident=true  -> prothombar load, GPU te thake
    resident=false -> dorkar hole load, kaj shesh e unload (GPU memory bachay)
    """

    def __init__(self, cfg):
        self.cfg = cfg.get("models", {})
        self.four_bit = self.cfg.get("load_in_4bit", True)
        self.loaded = {}

    def has(self, name):
        m = self.cfg.get(name)
        return isinstance(m, dict) and bool(m.get("enabled")) and bool(m.get("name"))

    def any_enabled(self):
        return any(self.has(n) for n in ("language", "expert", "ocr"))

    def preload(self):
        for n in ("language", "expert"):
            if self.has(n) and self.cfg[n].get("resident", True):
                self._get(n)

    # ---------- loading ----------
    def _get(self, name):
        if name not in self.loaded:
            print(f"[model] loading {name}: {self.cfg[name]['name']}")
            self.loaded[name] = self._load(name)
        return self.loaded[name]

    def _unload(self, name):
        self.loaded.pop(name, None)
        gc.collect()
        try:
            import torch
            torch.cuda.empty_cache()
        except Exception:
            pass

    def _load(self, name):
        import torch
        from transformers import BitsAndBytesConfig

        c = self.cfg[name]
        kwargs = {"device_map": "auto"}
        if self.four_bit:
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
                llm_int8_skip_modules=["visual", "lm_head"] if name == "ocr" else None)
        else:
            kwargs["torch_dtype"] = torch.float16

        if name == "ocr":
            # NOTE: ekhono GPU te test kora hoyni
            from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
            proc = AutoProcessor.from_pretrained(c["name"], min_pixels=256 * 28 * 28, max_pixels=1024 * 28 * 28)
            model = Qwen2_5_VLForConditionalGeneration.from_pretrained(c["name"], **kwargs)
            model.eval()
            return proc, model

        from transformers import AutoModelForCausalLM, AutoTokenizer
        tok = AutoTokenizer.from_pretrained(c["name"])
        model = AutoModelForCausalLM.from_pretrained(c["name"], **kwargs)
        if c.get("lora_path"):
            from peft import PeftModel
            model = PeftModel.from_pretrained(model, c["lora_path"])
        model.eval()
        return tok, model

    def _release_if_needed(self, name):
        if not self.cfg[name].get("resident", name != "ocr"):
            self._unload(name)

    # ---------- use ----------
    def generate(self, name, messages, max_new_tokens=None, thinking=None):
        import torch
        c = self.cfg[name]
        tok, model = self._get(name)
        try:
            text = tok.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True,
                enable_thinking=bool(c.get("thinking", False) if thinking is None else thinking))
            inputs = tok([text], return_tensors="pt").to(model.device)
            with torch.no_grad():
                out = model.generate(
                    **inputs, max_new_tokens=max_new_tokens or c.get("max_new_tokens", 1500),
                    do_sample=False)
            reply = tok.decode(out[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        finally:
            self._release_if_needed(name)
        return THINK_RE.sub("", reply).strip()

    def read_image(self, image, prompt, max_new_tokens=1500):
        import torch
        proc, model = self._get("ocr")
        try:
            messages = [{"role": "user", "content": [
                {"type": "image"}, {"type": "text", "text": prompt}]}]
            text = proc.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = proc(text=[text], images=[image], return_tensors="pt").to(model.device)
            with torch.no_grad():
                out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
            reply = proc.batch_decode(out[:, inputs.input_ids.shape[1]:], skip_special_tokens=True)[0]
        finally:
            self._release_if_needed("ocr")
        return reply.strip()
