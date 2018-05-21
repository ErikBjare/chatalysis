from datetime import datetime, timedelta, date
from pathlib import Path
from collections import namedtuple, Counter, defaultdict
import logging
import re
import typing
from typing import List, Dict, Iterator
from itertools import groupby

import bs4

log = logging.getLogger(__name__)
Message = namedtuple("Message", ["from_name", "to_name", "date", "content"])

me = "Erik Bjäreholt"

# Idk how this works, but it does
# https://stackoverflow.com/a/26740753/965332
re_emoji = re.compile(u'[\U00002600-\U000027BF]|[\U0001f300-\U0001f64F]|[\U0001f680-\U0001f6FF]')


def main() -> None:
    msgs = _parse_messages()
    _print_msg(msgs[0])
    my_msgs = [m for m in msgs if me in m.from_name]
    print(f"Messages sent by me: {len(my_msgs)}")
    for year in range(2006, 2019):
        year_msgs = [m for m in my_msgs if m.date.year == year]
        if not year_msgs:
            continue
        words = sum(len(m.content.split(" ")) for m in year_msgs)
        chars = sum(len(m.content) for m in year_msgs)
        print(f"During {year} {len(year_msgs)} msgs were sent using {words} words and {chars} chars")
        print(f" - avg of {round(words/len(year_msgs), 1)} words per msg")
        print(f" - avg of {round(chars/len(year_msgs), 1)} chars per msg")

    _people_stats(msgs)


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


def test_count_emoji() -> None:
    assert _count_emoji("👍👍😋😋❤") == {"👍": 2, "😋": 2, "❤": 1}


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
    grouped = groupby(sorted(msgs, key=_convo_participants_key_undir), key=_convo_participants_key_undir)
    for k, _v in grouped:
        v = list(_v)
        days = {m.date.date() for m in v}
        print(f"{k}: {len(v)} messages on {len(days)} days")
        print(f" - longest streak is {_calculate_streak(days)}")
        print(f" - most used emojis: {_most_used_emoji(m.content for m in v).most_common()[:10]}")


def _parse_messages(glob: str = '*') -> List[Message]:
    messages = []
    msgdir = Path("data/private/messages")
    for chat in msgdir.glob(f"{glob}/message.html"):
        with open(chat) as f:
            data = f.read()
            soup = bs4.BeautifulSoup(data, "lxml")
            other = soup.title.text
            for msg in soup.select("div[role='main']")[0]:
                try:
                    sub = msg.find_all("div")
                    pfrom = sub[0].text
                    pto = me if pfrom != me else other
                    text = sub[1].text
                    datestr = sub[7].text
                    date = datetime.strptime(datestr, "%b %d, %Y %I:%M%p")
                    if "You are now connected" in text:
                        continue
                    messages.append(Message(pfrom, pto, date, text))
                except IndexError as e:
                    log.warning(f"Unable to parse: {e}")
                except ValueError as e:
                    log.warning(f"Unable to parse: {e}")

    log.info(f"Parsed {len(messages)} messages")
    return messages


def _print_msg(msg: Message) -> None:
    print(f"{msg.from_name} -> {msg.to_name}: {msg.content}   ({msg.date.isoformat()})")


if __name__ == "__main__":
    logging.basicConfig()
    main()
