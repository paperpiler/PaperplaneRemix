# @Author Udit Karode <udit.karode@gmail.com>
# @Purpose Forwards a message to the TGR channel along with the divider sticker
# @Date 03/17/2020
# @License Apache License, Version 2.0 <https://www.apache.org/licenses/LICENSE-2.0.txt>
import os

from telethon.tl.functions.messages import SendMediaRequest
from telethon.tl.types import InputMediaDocument, InputDocument
from userbot import client
import random
from userbot.utils.events import NewMessage
from telethon.tl.functions.messages import GetStickersRequest

SUCCESS_MESSAGES = [
    "Retard added to showcase!",
    "Judgement has been served, master!"
    "The rarts have been returned to where they belong!"
]

tgr_entity = client.get_entity("t.me/yeet_retards")


@client.onMessage(command="tgr",
                  require_admin=False,
                  outgoing=True, regex=r"tgr$")
async def tgr_send(event: NewMessage.Event) -> None:
    if not event.reply_to_msg_id:
        await event.answer("`I need a retard to proceed!`")
        return

    reply = await event.get_reply_message()

    # Forward the message to TGR
    await client.forward_messages(
        entity=tgr_entity,
        messages=reply,
        silent=True,
        from_peer=reply.chat_id
    )

    divider = client(GetStickersRequest(
        emoticon='❤',
        hash=-1447283942124334054
    ))

    # Send the divider sticker
    await client(SendMediaRequest(
        entities=tgr_entity,
        message='',
        peer=client.get_entity("hyperterminal"),
        media=InputMediaDocument(
            id=InputDocument(
                id=divider.id,
                access_hash=divider.access_hash,
                file_reference=divider.file_reference
            )
        )
    ))

    await event.answer(f"`{random.choice(SUCCESS_MESSAGES)}`")
