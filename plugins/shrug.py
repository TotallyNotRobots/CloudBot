from cloudbot import hook


@hook.command("shrug", autohelp=False)
def shrug():
    """- shrugs"""
    return "¯\_(ツ)_/¯"
