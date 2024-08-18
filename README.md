# unrealpeoplebot

This Telegram bot ([@unrealpeoplebot](https://unrealpeoplebot.t.me)) can fetch images from the website [thispersondoesnotexist.com](https://thispersondoesnotexist.com).

It also shares each result to a dedicated channel ([@thesepeopledonotexist](https://thesepeopledonotexist.t.me)).

Follow [@dst212botnews](https://dst212botnews.t.me) for updates.

## Installation

Requires Python 3.12+.

On Linux and UNIX-based systems:

```shell
git clone --recurse-submodules https://github.com/dst212/unrealpeoplebot.git
cd unrealpeoplebot
python3 -m venv env
source env/bin/activate
python3 -m pip install -r requirements.txt
```

## Configuration

`config.py`

```python
BOTNAME = "unrealpeoplebot"  # Name of the bot for logging purposes
CHANNEL = "@thesepeopledonotexist"  # Channel where generated pictures will be shared
ADMINS = [448025569]  # Whoever will be able to reply to /feedback and manage the bot
LOG_CHAT = ADMINS[0]  # Log bot actions (start, stop)
SUPPORT_CHAT = ADMINS[0]  # Chat for /feedback
```

`keys.py`

```python
TOKEN = "Bot's token here"
API_ID = "Your Telegram API's application ID from my.telegram.org"
API_HASH = "Your API hash"
```

---

# Credits

- [thispersondoesnotexist.com](https://thispersondoesnotexist.com): the actual tool

- [Pyrogram](https://github.com/pyrogram/pyrogram): Telegram client
