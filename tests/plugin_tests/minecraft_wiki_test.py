import importlib

from plugins import minecraft_wiki
from tests.util import get_test_data, run_cmd


def test_mcwiki(mock_requests):
    importlib.reload(minecraft_wiki)
    mock_requests.add(
        "GET",
        "http://minecraft.gamepedia.com/api.php?action=opensearch&search"
        "=diamond",
        json=[
            "diamond",
            [
                "Diamond",
                "Diamond Ore",
                "Diamond (disambiguation)",
                "Diamond Chicken",
                "DIAMONDS",
                "Diamond Armor",
                "Diamond Pickaxe",
                "Diamond Horse Armor",
                "Diamond block",
                "Diamond Sword",
            ],
            ["", "", "", "", "", "", "", "", "", ""],
            [
                "https://minecraft.gamepedia.com/Diamond",
                "https://minecraft.gamepedia.com/Diamond_Ore",
                "https://minecraft.gamepedia.com/Diamond_(disambiguation)",
                "https://minecraft.gamepedia.com/Diamond_Chicken",
                "https://minecraft.gamepedia.com/DIAMONDS",
                "https://minecraft.gamepedia.com/Diamond_Armor",
                "https://minecraft.gamepedia.com/Diamond_Pickaxe",
                "https://minecraft.gamepedia.com/Diamond_Horse_Armor",
                "https://minecraft.gamepedia.com/Diamond_block",
                "https://minecraft.gamepedia.com/Diamond_Sword",
            ],
        ],
    )
    mock_requests.add(
        "GET",
        "http://minecraft.gamepedia.com/Diamond",
        body=get_test_data("minecraft_wiki-diamond.html"),
    )
    assert run_cmd(minecraft_wiki.mcwiki, "mcwiki", "diamond") == [
        (
            "return",
            "A Diamond is a rare mineral obtained from diamond ore or loot "
            "chests. They are mainly used to craft high-tier tools and armor, "
            "enchanting tables, blocks of diamond, and jukeboxes. :: "
            "http://minecraft.gamepedia.com/Diamond",
        )
    ]
