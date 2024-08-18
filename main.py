#!/usr/bin/env python3

from keys import API_HASH, API_ID, TOKEN
from config import BOTNAME, CHANNEL, ADMINS, LOG_CHAT, SUPPORT_CHAT
try:
    from config import DELAY
except ImportError:
    DELAY = 3600  # Delay between a post and the following one in the channel
try:
    from config import POOL_SIZE
except ImportError:
    POOL_SIZE = 10

from misc.sudo import SudoConfig
from misc.fun import try_wait
from misc import commands

import asyncio
import io
import json
import logging
import requests
import uvloop

from pyrogram import Client, idle, filters
from pyrogram.enums import ParseMode
from pyrogram.types import (
    InlineQueryResultCachedPhoto,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from pyrogram.errors import QueryIdInvalid

LINK = "https://thispersondoesnotexist.com"
POOL_FILE = "./pool.json"

logging.basicConfig(
    format="[%(asctime)s|%(levelname)s] - %(name)s - %(message)s", level=logging.INFO)
log = logging.getLogger(BOTNAME)


async def main():
    docs: dict[str, str] = {}
    pool: list[(str, str)] = None
    ilock = asyncio.Lock()  # Pool init lock
    dlock = asyncio.Lock()  # Access to docs's items
    plock = asyncio.Lock()  # Access to pool's items
    delay = asyncio.Lock()  # Keep the function busy to avoid /go flood
    log_chat = dict(
        chat_id=LOG_CHAT[0],
        reply_to_message_id=LOG_CHAT[1],
        disable_notification=True,
    ) if isinstance(LOG_CHAT, list) else dict(
        chat_id=LOG_CHAT,
        disable_notification=True,
    )
    channel = None
    caption = None
    me = None

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

    # Get a new photo and get the file_id of photo and document
    async def new_photo() -> (str, str):
        log.info("Getting a new photo...")
        res = await asyncio.to_thread(requests.get, LINK)
        file = io.BytesIO(res.content)
        file.name = "thispersondoesnotexist.com.jpg"
        photo = await try_wait(
            bot.send_photo, **log_chat, photo=file, caption=f"{len(pool)+1}/{POOL_SIZE}")
        if photo:
            log.info(f"Photo: {photo.photo.file_id}")
        else:
            raise Exception("Couldn't send the photo.")
        doc = await try_wait(bot.send_document, **dict(
            log_chat, reply_to_message_id=photo.id, document=file))
        if doc:
            log.info(f"Doc: {doc.document.file_id}")
        else:
            raise Exception("Couldn't send the document.")
        return photo.photo.file_id, doc.document.file_id

    # Fill the pool with new photos
    async def init_pool():
        if ilock.locked():
            # No need to repeat this process if it's already going on
            return
        nonlocal pool
        async with ilock:
            async with plock:
                if pool is None:
                    try:
                        with open(POOL_FILE, "r") as f:
                            log.info("Loading pool from file...")
                            pool = json.load(f)
                        await sudo.log(f"Loaded pool from file ({len(pool)} item{"" if len(pool) == 1 else "s"}).")
                    except Exception:
                        # Any error would lead to the reset of the pool
                        pool = []
            if len(pool) < POOL_SIZE:  # Only save the pool if it will change
                while len(pool) < POOL_SIZE:
                    photo, doc = await new_photo()
                    async with plock:
                        pool.append((photo, doc))
                log.info("Dumping pool to file...")
                with open(POOL_FILE, "w") as f:
                    log.debug(f"{pool}")
                    json.dump(pool, f)

    # Get a never used photo id
    async def get_photo() -> (str, str):
        ret = None
        async with plock:
            if pool:
                ret = pool.pop(0)
        asyncio.run_coroutine_threadsafe(init_pool(), asyncio.get_event_loop())
        if not ret:
            ret = await new_photo()
        return ret

    # Forward to the channel and wait
    async def send_to_channel(photo: str, doc: str, notify: bool = False):
        if delay.locked():
            log.info(f"Waiting before sending:\n{photo}\n{doc}")
        async with delay:
            p = await try_wait(
                bot.send_photo,
                channel.id,
                photo=photo,
                caption=caption,
                disable_notification=not notify,
            )
            if p:
                async with dlock:
                    docs[p.photo.file_unique_id] = doc
            await asyncio.sleep(DELAY)

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
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Use it inline!", switch_inline_query=""),
            ]]),
        )

    @bot.on_message(filters.command(["go", "silent"]))
    async def _(bot, m):
        r = await m.reply("Loading...")
        photo, doc = await get_photo()
        await m.reply_photo(photo, caption=caption)
        try:
            await r.delete()
        except Exception:
            pass
        await m.reply_document(doc, caption=caption)
        if channel:
            if m.command[0].startswith("go"):
                await send_to_channel(photo, doc)

    @bot.on_inline_query()
    async def _(bot, q):
        photo, doc = await get_photo()
        try:
            await q.answer([InlineQueryResultCachedPhoto(
                photo,
                title="Generate person!",
                caption=caption,
            )], cache_time=1)
        except QueryIdInvalid:
            pass
        if "silent" not in q.query and channel:
            await send_to_channel(photo, doc)

    async with bot:
        if CHANNEL:
            channel = await bot.get_chat(CHANNEL)
            if channel.linked_chat:
                @bot.on_message(filters.chat(channel.linked_chat.id) & filters.linked_channel & filters.photo)
                async def _(bot, m):
                    async with dlock:
                        unique_id = m.photo.file_unique_id
                        doc = docs.get(unique_id)
                        if doc:
                            await bot.send_document(
                                m.chat.id,
                                document=doc,
                                caption=caption,
                                reply_to_message_id=m.id,
                                disable_notification=True,
                            )
                            del docs[unique_id]
                        else:
                            log.warning(f"Unrecognized file: {unique_id}")
        asyncio.run_coroutine_threadsafe(init_pool(), asyncio.get_event_loop())
        me = await bot.get_users("me")
        caption = f"@{channel.username if channel and channel.username else me.username}"
        log.info(f"Started as @{me.username}.")
        await sudo.log("Started.")
        await idle()
        await sudo.log("Stopped.")
        log.info("Stopping.")

uvloop.install()
asyncio.run(main())
