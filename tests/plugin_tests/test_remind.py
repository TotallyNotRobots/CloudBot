import datetime
import time
from contextlib import contextmanager
from unittest.mock import MagicMock, call

import pytest

from plugins import remind

second = datetime.timedelta(seconds=1)
minute = 60 * second
hour = 60 * minute


@pytest.fixture()
def setup_db(mock_db):
    remind.table.create(mock_db.engine)


async def async_call(func, *args):
    return func(*args)


async def make_reminder(text, nick, chan, mock_db, conn, event):
    return await remind.remind(
        text, nick, chan, mock_db.session(), conn, event, async_call
    )


@pytest.mark.asyncio()
async def test_invalid_reminder(mock_db, freeze_time, setup_db):
    await remind.load_cache(async_call, mock_db.session())
    mock_conn = MagicMock()
    mock_conn.name = "test"
    mock_event = MagicMock()

    result = await make_reminder(
        "1 day some reminder", "user", "#chan", mock_db, mock_conn, mock_event
    )

    assert mock_event.notice_doc.called

    assert not result

    assert mock_db.get_data(remind.table) == []


@pytest.mark.asyncio()
async def test_invalid_reminder_time(mock_db, freeze_time, setup_db):
    await remind.load_cache(async_call, mock_db.session())
    mock_conn = MagicMock()
    mock_conn.name = "test"
    mock_event = MagicMock()

    result = await make_reminder(
        "0 days: some reminder", "user", "#chan", mock_db, mock_conn, mock_event
    )

    assert result == "Invalid input."

    assert mock_db.get_data(remind.table) == []


@pytest.mark.asyncio()
async def test_invalid_reminder_overtime(mock_db, freeze_time, setup_db):
    await remind.load_cache(async_call, mock_db.session())
    mock_conn = MagicMock()
    mock_conn.name = "test"
    mock_event = MagicMock()

    result = await make_reminder(
        "6 weeks: some reminder",
        "user",
        "#chan",
        mock_db,
        mock_conn,
        mock_event,
    )

    expected = "Sorry, remind input must be more than a minute, and less than one month."

    assert result == expected

    assert mock_db.get_data(remind.table) == []


@pytest.mark.asyncio()
async def test_add_reminder(mock_db, freeze_time, setup_db):
    await remind.load_cache(async_call, mock_db.session())
    mock_conn = MagicMock()
    mock_conn.name = "test"
    mock_event = MagicMock()

    now = datetime.datetime.fromtimestamp(time.time())
    remind_time = now + (2.5 * hour)
    result = await make_reminder(
        "2 hours, 30 minutes: some reminder",
        "user",
        "#chan",
        mock_db,
        mock_conn,
        mock_event,
    )

    expected = 'Alright, I\'ll remind you "some reminder" in \x022 hours and 30 minutes\x0F!'

    assert result == expected

    assert mock_db.get_data(remind.table) == [
        ("test", "user", now, "#chan", "some reminder", remind_time)
    ]


@pytest.mark.asyncio()
async def test_add_reminder_fail_count(mock_db, freeze_time, setup_db):
    mock_conn = MagicMock()
    mock_conn.name = "test"
    mock_event = MagicMock()

    now = datetime.datetime.fromtimestamp(time.time())
    remind_time = now + (2.5 * hour)

    data = [
        (
            "test",
            "user",
            now + ((i + 1) * 2 * second),
            "#chan",
            "a reminder",
            remind_time,
        )
        for i in range(11)
    ]

    for row in data:
        mock_db.add_row(
            remind.table,
            network=row[0],
            added_user=row[1],
            added_time=row[2],
            added_chan=row[3],
            message=row[4],
            remind_time=row[5],
        )

    await remind.load_cache(async_call, mock_db.session())

    result = await make_reminder(
        "2 hours, 30 minutes: some reminder",
        "user",
        "#chan",
        mock_db,
        mock_conn,
        mock_event,
    )

    expected = (
        "Sorry, you already have too many reminders queued (10), "
        "you will need to wait or clear your reminders to add any more."
    )

    assert result == expected

    assert mock_db.get_data(remind.table) == data


class TestCheckReminders:
    delay = second * 0

    @contextmanager
    def set_delay(self, n):
        old = self.delay
        self.delay = n
        try:
            yield
        finally:
            self.delay = old

    @property
    def now(self):
        return datetime.datetime.now()

    @property
    def set_time(self):
        return self.now - hour

    @property
    def remind_time(self):
        return (self.now - (5 * minute)) - self.delay

    async def check_reminders(self, mock_db, bot):
        mock_db.add_row(
            remind.table,
            network="test",
            added_user="user",
            added_time=self.set_time,
            added_chan="#chan",
            message="a reminder",
            remind_time=self.remind_time,
        )
        await remind.load_cache(async_call, mock_db.session())
        await remind.check_reminders(bot, async_call, mock_db.session())

    @pytest.mark.asyncio()
    async def test_no_conn(
        self,
        mock_bot_factory,
        mock_db,
        setup_db,
        freeze_time,
        event_loop,
    ):
        await remind.load_cache(async_call, mock_db.session())
        bot = mock_bot_factory(loop=event_loop)
        bot.connections = {}
        mock_conn = MagicMock()
        mock_conn.name = "test"
        mock_conn.ready = True

        await self.check_reminders(mock_db, bot)

        assert mock_conn.message.mock_calls == []

        assert mock_db.get_data(remind.table) == [
            (
                "test",
                "user",
                self.set_time,
                "#chan",
                "a reminder",
                self.remind_time,
            )
        ]

    @pytest.mark.asyncio()
    async def test_conn_not_ready(
        self,
        mock_bot_factory,
        mock_db,
        setup_db,
        freeze_time,
        event_loop,
    ):
        await remind.load_cache(async_call, mock_db.session())
        bot = mock_bot_factory(loop=event_loop)
        mock_conn = MagicMock()
        mock_conn.name = "test"
        mock_conn.ready = False
        bot.connections = {mock_conn.name: mock_conn}

        await self.check_reminders(mock_db, bot)

        assert mock_conn.message.mock_calls == []

        assert mock_db.get_data(remind.table) == [
            (
                "test",
                "user",
                self.set_time,
                "#chan",
                "a reminder",
                self.remind_time,
            )
        ]

    @pytest.mark.asyncio()
    async def test_late(
        self,
        mock_bot_factory,
        mock_db,
        setup_db,
        freeze_time,
        event_loop,
    ):
        await remind.load_cache(async_call, mock_db.session())
        bot = mock_bot_factory(loop=event_loop)
        mock_conn = MagicMock()
        mock_conn.name = "test"
        mock_conn.ready = True
        bot.connections = {mock_conn.name: mock_conn}

        with self.set_delay(40 * minute):
            await self.check_reminders(mock_db, bot)

        assert mock_conn.message.mock_calls == [
            call(
                "user", "user, you have a reminder from \x0260 minutes\x0f ago!"
            ),
            call("user", '"a reminder"'),
            call(
                "user",
                "(I'm sorry for delivering this message \x0245 minutes\x0f late, "
                "it seems I was unable to deliver it on time)",
            ),
        ]

        assert mock_db.get_data(remind.table) == []

    @pytest.mark.asyncio()
    async def test_normal(
        self,
        mock_bot_factory,
        mock_db,
        setup_db,
        freeze_time,
        event_loop,
    ):
        await remind.load_cache(async_call, mock_db.session())
        bot = mock_bot_factory(loop=event_loop)
        mock_conn = MagicMock()
        mock_conn.name = "test"
        mock_conn.ready = True
        bot.connections = {mock_conn.name: mock_conn}

        await self.check_reminders(mock_db, bot)

        assert mock_conn.message.mock_calls == [
            call(
                "user", "user, you have a reminder from \x0260 minutes\x0f ago!"
            ),
            call("user", '"a reminder"'),
        ]

        assert mock_db.get_data(remind.table) == []


@pytest.mark.asyncio()
async def test_clear_reminders(mock_db, setup_db):
    now = datetime.datetime.now()

    mock_db.add_row(
        remind.table,
        network="test",
        added_user="user",
        added_time=now,
        added_chan="#chan",
        message="a reminder",
        remind_time=now + (2 * hour),
    )

    assert len(mock_db.get_data(remind.table)) == 1

    await remind.load_cache(async_call, mock_db.session())

    mock_conn = MagicMock()
    mock_conn.name = "test"

    mock_event = MagicMock()

    result = await remind.remind(
        "clear",
        "user",
        "#chan",
        mock_db.session(),
        mock_conn,
        mock_event,
        async_call,
    )

    assert result == "Deleted all (1) reminders for user!"

    assert mock_db.get_data(remind.table) == []


@pytest.mark.asyncio()
async def test_clear_reminders_empty(mock_db):
    remind.table.create(mock_db.engine, checkfirst=True)
    assert mock_db.get_data(remind.table) == []

    await remind.load_cache(async_call, mock_db.session())

    mock_conn = MagicMock()
    mock_conn.name = "test"

    mock_event = MagicMock()

    result = await remind.remind(
        "clear",
        "user",
        "#chan",
        mock_db.session(),
        mock_conn,
        mock_event,
        async_call,
    )

    assert result == "You have no reminders to delete."

    assert mock_db.get_data(remind.table) == []
