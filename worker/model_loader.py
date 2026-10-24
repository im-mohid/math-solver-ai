def load_model(cfg):
    """Model off thakle None dey (Phase 0). On hole (tokenizer, model) tuple dey."""
    mcfg = cfg.get("model", {})
    if not mcfg.get("enabled"):
        print("[model] disabled (Phase 0 dummy mode)")
        return None

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    name = mcfg["name"]
    kwargs = {"device_map": "auto"}
    if mcfg.get("load_in_4bit", True):
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16, bnb_4bit_quant_type="nf4")
    else:
        kwargs["torch_dtype"] = torch.float16

    print(f"[model] loading {name} ...")
    tok = AutoTokenizer.from_pretrained(name)
    model = AutoModelForCausalLM.from_pretrained(name, **kwargs)

    if mcfg.get("lora_path"):
        from peft import PeftModel   # requirements e peft add korte hobe
        model = PeftModel.from_pretrained(model, mcfg["lora_path"])
    model.eval()
    return tok, model
