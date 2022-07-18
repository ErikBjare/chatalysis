import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from joblib import Memory

from .models import Message, Conversation

logger = logging.getLogger(__name__)

cache_location = "./.message_cache"
memory = Memory(cache_location, verbose=0)

# TODO: Remove this constant, make configurable
ME = "Erik Bjäreholt"


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


def _load_all_messages(glob: str = "*") -> list[Message]:
    messages = [msg for convo in _load_convos(glob) for msg in convo.messages]
    logger.info(f"Loaded {len(messages)} messages")
    return messages


def _parse_message(msg: dict, is_groupchat: bool, title: str) -> Optional[Message]:
    _type = msg.pop("type")
    if _type == "Subscribe":
        # We don't care about 'X added Y to the group'
        return None
    elif _type == "Generic":
        if "content" not in msg:
            return None
        else:
            text = msg.pop("content").encode("latin1").decode("utf8")
    elif _type == "Share":
        if "share" in msg:
            share = msg.pop("share", None)
            if share:
                text = share["link"]
        else:
            logger.warning("Share message without share field")
    else:
        logger.info(f"Skipping non-text message with type {_type}: {msg}")

    is_unsent = msg.pop("is_unsent", None)
    if is_unsent:
        print(f"is_unsent: {is_unsent}")

    # the `.encode('latin1').decode('utf8')` hack is needed due to https://stackoverflow.com/a/50011987/965332
    sender = msg.pop("sender_name").encode("latin1").decode("utf8")
    reacts: list[dict] = msg.pop("reactions", [])
    for react in reacts:
        react["reaction"] = react["reaction"].encode("latin1").decode("utf8")
        react["actor"] = react["actor"].encode("latin1").decode("utf8")

    receiver = ME if not is_groupchat and sender != ME else title
    date = datetime.fromtimestamp(msg.pop("timestamp_ms") / 1000)

    # find remaining unused keys in msg
    unused_keys = set(msg.keys()) - {"is_unsent"}
    for key in unused_keys:
        logger.info(f"Skipping unknown key: {key}")

    data = {"groupchat": is_groupchat}
    return Message(
        sender,
        receiver,
        date,
        text,
        reactions=reacts,
        data=data,
    )


def test_parse_message_text():
    name = "Erik Bjäreholt".encode("utf-8").decode("latin1")
    content = "Hello"
    msg = {
        "type": "Generic",
        "content": content,
        "timestamp_ms": 1568010580000,
        "sender_name": name,
        "reactions": [],
    }
    assert _parse_message(msg, False, "") is not None


def test_parse_message_share():
    name = "Erik Bjäreholt".encode("utf-8").decode("latin1")
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    msg = {
        "type": "Share",
        "share": {
            "link": url,
        },
        "timestamp_ms": 1568010580000,
        "sender_name": name,
    }
    resmsg = _parse_message(msg, False, "")
    assert resmsg is not None
    assert resmsg.content == url


@memory.cache
def _parse_chatfile(filename: str) -> Conversation:
    # FIXME: This should open all `message_*.json` files and merge into a single convo
    messages = []
    with open(filename) as f:
        data = json.load(f)
        title = data["title"].encode("latin1").decode("utf8")
        participants: list[str] = [
            p["name"].encode("latin1").decode("utf8") for p in data["participants"]
        ]
        # print(participants)

        # Can be one of at least: Regular, RegularGroup
        thread_type = data.pop("thread_type")
        is_groupchat = thread_type == "RegularGroup"

        for msg in data["messages"]:
            message = _parse_message(msg, is_groupchat, title)
            if message is not None:
                messages.append(message)

    return Conversation(
        title=title,
        participants=participants,
        messages=messages,
        data={"groupchat": is_groupchat},
    )
