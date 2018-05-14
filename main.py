from datetime import datetime
from pathlib import Path
from collections import namedtuple
import logging
from typing import List
from itertools import groupby

import bs4

log = logging.getLogger(__name__)
Message = namedtuple("Message", ["from_name", "to_name", "date", "content"])

me = "Erik Bjäreholt"


def main():
    msgs = _parse_messages()
    _print_msg(msgs[0])
    my_msgs = [m for m in msgs if me in m.from_name]
    print(f"Messages sent by me: {len(my_msgs)}")
    for year in range(2008, 2019):
        year_msgs = [m for m in my_msgs if m.date.year == year]
        words = sum(len(m.content.split(" ")) for m in year_msgs)
        chars = sum(len(m.content) for m in year_msgs)
        print(f"During {year} {len(year_msgs)} msgs were sent using {words} words and {chars} chars")
        print(f" - avg of {round(words/len(year_msgs), 1)} words per msg")
        print(f" - avg of {round(chars/len(year_msgs), 1)} chars per msg")


def _people_stats(msgs):
    # people = {m.from_name for m in msgs} | {m.to_name for m in msgs}
    # print(people)

    def key(m):
        return m.from_name + " -> " + m.to_name

    grouped = groupby(sorted(msgs, key=key), key=key)
    for k, v in grouped:
        v = list(v)
        print(f"{k}: {len(v)}")


def _parse_messages() -> List[Message]:
    messages = []
    msgdir = Path("data/private/messages")
    for chat in msgdir.glob("*/message.html"):
        print(chat)
        with open(chat) as f:
            data = f.read()
            other = str(chat).split("/")[-2]
            soup = bs4.BeautifulSoup(data, "lxml")
            for msg in soup.select("div[role='main']")[0]:
                try:
                    # print(msg.prettify())
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


def _print_msg(msg: Message):
    print(f"{msg.from_name} -> {msg.to_name}: {msg.content}   ({msg.date.isoformat()})")


if __name__ == "__main__":
    main()
