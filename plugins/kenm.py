import random

from cloudbot import hook

kenm_data: list[str] = []


@hook.on_start()
def load_kenm(bot):
    kenm_data.clear()
    with open((bot.data_path / "kenm.txt"), encoding="utf-8") as f:
        kenm_data.extend(
            line.strip() for line in f.readlines() if not line.startswith("//")
        )


@hook.command("kenm", autohelp=False)
def kenm(message):
    """- Wisdom from Ken M."""
    message(random.choice(kenm_data))
