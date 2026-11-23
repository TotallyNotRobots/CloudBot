from __future__ import annotations

from typing import TYPE_CHECKING

from cloudbot import hook
from cloudbot.util import textgen

if TYPE_CHECKING:
    from collections.abc import Callable

    from cloudbot.bot import CloudBot
    from cloudbot.event_functions import EventAction, EventIsNickValid


class BasicFood:
    def __init__(
        self, name: str, unit: str, *commands: str, file: str | None = None
    ) -> None:
        self.name: str = name
        self.unit: str = unit
        self.commands: tuple[str, ...] = commands or (name,)
        self.file: str = file or f"{self.name}.json"


BASIC_FOOD = (
    BasicFood("sandwich", "a sandwich"),
    BasicFood("taco", "a taco"),
    BasicFood("coffee", "coffee"),
    BasicFood("noodles", "noodles"),
    BasicFood("muffin", "a muffin"),
    BasicFood("scone", "a scone"),
    BasicFood("donut", "a donut"),
    BasicFood("rice", "rice"),
    BasicFood("tea", "tea"),
    BasicFood("keto", "food"),
    BasicFood("beer", "beer"),
    BasicFood("cheese", "cheese"),
    BasicFood("pancake", "pancakes"),
    BasicFood("chicken", "chicken"),
    BasicFood("nugget", "nuggets"),
    BasicFood("pie", "pie"),
    BasicFood("brekkie", "brekkie", "brekkie", "brekky"),
    BasicFood("icecream", "icecream"),
    BasicFood("doobie", "a doobie"),
    BasicFood("wine", "wine"),
    BasicFood("pizza", "pizza"),
    BasicFood("vpizza", "pizza"),
    BasicFood("chocolate", "chocolate"),
    BasicFood("pasta", "pasta"),
    BasicFood("cereal", "cereal"),
    BasicFood("sushi", "sushi"),
    BasicFood("steak", "a nice steak dinner"),
    BasicFood("burger", "a tasty burger"),
    BasicFood("milkshake", "a milkshake"),
    BasicFood("kebab", "a kebab"),
    BasicFood("cake", "a cake"),
    BasicFood("hotchoc", "hotchoc"),
    BasicFood("squid", "some squid"),
    # Kept for posterity
    # <Luke> Hey guys, any good ideas for plugins?
    # <User> I don't know, something that lists every potato known to man?
    # <Luke> BRILLIANT
    BasicFood("potato", "a potato"),
    BasicFood("cookie", "a cookie", file="cookies.json"),
    BasicFood("soup", "Some Soup"),
    BasicFood("halal", "food", "halal", "halaal"),
    BasicFood("kosher", "food"),
    BasicFood("birthday", "birthday cake"),
)

basic_food_data = dict[str, textgen.TemplateConfig]()


@hook.on_start()
def load_foods(bot: CloudBot) -> None:
    basic_food_data.clear()
    food_dir = bot.data_path / "food"
    for food in BASIC_FOOD:
        basic_food_data[food.name] = textgen.TemplateConfig.from_json_file(
            food_dir / food.file
        )


def basic_format(
    nick: str, text: str, data: textgen.TemplateConfig, **kwargs: str
) -> str:
    user = text
    kwargs["user"] = user
    kwargs["target"] = user
    kwargs["nick"] = nick

    generator = data.make_generator(has_target=bool(text), variables=kwargs)
    return generator.generate_string()


def basic_food(food: BasicFood) -> Callable[..., str | None]:
    def func(
        text: str,
        nick: str,
        action: EventAction,
        is_nick_valid: EventIsNickValid,
    ) -> str | None:
        if not is_nick_valid(text):
            return f"I can't give {food.unit} to that user."

        action(basic_format(nick, text, basic_food_data[food.name]))
        return None

    func.__name__ = food.name
    func.__doc__ = f"<user> - gives {food.unit} to [user]"
    return func


def init_hooks() -> None:
    for food in BASIC_FOOD:
        globals()[food.name] = hook.command(*food.commands)(basic_food(food))


init_hooks()
