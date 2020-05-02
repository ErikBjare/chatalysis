from datetime import datetime, timedelta, date
from pathlib import Path
from collections import Counter, defaultdict
import logging
import re
import json
import typing
from typing import List, Dict, Iterator, Optional
from itertools import groupby
import textwrap
from dataclasses import dataclass, field

from joblib import Memory
from tabulate import tabulate

logger = logging.getLogger(__name__)


@dataclass
class Message:
    from_name: str
    to_name: str
    date: datetime
    content: str
    reactions: List[dict] = field(default_factory=list)
    data: dict = field(default_factory=dict)


cache_location = "./.message_cache"
memory = Memory(cache_location, verbose=0)

me = "Erik Bjäreholt"

# Idk how this works, but it does
# https://stackoverflow.com/a/26740753/965332
re_emoji = re.compile(
    "[\U00002600-\U000027BF]|[\U0001f300-\U0001f64F]|[\U0001f680-\U0001f6FF]"
)


def main() -> None:
    # memory.clear()
    msgs = _parse_all_messages()
    msgs = [msg for msg in msgs if msg.to_name == "Peace Club Dropouts"]

    top_writers(msgs)
    _yearly_messaging_stats(msgs, me)
    _people_stats(msgs)
    _most_reacted_msgs(msgs)


def _most_reacted_msgs(msgs):
    msgs = filter(lambda m: m.reactions, msgs)
    msgs = sorted(msgs, key=lambda m: -len(m.reactions))
    for m in msgs[:30]:
        _print_msg(m)


def _yearly_messaging_stats(msgs, name):
    my_msgs = [m for m in msgs if name in m.from_name]
    print(f"Messages sent by me: {len(my_msgs)}")
    rows = []
    for year in range(2006, 2019):
        year_msgs = [m for m in my_msgs if m.date.year == year]
        if not year_msgs:
            continue
        rows.append(
            (
                year,
                len(year_msgs),
                sum(len(m.content.split(" ")) for m in year_msgs),  # words
                sum(len(m.content) for m in year_msgs),  # chars
            )
        )
    print(tabulate(rows, headers=["year", "# msgs", "words", "chars"]))


def top_writers(msgs):
    writerstats = defaultdict(lambda: Counter())
    for msg in msgs:
        if msg.data.get("groupchat", False):
            continue
        s = writerstats[msg.from_name]
        if "days" not in s:
            s["days"] = set()
        s["days"] = s.get("days", set()) | {msg.date.date()}
        s["msgs"] += 1
        s["words"] += len(msg.content.split(" "))
    writerstats = dict(
        sorted(writerstats.items(), key=lambda kv: kv[1]["msgs"], reverse=True)
    )

    wrapper = textwrap.TextWrapper(max_lines=1, width=30, placeholder="...")
    print(
        tabulate(
            [
                (wrapper.fill(k), v["msgs"], len(v["days"]), v["words"])
                for k, v in writerstats.items()
            ],
            headers=["name", "msgs", "days", "words"],
        )
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
    assert _count_emoji("\u00e2\u009d\u00a4") == {"\u00e2\u009d\u00a4": 1}
    assert _count_emoji("👍👍😋😋❤") == {"👍": 2, "😋": 2, "❤": 1}
    assert _format_emojicount(_count_emoji("👍👍😋😋❤")) == "2x 😋, 2x 👍, 1x ❤"


def _most_used_emoji(msgs: Iterator[str]) -> Counter:
    c: typing.Counter[str] = Counter()
    for m in msgs:
        c += Counter(_count_emoji(m))
    return c


def _convo_participants_key_dir(m: Message) -> str:
    # Preserves message direction
    return m.from_name + " -> " + m.to_name


def _convo_participants_key_undir(m: Message) -> str:
    # Disregards message direction
    return " <-> ".join(sorted((m.to_name, m.from_name)))


def _calendar(msgs: List[Message]) -> Dict[date, List[Message]]:
    def datekey(m: Message):
        return m.date.date()

    grouped = groupby(sorted(msgs, key=datekey), key=datekey)
    msgs_per_date: Dict[date, List[Message]] = defaultdict(list)
    msgs_per_date.update({k: list(v) for k, v in grouped})
    return msgs_per_date


def _people_stats(msgs: List[Message]) -> None:
    grouped = groupby(
        sorted(msgs, key=_convo_participants_key_undir),
        key=_convo_participants_key_undir,
    )
    rows = []
    for k, _v in grouped:
        v = list(_v)
        days = {m.date.date() for m in v}
        rows.append(
            (
                k[:40],
                len(v),
                len(days),
                _calculate_streak(days),
                _format_emojicount(
                    dict(_most_used_emoji(m.content for m in v).most_common()[:5])
                ),
            )
        )
    print(tabulate(rows, headers=["k", "days", "max streak", "most used emoji"]))


def _get_all_chat_files(glob="*"):
    msgdir = Path("data/messages/inbox")
    return sorted(list(msgdir.glob(f"{glob}/message*.json")))


def _list_all_chats():
    conversations = _get_all_chat_files()
    for chat in conversations:
        with open(chat) as f:
            data = json.load(f)
            print(data["title"])


def _parse_all_messages(glob: str = "*") -> List[Message]:
    messages = [
        msg
        for filename in _get_all_chat_files(glob)
        for msg in _parse_messages(filename)
    ]
    logger.info(f"Parsed {len(messages)} messages")
    return messages


@memory.cache
def _parse_messages(filename: str) -> List[Message]:
    messages = []
    with open(filename) as f:
        data = json.load(f)
        title = data["title"]
        participants = data["participants"]
        thread_type = data[
            "thread_type"
        ]  # Can be one of at least: Regular, RegularGroup
        is_groupchat = thread_type == "RegularGroup"

        for msg in data["messages"]:
            if "content" not in msg:
                logger.info(f"Skipping non-text message: {msg}")
                continue

            sender = msg["sender_name"]
            receiver = me if not is_groupchat and sender != me else title
            text = msg["content"]
            reacts: List[dict] = msg.get("reactions", [])
            date = datetime.fromtimestamp(msg["timestamp_ms"] / 1000)

            messages.append(
                Message(
                    sender,
                    receiver,
                    date,
                    text,
                    reactions=reacts,
                    data={"groupchat": is_groupchat},
                )
            )
    return messages


def _print_msg(msg: Message) -> None:
    emojicount_str = _format_emojicount(
        _count_emoji("".join(d["reaction"] for d in msg.reactions))
    )
    print(
        f"{msg.date.isoformat()[:10]} | {msg.from_name} -> {msg.to_name}: {msg.content}  ({emojicount_str})"
    )


if __name__ == "__main__":
    logging.basicConfig()
    main()
