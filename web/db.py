import os
from supabase import create_client

_client = None


def get_client():
    global _client
    if _client is None:
        url = os.environ.get("SUPABASE_URL", "").strip()
        key = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL ba SUPABASE_SERVICE_KEY set kora nai "
                "(Render > Environment e dao)")
        _client = create_client(url, key)
    return _client


class _Lazy:
    """App boot howar shomoy env na thakleo crash korbe na; prothom use e clear error dibe."""
    def __getattr__(self, name):
        return getattr(get_client(), name)


sb = _Lazy()
