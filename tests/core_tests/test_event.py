def test_event_copy():
    from cloudbot.event import Event

    event = Event(
        bot=object(),
        conn=object(),
        hook=object(),
        event_type=object(),
        channel=object(),
        nick=object(),
        user=object(),
        host=object(),
    )

    new_event = Event(base_event=event)

    assert event.bot is new_event.bot
    assert event.conn is new_event.conn
    assert event.hook is new_event.hook
    assert event.nick is new_event.nick
    assert len(event) == 20
    assert len(new_event) == len(event)
