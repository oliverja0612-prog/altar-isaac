# Altar Discord bot

Slash commands for your server, plus automatic announcements.

| Command | What it does |
|---|---|
| `/download` | Latest AltarSetup.exe with size and link |
| `/mods [search]` | Mods in the Altar library |
| `/mod <name>` | One mod's details (autocompletes) |
| `/submit` | How to upload a mod |
| `/status <issue>` | Where a submission is: checking, failed, waiting for admins, published |
| `/pending` | Submissions waiting for review (only people with **Manage Server** see it) |
| `/admins` | The admin team and their roles |

When `ANNOUNCE_CHANNEL_ID` is set, it posts there when a new Altar release comes out
and when a mod is approved or updated.

## 1. Create the bot (5 minutes)

1. Go to <https://discord.com/developers/applications> → **New Application** → name it `Altar`.
2. **Bot** tab → **Reset Token** → copy the token. Keep it secret (it's a password for the bot).
3. **OAuth2 → URL Generator**: tick `bot` and `applications.commands`; under bot permissions tick
   `Send Messages`, `Embed Links`, `View Channels`. Open the generated URL and add the bot to your server.
4. In Discord: **User Settings → Advanced → Developer Mode** on. Right-click your announcements
   channel → **Copy Channel ID**.

## 2. Host it for free

### Railway

1. <https://railway.app> → sign in with GitHub → **New Project → Deploy from GitHub repo** → `altar-isaac`.
2. Service **Settings → Root Directory**: `discord-bot`. It builds from the Dockerfile.
3. **Variables**: add `DISCORD_TOKEN` and `ANNOUNCE_CHANNEL_ID` (optional: `GITHUB_TOKEN`, a
   fine-grained token with no permissions, just to raise GitHub's rate limit).
4. Deploy. The log shows `Altar bot online as Altar#1234`.

### Render

1. <https://render.com> → **New → Background Worker** → connect `altar-isaac`.
2. Root directory `discord-bot`, runtime **Docker** (or Python with build `pip install -r requirements.txt`,
   start `python bot.py`).
3. Add the same environment variables and create it.

## Run it on your PC instead

```
cd discord-bot
pip install -r requirements.txt
set DISCORD_TOKEN=...
python bot.py
```

Slash commands can take a minute to appear the first time.
