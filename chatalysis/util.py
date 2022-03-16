import re
from typing import List, Dict, Iterator, Counter as TCounter
from datetime import timedelta, date
from itertools import groupby
from collections import Counter, defaultdict

from .models import Message

# Idk how this works, but it does
# https://stackoverflow.com/a/26740753/965332
re_emoji = re.compile(
    "[\U00002600-\U000027BF]|[\U0001f300-\U0001f64F]|[\U0001f680-\U0001f6FF]"
)


def _calculate_streak(days) -> int:
    days = sorted(days)
    last_day = None
    curr_streak = 0
    longest_streak = 0
    for day in days:
        if last_day:
            if last_day == day - timedelta(days=1):
                curr_streak += 1
                if curr_streak > longest_streak:
                    longest_streak = curr_streak
            else:
                curr_streak = 0
        last_day = day
    return longest_streak


def _count_emoji(txt: str) -> Dict[str, int]:
    return {k: len(list(v)) for k, v in groupby(sorted(re_emoji.findall(txt)))}


def _format_emojicount(emojicount: Dict[str, int]):
    return ", ".join(
        f"{n}x {emoji}"
        for n, emoji in reversed(sorted((v, k) for k, v in emojicount.items()))
    )


def test_count_emoji() -> None:
    # assert _count_emoji("\u00e2\u009d\u00a4") == {"\u00e2\u009d\u00a4": 1}
    assert _count_emoji("👍👍😋😋❤") == {"👍": 2, "😋": 2, "❤": 1}
    assert _format_emojicount(_count_emoji("👍👍😋😋❤")) == "2x 😋, 2x 👍, 1x ❤"


def _most_used_emoji(msgs: Iterator[str]) -> Counter:
    c: TCounter[str] = Counter()
    for m in msgs:
        c += Counter(_count_emoji(m))
    return c


def _convo_participants_key_dir(m: Message) -> str:
    # Preserves message direction
    return f'{m.from_name} -> {m.to_name}'


def _convo_participants_key_undir(m: Message) -> str:
    # Disregards message direction
    return " <-> ".join(sorted((m.to_name, m.from_name)))


def _calendar(msgs: List[Message]) -> Dict[date, List[Message]]:
    def datekey(m: Message):
        return m.timestamp.date()

    grouped = groupby(sorted(msgs, key=datekey), key=datekey)
    msgs_per_date: Dict[date, List[Message]] = defaultdict(list)
    msgs_per_date.update({k: list(v) for k, v in grouped})
    return msgs_per_date


def _filter_author(msgs: list[Message], name: str) -> list[Message]:
    return [m for m in msgs if name in m.from_name]


def _active_days(msgs: list[Message]) -> set[date]:
    return {m.timestamp.date() for m in msgs}
