class Feature:
    """Shob feature ei class theke inherit korbe.

    stage: "pre" -> "solve" -> "post" order e chole
    order: ek-i stage er moddhe chhoto number age chole
    """
    name = "base"
    stage = "pre"
    order = 50
    enabled = True

    def should_run(self, ctx) -> bool:
        return True

    def run(self, ctx):
        """ctx (dict) modify kore return koro."""
        return ctx
