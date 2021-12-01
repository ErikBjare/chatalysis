from datetime import datetime, date
from dataclasses import dataclass, field


@dataclass
class Message:
    from_name: str
    to_name: str
    timestamp: datetime
    content: str
    reactions: list[dict] = field(default_factory=list)
    data: dict = field(default_factory=dict)

    def print(self) -> None:
        from .util import _format_emojicount, _count_emoji

        emojicount_str = _format_emojicount(
            _count_emoji("".join(d["reaction"] for d in self.reactions))
        )
        content = self.content

        # start multiline messages on new line
        if content.count("\n") > 0:
            content = "\n  " + "\n  ".join(content.split("\n"))

        # wrap long lines correctly
        if content.count("\n") == 0:
            words = content.split(" ")
            content = " ".join(words[:20]) + " " + " ".join(words[20:])
        print(
            f"{self.timestamp.isoformat()[:10]} | {self.from_name} -> {self.to_name}: {content}"
            + ("  ({emojicount_str})" if emojicount_str else "")
        )


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
            messages=sorted(self.messages + c2.messages, key=lambda m: m.timestamp),
            data=self.data,
        )


@dataclass
class Writerstats:
    days: set[date] = field(default_factory=set)
    msgs: int = 0
    words: int = 0
    reacts_recv: int = 0
    reacts_sent: int = 0
