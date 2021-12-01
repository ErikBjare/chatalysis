import json
import logging
from pathlib import Path
from datetime import datetime

from joblib import Memory

from .models import Message, Conversation

logger = logging.getLogger(__name__)

cache_location = "./.message_cache"
memory = Memory(cache_location, verbose=0)

# TODO: Remove this constant, make configurable
ME = "Erik Bj"


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


def _load_all_messages(glob: str = "*") -> list[Message]:
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
        participants: list[str] = [
            p["name"].encode("latin1").decode("utf8") for p in data["participants"]
        ]
        # print(participants)
        thread_type = data[
            "thread_type"
        ]  # Can be one of at least: Regular, RegularGroup
        is_groupchat = thread_type == "RegularGroup"

        for msg in data["messages"]:
            if "content" not in msg:
                logger.debug(f"Skipping non-text message: {msg}")
                continue

            # the `.encode('latin1').decode('utf8')` hack is needed due to https://stackoverflow.com/a/50011987/965332
            sender = msg["sender_name"].encode("latin1").decode("utf8")
            text = msg["content"].encode("latin1").decode("utf8")
            reacts: list[dict] = msg.get("reactions", [])
            for react in reacts:
                react["reaction"] = react["reaction"].encode("latin1").decode("utf8")
                react["actor"] = react["actor"].encode("latin1").decode("utf8")

            # if reacts:
            #     print(f"R: {reacts}")

            receiver = ME if not is_groupchat and sender != ME else title
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
