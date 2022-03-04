import datetime
import logging
from collections.abc import Sized
from enum import Enum
from functools import wraps
from typing import (
    Any,
    Container,
    Dict,
    Generic,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
    cast,
    overload,
)

import requests

from cloudbot import hook
from cloudbot.bot import CloudBot
from cloudbot.event import Event
from cloudbot.util import func_utils
from cloudbot.util.http import GetParams

logger = logging.getLogger(__name__)
token_lifetime = datetime.timedelta(hours=1)

JsonPrimitive = Union[int, str, bool, None]
JsonObject = Dict[
    str, Union[JsonPrimitive, List[JsonPrimitive], Dict[str, JsonPrimitive]]
]


class NoMatchingSeries(LookupError):
    pass


class TvdbApi:
    def __init__(self) -> None:
        self.token_lifetime = token_lifetime
        self._headers = None  # type: Optional[Dict[str, str]]
        self.base_url = "https://api.thetvdb.com"
        self.api_version = "3.0.0"
        self.default_headers = {
            "Accept": "application/vnd.thetvdb.v{}".format(self.api_version)
        }

        self.jwt_token = None  # type: Optional[str]
        self.refresh_time = datetime.datetime.min

    @property
    def authed(self) -> bool:
        return self.jwt_token is not None

    def set_api_key(self, bot: CloudBot) -> None:
        res = cast(
            Dict[str, str],
            self._post(
                "/login", json={"apikey": bot.config.get_api_key("tvdb")}
            ),
        )
        self.set_token(res["token"])

    def refresh_token(self, bot: CloudBot) -> None:
        if self.jwt_token is None:
            self.set_api_key(bot)
            return

        try:
            res = cast(Dict[str, str], self._get("/refresh_token"))
        except requests.HTTPError as e:
            if e.response.status_code == 401:
                self.set_api_key(bot)
            else:
                raise
        else:
            self.set_token(res["token"])

    def set_token(self, token: str) -> None:
        self.jwt_token = token
        self.refresh_time = datetime.datetime.now() + self.token_lifetime
        # Clear header cache
        self._headers = None

    def _get(self, path: str, params: Optional[GetParams] = None) -> JsonObject:
        with requests.get(
            self.base_url + path, headers=self.headers, params=params or {}
        ) as response:
            response.raise_for_status()
            return cast(JsonObject, response.json())

    def _get_paged(
        self,
        path: str,
        params: Optional[GetParams] = None,
        reverse: bool = False,
    ) -> Iterable[JsonObject]:
        params = params or {}
        params["page"] = 1
        first_page = self._get(path, params)
        links = cast(Dict[str, int], first_page.get("links", {}))
        last_num = links.get("last", 1)
        if last_num == 1:
            yield first_page
            return

        if reverse:
            page = last_num
        else:
            yield first_page
            page = 2

        while True:
            params["page"] = page
            res = self._get(path, params)
            yield res

            links = cast(Dict[str, int], res["links"])
            if reverse:
                if page == 2:
                    break

                page = links["previous"]
            else:
                if page == links["last"]:
                    break

                page = links["next"]

        if reverse:
            yield first_page

    def _post(self, path: str, json: Dict[str, Any]) -> JsonObject:
        with requests.post(
            self.base_url + path, headers=self.headers, json=json
        ) as response:
            response.raise_for_status()
            return cast(JsonObject, response.json())

    @property
    def headers(self) -> Dict[str, str]:
        if self._headers is not None:
            return self._headers

        self._headers = self.default_headers.copy()
        if self.jwt_token:
            self._headers["Authorization"] = "Bearer {}".format(self.jwt_token)

        return self._headers

    def find_series(self, name: str) -> List[JsonObject]:
        try:
            return cast(
                List[JsonObject],
                self._get("/search/series", params={"name": name})["data"],
            )
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                raise NoMatchingSeries(name) from e

            raise

    def get_episodes(
        self, series_id: str, reverse=True
    ) -> Iterable[JsonObject]:
        try:
            for page in self._get_paged(
                "/series/{id}/episodes".format(id=series_id), reverse=reverse
            ):
                data = cast(List[JsonObject], page["data"])
                if not reverse:
                    yield from data
                else:
                    yield from reversed(data)
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                # 404 means no episodes
                return

            raise


api = TvdbApi()


class MissingItem(Exception):
    pass


T = TypeVar("T")


class Holder(Generic[T]):
    """
    >>> holder = Holder()
    >>> holder.exists()
    False
    >>> holder.set(object())
    >>> holder.exists()
    True
    >>> holder.clear()
    >>> holder.exists()
    False
    """

    def __init__(self) -> None:
        self._item = None  # type: Optional[T]
        self._set = False

    def set(self, item: T) -> None:
        self._item = item
        self._set = True

    def clear(self) -> None:
        self._item = None
        self._set = False

    @classmethod
    def empty(cls) -> "Holder[T]":
        return cls()

    @classmethod
    def of(cls, item: T) -> "Holder[T]":
        obj = cls()
        obj.set(item)
        return obj

    @classmethod
    def of_optional(cls, item: Optional[T]) -> "Holder[T]":
        obj = cls()
        if item is not None:
            obj.set(item)

        return obj

    def exists(self) -> bool:
        return self._set

    def get(self) -> T:
        if not self._set:
            raise MissingItem()

        return self._item


class LazyCollection(Sized, Iterable[T], Container[T]):
    """
    >>> col = LazyCollection([1])
    >>> col[0:5]
    [1]
    >>> col = LazyCollection([1])
    >>> col[-1]
    1
    >>> col = LazyCollection([])
    >>> len(col)
    0
    >>> col = LazyCollection(['a'])
    >>> 'a' in col
    True
    >>> 'a' in col
    True
    >>> 'b' in col
    False
    >>> col[1]
    Traceback (most recent call last):
        ...
    IndexError: list index out of range
    """

    def __init__(self, it: Iterable[T]) -> None:
        self._data = []  # type: List[T]
        self._it = iter(it)
        self._complete = False

    def __len__(self) -> int:
        self._gen_all()
        return len(self._data)

    def _get_next(self) -> Holder[T]:
        try:
            item = next(self._it)
        except StopIteration:
            self._complete = True
            return Holder.empty()
        else:
            self._data.append(item)
            return Holder.of(item)

    def __iter__(self) -> Iterator[T]:
        yield from self._data
        while True:
            holder = self._get_next()
            if holder.exists():
                yield holder.get()
            else:
                break

    def __contains__(self, needle: object) -> bool:
        if needle in self._data:
            return True

        while True:
            holder = self._get_next()
            if not holder.exists():
                return False

            if holder.get() == needle:
                return True

    def _gen_to_index(self, i: int) -> None:
        current_size = len(self._data)
        if i >= current_size:
            for _ in range((i - current_size) + 1):
                try:
                    self._data.append(next(self._it))
                except StopIteration:
                    return

    def _gen_all(self) -> None:
        self._data.extend(self._it)
        self._complete = True

    def _gen_bounds(self, i: int) -> None:
        if self._complete:
            return

        if i < 0:
            self._gen_all()
        else:
            self._gen_to_index(i)

    @overload
    def __getitem__(self, item: int) -> T:
        ...

    @overload
    def __getitem__(self, item: slice) -> List[T]:
        ...

    def __getitem__(self, item: Union[int, slice]) -> Union[T, List[T]]:
        if isinstance(item, slice):
            self._gen_bounds(item.start)
            self._gen_bounds(item.stop)
        else:
            self._gen_bounds(item)

        return self._data[item]


class EpisodeInfo:
    def __init__(
        self,
        first_aired: Optional[datetime.date],
        episode_number: int,
        season: int,
        name: Optional[str],
    ) -> None:
        self.episode_number = episode_number
        self.season = season
        self.first_aired = first_aired
        self.name = name

    @classmethod
    def from_json(cls, json: Dict[str, Any]) -> "EpisodeInfo":
        first_aired = json.get("firstAired")
        if not first_aired:
            air_date = None
        else:
            air_date = datetime.datetime.strptime(
                first_aired, "%Y-%m-%d"
            ).date()

        episode_number = json["airedEpisodeNumber"]
        season = json["airedSeason"]

        name = json.get("episodeName")
        if name == "TBA":
            name = None

        return cls(
            first_aired=air_date,
            episode_number=episode_number,
            season=season,
            name=name,
        )

    @property
    def full_number(self) -> str:
        return "S{:02d}E{:02d}".format(self.season, self.episode_number)

    @property
    def description(self) -> str:
        episode_desc = "{}".format(self.full_number)
        if self.name:
            episode_desc += " - {}".format(self.name)

        return episode_desc


class Status(Enum):
    ENDED = "Ended"
    CONTINUING = "Continuing"
    UPCOMING = "Upcoming"


class SeriesInfo:
    def __init__(
        self, name: str, episodes: Iterable[Dict[str, Any]], status: Status
    ) -> None:
        self.name = name
        self.episodes = LazyCollection(map(EpisodeInfo.from_json, episodes))
        self.status = status

    @property
    def ended(self) -> bool:
        return self.status is Status.ENDED


def get_episodes_for_series(series_name: str) -> SeriesInfo:
    search_results = api.find_series(series_name)
    series = search_results[0]
    status = Status(series["status"])

    episodes = api.get_episodes(cast(str, series["id"]))

    return SeriesInfo(cast(str, series["seriesName"]), episodes, status)


def check_and_get_series(
    series: str,
) -> Union[Tuple[SeriesInfo, None], Tuple[None, str]]:
    if not api.authed:
        return None, "TVDB API not enabled."

    try:
        return get_episodes_for_series(series), None
    except NoMatchingSeries:
        return None, "Unable to find series"


def handle_error(event: Event, error):
    event.reply("Failed to contact thetvdb.com")
    raise error


def _error_handler(exc_type, handler):
    def decorator(f):
        @wraps(f)
        def func(event):
            try:
                return func_utils.call_with_args(f, event)
            except exc_type as e:
                return handler(event, e)

        return func

    return decorator


@hook.on_start()
@hook.periodic(token_lifetime.total_seconds())
def refresh(bot: CloudBot) -> None:
    api.refresh_token(bot)


@hook.command("tv_next", "tv")
@_error_handler(requests.HTTPError, handle_error)
def tv_next(text: str) -> str:
    """<series> - Get the next episode of <series>."""
    series, err = check_and_get_series(text)
    if err is not None:
        return err

    if series.ended:
        return "{} has ended.".format(series.name)

    next_eps = []
    today = datetime.date.today()

    for episode in series.episodes:
        if episode.first_aired is not None and episode.first_aired < today:
            break

        if episode.first_aired is None:
            date_str = "TBA"
        elif episode.first_aired == today:
            date_str = "Today"
        else:
            date_str = str(episode.first_aired)

        next_eps.append("{} ({})".format(date_str, episode.description))

    if not next_eps:
        return "There are no new episodes scheduled for {}.".format(series.name)

    if len(next_eps) == 1:
        return "The next episode of {} airs {}".format(series.name, next_eps[0])

    return "The next episodes of {}: {}".format(
        series.name, ", ".join(reversed(next_eps))
    )


@hook.command("tv_last", "tv_prev")
@_error_handler(requests.HTTPError, handle_error)
def tv_last(text: str) -> str:
    """<series> - Gets the most recently aired episode of <series>."""
    series, err = check_and_get_series(text)
    if err is not None:
        return err

    prev_ep = None
    today = datetime.date.today()

    for episode in series.episodes:
        if episode.first_aired is None:
            continue

        if episode.first_aired < today:
            prev_ep = "{} ({})".format(episode.first_aired, episode.description)
            break

    if not prev_ep:
        return "There are no previously aired episodes for {}.".format(
            series.name
        )

    if series.ended:
        return "{} ended. The last episode aired {}.".format(
            series.name, prev_ep
        )

    return "The last episode of {} aired {}.".format(series.name, prev_ep)
