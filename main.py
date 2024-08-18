#!/usr/bin/env python3

from keys import API_HASH, API_ID, TOKEN
from config import BOTNAME, CHANNEL, ADMINS, LOG_CHAT, SUPPORT_CHAT
from misc.sudo import SudoConfig
from misc import commands

import asyncio
import io
import logging
import requests
import uvloop

from pyrogram import Client, idle, filters
from pyrogram.enums import ParseMode

LINK = "https://thispersondoesnotexist.com"

logging.basicConfig(
    format="[%(asctime)s|%(levelname)s] - %(name)s - %(message)s", level=logging.INFO)
log = logging.getLogger(BOTNAME)


async def get_photo():
    res = await asyncio.to_thread(requests.get, LINK)
    obj = io.BytesIO(res.content)
    obj.name = "thispersondoesnotexist.com.jpg"
    return obj


async def main():
    channel = None
    me = None
    docs = {}
    lock = asyncio.Lock()

    bot = Client(BOTNAME, api_id=API_ID, api_hash=API_HASH, bot_token=TOKEN)
    bot.set_parse_mode(ParseMode.HTML)

    sudo = SudoConfig(
        bot,
        admins=ADMINS,
        log_chat=LOG_CHAT,
        error_message="An error occurred.\nPlease, contact @dst212 for further information."
    )

    commands.init("id", bot)
    commands.init("ping", bot)
    commands.init("inspect", bot)
    commands.init("feedback", bot, sudo, SUPPORT_CHAT)

    @bot.on_message(filters.command(["start", "help"]))
    async def _(bot, m):
        await m.reply(
            "Bot made by @dst212 with @pyrogram, visit @dst212botnews for updates.\n\n"
            f"{f"<b>Also join @{channel.username} because yes.</b>\n"
                "Every newly generated person will be posted there too.\n\n"
                if channel and channel.username else ""}"
            f"This bot works thanks to {LINK}.\n\n"
            f"To get started, send /go!\n\n"
            f"If you don't want the result to be shared to the channel, send /silent instead.",
        )

    @bot.on_message(filters.command(["go", "silent"]))
    async def _(bot, m):
        r = await m.reply("Loading...")
        file = await get_photo()
        photo = await m.reply_photo(file, caption=f"@{me.username}")
        try:
            await r.delete()
        except Exception:
            pass
        document = await m.reply_document(file, caption=f"@{me.username}")
        if channel:
            if m.command[0].startswith("go"):
                await photo.copy(channel.id)
                async with lock:
                    docs[photo.photo.file_unique_id] = document
            else:
                # I still enjoy seeing the bugged pictures, I can't miss any
                p = await photo.copy(LOG_CHAT)
                await document.copy(LOG_CHAT, reply_to_message_id=p.id)

    async with bot:
        if CHANNEL:
            channel = await bot.get_chat(CHANNEL)
            if channel.linked_chat:
                @bot.on_message(filters.chat(channel.linked_chat.id) & filters.linked_channel & filters.photo)
                async def _(bot, m):
                    async with lock:
                        unique_id = m.photo.file_unique_id
                        message = docs.get(unique_id)
                        if message:
                            await message.copy(m.chat.id, reply_to_message_id=m.id)
                            del docs[unique_id]
                        else:
                            log.warning(f"Unrecognized file: {unique_id}")
        me = await bot.get_users("me")
        log.info(f"Started as @{me.username}.")
        await sudo.log("Started.")
        await idle()
        await sudo.log("Stopped.")
        log.info("Stopping.")

uvloop.install()
asyncio.run(main())
