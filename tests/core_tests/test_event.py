def test_event_copy():
    from cloudbot.event import Event

    event = Event(bot=object())

    new_event = Event(base_event=event)

    assert event.bot is new_event.bot
