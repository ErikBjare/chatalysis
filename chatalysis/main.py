import logging
import re
import json
import typing
import textwrap

from datetime import datetime, timedelta, date
from pathlib import Path
from collections import Counter, defaultdict
from typing import List, Dict, Iterator, Any
from itertools import groupby
from dataclasses import dataclass, field

import click
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


@dataclass
class Conversation:
    title: str
    participants: list[str]
    messages: list[Message]
    data: dict

    def merge(self, c2: "Conversation") -> "Conversation":
        assert self.title == c2.title
        assert self.participants == c2.participants
        return Conversation(
            title=self.title,
            participants=self.participants,
            messages=sorted(self.messages + c2.messages, key=lambda m: m.date),
            data=self.data,
        )


cache_location = "./.message_cache"
memory = Memory(cache_location, verbose=0)

me = "Erik Bj"

# Idk how this works, but it does
# https://stackoverflow.com/a/26740753/965332
re_emoji = re.compile(
    "[\U00002600-\U000027BF]|[\U0001f300-\U0001f64F]|[\U0001f680-\U0001f6FF]"
)


@click.group()
def main():
    # memory.clear()
    logging.basicConfig(level=logging.INFO)
    pass


@main.command()
def daily() -> None:
    """Your messaging stats, by date"""
    msgs = _load_all_messages()
    _daily_messaging_stats(msgs, me)


@main.command()
def yearly() -> None:
    """Your messaging stats, by year"""
    msgs = _load_all_messages()
    _yearly_messaging_stats(msgs, me)


@main.command()
@click.argument("glob", default="*")
def top_writers(glob: str) -> None:
    """List the top writers"""
    msgs = _load_all_messages(glob)
    _top_writers(msgs)


@main.command()
def people() -> None:
    """List all people"""
    msgs = _load_all_messages()
    _people_stats(msgs)


@main.command()
@click.argument("glob", default="*")
def convos(glob: str) -> None:
    """List all conversations (groups and 1-1s)"""
    convos = _load_convos(glob)

    data = []
    for convo in convos:
        data.append((convo.title, len(convo.participants), len(convo.messages)))
    print(tabulate(data, headers=["name", "members", "messages"]))


@main.command()
def most_reacted() -> None:
    """List the most reacted messages"""
    msgs = _load_all_messages()
    _most_reacted_msgs(msgs)


@main.command()
@click.argument("glob", default="*")
def creeps(glob: str) -> None:
    """
    List creeping participants (who have minimal or no engagement)

    Note: this is perhaps easier using same output as from top-writers, but taking the bottom instead

    """
    convos = _load_convos(glob)

    for convo in convos:
        if not convo.data["groupchat"]:
            continue

        messages_by_user: dict[str, int] = defaultdict(int)
        reacts_by_user: dict[str, int] = defaultdict(int)
        for message in convo.messages:
            messages_by_user[message.from_name] += 1
            for react in message.reactions:
                actor = react["actor"]
                reacts_by_user[actor] += 1

        fullcreeps = set(convo.participants) - (
            set(messages_by_user.keys()) | set(reacts_by_user.keys())
        )

        stats = [
            (part, messages_by_user[part], reacts_by_user[part])
            for part in set(convo.participants)
        ]
        stats = sorted(stats, key=lambda t: t[1])
        print(
            tabulate(
                stats,
                headers=["name", "messages", "reacts"],
            )
        )

        print("No engagement from: " + ", ".join(sorted(fullcreeps)))


def _most_reacted_msgs(msgs):
    msgs = filter(lambda m: m.reactions, msgs)
    msgs = sorted(msgs, key=lambda m: -len(m.reactions))
    for m in msgs[:30]:
        _print_msg(m)


def _yearly_messaging_stats(msgs, name):
    msgs = [m for m in msgs if name in m.from_name]
    print(f"Messages sent by me: {len(msgs)}")

    msgs_by_date = defaultdict(list)
    for msg in msgs:
        msgs_by_date[msg.date.year].append(msg)

    rows = []
    for year, msgs in sorted(msgs_by_date.items()):
        if not msgs:
            continue
        rows.append(
            (
                year,
                len(msgs),
                sum(len(m.content.split(" ")) for m in msgs),  # words
                sum(len(m.content) for m in msgs),  # chars
            )
        )
    print(tabulate(rows, headers=["year", "# msgs", "words", "chars"]))


def _daily_messaging_stats(msgs, name):
    msgs = [m for m in msgs if name in m.from_name]
    print(f"Messages sent by me: {len(msgs)}")

    msgs_by_date = defaultdict(list)
    for msg in msgs:
        msgs_by_date[msg.date.date()].append(msg)

    rows = []
    for d, msgs in sorted(msgs_by_date.items()):
        if not msgs:
            continue
        rows.append(
            (
                d,
                len(msgs),
                sum(len(m.content.split(" ")) for m in msgs),  # words
                sum(len(m.content) for m in msgs),  # chars
            )
        )
    print(tabulate(rows, headers=["year", "# msgs", "words", "chars"]))


def _top_writers(msgs):
    writerstats: dict[str, Any] = defaultdict(lambda: Counter())
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


def _get_all_conv_dirs():
    msgdir = Path("data/private/messages/inbox")
    return [path.parent for path in msgdir.glob("*/message_1.json")]


def _load_convo(convdir: Path) -> Conversation:
    chatfiles = convdir.glob("message_*.json")
    convo = None
    for file in chatfiles:
        if convo is None:
            convo = _parse_chatfile(file)
        else:
            convo = convo.merge(_parse_chatfile(file))
    assert convo is not None
    return convo


def _load_convos(glob="*"):
    logger.info("Loading conversations...")
    convos = [_load_convo(convdir) for convdir in _get_all_conv_dirs()]
    if glob != "*":
        convos = [convo for convo in convos if glob.lower() in convo.title.lower()]
    return convos


def _get_all_chat_files(glob="*"):
    msgdir = Path("data/private/messages/inbox")
    return sorted(
        [
            chatfile
            for convdir in _get_all_conv_dirs()
            for chatfile in msgdir.glob(f"{glob}/message*.json")
        ]
    )


def _list_all_chats():
    conversations = _get_all_chat_files()
    for chat in conversations:
        with open(chat) as f:
            data = json.load(f)
            print(data["title"])


def _load_all_messages(glob: str = "*") -> List[Message]:
    messages = [msg for convo in _load_convos(glob) for msg in convo.messages]
    logger.info(f"Loaded {len(messages)} messages")
    return messages


@memory.cache
def _parse_chatfile(filename: str) -> Conversation:
    # FIXME: This should open all `message_*.json` files and merge into a single convo
    messages = []
    with open(filename) as f:
        data = json.load(f)
        title = data["title"].encode("latin1").decode("utf8")
        participants: List[str] = [
            p["name"].encode("latin1").decode("utf8") for p in data["participants"]
        ]
        # print(participants)
        thread_type = data[
            "thread_type"
        ]  # Can be one of at least: Regular, RegularGroup
        is_groupchat = thread_type == "RegularGroup"

        for msg in data["messages"]:
            if "content" not in msg:
                logger.info(f"Skipping non-text message: {msg}")
                continue

            # the `.encode('latin1').decode('utf8')` hack is needed due to https://stackoverflow.com/a/50011987/965332
            sender = msg["sender_name"].encode("latin1").decode("utf8")
            text = msg["content"].encode("latin1").decode("utf8")
            reacts: List[dict] = msg.get("reactions", [])
            for react in reacts:
                react["reaction"] = react["reaction"].encode("latin1").decode("utf8")
                react["actor"] = react["actor"].encode("latin1").decode("utf8")

            # if reacts:
            #     print(f"R: {reacts}")

            receiver = me if not is_groupchat and sender != me else title
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

    return Conversation(
        title=title,
        participants=participants,
        messages=messages,
        data={"groupchat": is_groupchat},
    )


def _print_msg(msg: Message) -> None:
    emojicount_str = _format_emojicount(
        _count_emoji("".join(d["reaction"] for d in msg.reactions))
    )
    print(
        f"{msg.date.isoformat()[:10]} | {msg.from_name} -> {msg.to_name}: {msg.content}  ({emojicount_str})"
    )


if __name__ == "__main__":
    main()
