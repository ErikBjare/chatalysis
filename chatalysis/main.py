import logging
import textwrap

from collections import defaultdict
from typing import List, Any, Tuple, Dict
from itertools import groupby

import click
from tabulate import tabulate

from .models import Message, Writerstats
from .util import (
    _calculate_streak,
    _format_emojicount,
    _most_used_emoji,
    _convo_participants_key_undir,
    _filter_author,
)
from .load import _load_all_messages, _load_convos

logger = logging.getLogger(__name__)


@click.group()
def main():
    # memory.clear()
    logging.basicConfig(level=logging.DEBUG)


@main.command()
@click.argument("glob", default="*")
@click.option("--user")
def daily(glob: str, user: str = None) -> None:
    """Your messaging stats, by date"""
    msgs = _load_all_messages(glob)
    if user:
        msgs = _filter_author(msgs, user)
    _daily_messaging_stats(msgs)


@main.command()
@click.argument("glob", default="*")
@click.option("--user")
def yearly(glob: str, user: str = None) -> None:
    """Your messaging stats, by year"""
    msgs = _load_all_messages(glob)
    if user:
        msgs = _filter_author(msgs, user)
    _yearly_messaging_stats(msgs)


@main.command()
@click.argument("glob", default="*")
def top_writers(glob: str) -> None:
    """List the top writers"""
    msgs = _load_all_messages(glob)
    _top_writers(msgs)


@main.command()
@click.option("--user")
@click.option("--contains")
def messages(user: str = None, contains: str = None) -> None:
    """List messages, filter by user or content."""
    msgs = _load_all_messages()
    if user:
        msgs = [msg for msg in msgs if user.lower() in msg.from_name.lower()]
    if contains:
        msgs = [msg for msg in msgs if contains.lower() in msg.content.lower()]
    msgs = sorted(msgs, key=lambda m: m.timestamp)
    for msg in msgs:
        msg.print()


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

    wrapper = textwrap.TextWrapper(max_lines=1, width=30, placeholder="...")
    data = [
        (
            wrapper.fill(convo.title),
            len(convo.participants),
            len(convo.messages),
        )
        for convo in convos
    ]

    data = sorted(data, key=lambda t: t[2])
    print(tabulate(data, headers=["name", "members", "messages"]))


@main.command()
@click.argument("glob", default="*")
def most_reacted(glob: str) -> None:
    """List the most reacted messages"""
    msgs = _load_all_messages(glob)
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

        # includes participants who've left the chat
        all_participants = set(convo.participants) | set(messages_by_user.keys())
        print(f"# {convo.title}\n")
        stats = [
            (part, messages_by_user[part], reacts_by_user[part])
            for part in all_participants
        ]
        stats = list(reversed(sorted(stats, key=lambda t: (t[1], t[2]))))
        print(
            tabulate(
                stats,
                headers=["name", "messages", "reacts"],
            )
        )

        print("\nNo engagement from: " + ", ".join(sorted(fullcreeps)))
        print()


def _most_reacted_msgs(msgs):
    msgs = filter(lambda m: m.reactions, msgs)
    msgs = sorted(msgs, key=lambda m: -len(m.reactions))
    for msg in msgs[:30]:
        msg.print()


def _yearly_messaging_stats(msgs: list[Message]):
    print(f"All-time messages sent: {len(msgs)}")

    msgs_by_date = defaultdict(list)
    for msg in msgs:
        msgs_by_date[msg.timestamp.year].append(msg)

    rows = [
        (
            year,
            len(msgs),
            sum(len(m.content.split(" ")) for m in msgs),  # words
            sum(len(m.content) for m in msgs),  # chars
        )
        for year, msgs in sorted(msgs_by_date.items())
        if msgs
    ]

    print(tabulate(rows, headers=["year", "# msgs", "words", "chars"]))


def _daily_messaging_stats(msgs: list[Message]):
    print(f"All-time messages sent: {len(msgs)}")

    msgs_by_date = defaultdict(list)
    for msg in msgs:
        msgs_by_date[msg.timestamp.date()].append(msg)

    rows = [
        (
            d,
            len(msgs),
            sum(len(m.content.split(" ")) for m in msgs),  # words
            sum(len(m.content) for m in msgs),  # chars
        )
        for d, msgs in sorted(msgs_by_date.items())
        if msgs
    ]

    print(tabulate(rows, headers=["year", "# msgs", "words", "chars"]))


def _writerstats(msgs: list[Message]) -> dict[str, Writerstats]:
    writerstats: dict[str, Writerstats] = defaultdict(lambda: Writerstats())
    for msg in msgs:
        # if msg.data["groupchat"]:
        #     continue
        s = writerstats[msg.from_name]
        s.days |= {msg.timestamp.date()}
        s.msgs += 1
        s.words += len(msg.content.split(" "))
        for react in msg.reactions:
            # TODO: Save which reacts the writer used (with Counter?)
            s.reacts_recv += 1  # [react]
            writerstats[react["actor"]].reacts_sent += 1  # [react]

    return writerstats


def _top_writers(msgs: list[Message]):
    writerstats = _writerstats(msgs)
    writerstats = dict(
        sorted(writerstats.items(), key=lambda kv: kv[1].msgs, reverse=True)
    )

    wrapper = textwrap.TextWrapper(max_lines=1, width=30, placeholder="...")
    print(
        tabulate(
            [
                (
                    wrapper.fill(writer),
                    stats.msgs,
                    len(stats.days),
                    stats.words,
                    stats.reacts_sent,
                    stats.reacts_recv,
                    round(
                        1000 * (stats.reacts_recv / stats.words) if stats.words else 0,
                    ),
                )
                for writer, stats in writerstats.items()
            ],
            headers=[
                "name",
                "msgs",
                "days",
                "words",
                "reacts sent",
                "reacts recv",
                "reacts/1k words",
            ],
        )
    )


def _people_stats(msgs: List[Message]) -> None:
    grouped = groupby(
        sorted(msgs, key=_convo_participants_key_undir),
        key=_convo_participants_key_undir,
    )
    rows = []
    for k, _v in grouped:
        v = list(_v)
        days = {m.timestamp.date() for m in v}
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


def _connections(msgs: List[Message]) -> Dict[Tuple[str, str], int]:
    connections: Dict[Tuple[str, str], int] = defaultdict(int)
    for msg in msgs:
        if msg.data["groupchat"]:
            continue
        connections[(msg.from_name, msg.to_name)] += 1
    return connections


@main.command()
@click.option("--csv", "-c", is_flag=True)
def connections(csv: bool) -> None:
    """
    List all connections between interacting people, assigning weights as per the number of messages they have exchanged.
    """
    # TODO: Also count reply-messages and immediately-following messages in groupchats
    msgs = _load_all_messages()
    connections = _connections(msgs)
    if csv:
        print(",".join(["from", "to", "count"]))
        for k, v in sorted(connections.items(), key=lambda kv: kv[1], reverse=True):
            print(",".join(map(str, k + (v,))))
    else:
        print(tabulate(sorted(connections.items()), headers=["from", "to", "count"]))


if __name__ == "__main__":
    main()
