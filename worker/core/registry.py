import importlib
import pkgutil
import yaml

from worker import features
from worker.core.base import Feature

STAGE_ORDER = {"pre": 0, "solve": 1, "post": 2}


def load_config(path="config.yaml"):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_features(cfg=None):
    cfg = cfg or load_config()
    feat_cfg = cfg.get("features", {})
    found = []
    for m in pkgutil.iter_modules(features.__path__):
        mod = importlib.import_module(f"worker.features.{m.name}")
        for obj in vars(mod).values():
            if isinstance(obj, type) and issubclass(obj, Feature) and obj is not Feature:
                f = obj()
                f.enabled = feat_cfg.get(f.name, {}).get("enabled", False)
                if f.enabled:
                    found.append(f)
    return sorted(found, key=lambda f: (STAGE_ORDER.get(f.stage, 9), f.order))
