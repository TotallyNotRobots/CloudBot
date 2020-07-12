from plugins import minecraft_user


def test_get_name(mock_requests):
    mock_requests.add(
        "GET",
        "https://api.mojang.com/user/profiles"
        "/6c78b87b38784ee1813a92a6a1fb37a9/names",
        json=[
            {"name": "linuxdemon"},
            {"name": "linuxdaemon", "changedToAt": 1484192187000},
        ],
    )
    name = minecraft_user.get_name("6c78b87b38784ee1813a92a6a1fb37a9")
    assert name == "linuxdaemon"
