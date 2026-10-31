"""Altar Discord bot.

Slash commands: /download /mods /mod /submit /status /pending /admins
Announces new Altar releases and newly approved mods in ANNOUNCE_CHANNEL_ID.

Environment:
  DISCORD_TOKEN         the bot token (required)
  ANNOUNCE_CHANNEL_ID   channel for announcements (optional)
  GITHUB_REPO           default oliverja0612-prog/altar-isaac
  GITHUB_TOKEN          optional, raises GitHub's API limit from 60 to 5000 calls an hour
  POLL_MINUTES          how often to check for news, default 5
"""
import os
import re

import aiohttp
import discord
from discord import app_commands
from discord.ext import tasks

REPO = os.environ.get("GITHUB_REPO", "oliverja0612-prog/altar-isaac")
OWNER, NAME = REPO.split("/")
SITE = f"https://{OWNER.lower()}.github.io/{NAME}/"
INDEX = SITE + "registry/index.json"
API = f"https://api.github.com/repos/{REPO}"
SUBMIT = f"https://github.com/{REPO}/issues/new?template=submit-mod.yml"
ANNOUNCE = int(os.environ.get("ANNOUNCE_CHANNEL_ID") or 0)
POLL = float(os.environ.get("POLL_MINUTES") or 5)
BLOOD = discord.Colour(0x8E1B1B)
PAPER = discord.Colour(0xEADCC0)


class Altar(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.http_session: aiohttp.ClientSession | None = None
        self.seen_release: str | None = None
        self.seen_mods: dict[str, str] | None = None

    async def setup_hook(self):
        headers = {"User-Agent": "Altar-Discord-Bot", "Accept": "application/vnd.github+json"}
        if os.environ.get("GITHUB_TOKEN"):
            headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
        self.http_session = aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=20))
        await self.tree.sync()
        if ANNOUNCE:
            self.watch.start()

    async def close(self):
        if self.http_session:
            await self.http_session.close()
        await super().close()

    async def get(self, url):
        async with self.http_session.get(url) as r:
            r.raise_for_status()
            return await r.json(content_type=None)

    async def mods(self):
        return (await self.get(INDEX)).get("mods", [])

    async def latest(self):
        rel = await self.get(f"{API}/releases/latest")
        exe = next((a for a in rel.get("assets", []) if a["name"].lower().endswith(".exe")), None)
        return rel, exe

    @tasks.loop(minutes=POLL)
    async def watch(self):
        channel = self.get_channel(ANNOUNCE)
        if channel is None:
            return
        try:
            rel, exe = await self.latest()
            if self.seen_release and rel["tag_name"] != self.seen_release:
                await channel.send(embed=release_embed(rel, exe, new=True))
            self.seen_release = rel["tag_name"]
        except Exception as e:  # GitHub hiccup: try again next loop
            print("release check failed:", e)
        try:
            mods = await self.mods()
            now = {m["id"]: m["commit"] for m in mods}
            if self.seen_mods is not None:
                for m in mods:
                    old = self.seen_mods.get(m["id"])
                    if old is None:
                        await channel.send(content="📦 **New mod in the library!**", embed=mod_embed(m))
                    elif old != m["commit"]:
                        await channel.send(content=f"🔄 **{m['name']}** updated to v{m['version']}", embed=mod_embed(m))
            self.seen_mods = now
        except Exception as e:
            print("mod check failed:", e)

    @watch.before_loop
    async def before_watch(self):
        await self.wait_until_ready()


bot = Altar()


def mb(n):
    return f"{n / 1e6:.1f} MB"


def release_embed(rel, exe, new=False):
    e = discord.Embed(
        title=("🎉 Altar " if new else "Altar ") + rel["tag_name"] + (" is out!" if new else ""),
        url=rel["html_url"], colour=BLOOD,
        description=(rel.get("body") or "")[:600] or "The mod menu, mod manager and mod library for Isaac: Repentance+.")
    if exe:
        e.add_field(name="Download", value=f"[{exe['name']}]({exe['browser_download_url']}) · {mb(exe['size'])}")
    e.add_field(name="Site", value=SITE)
    e.set_footer(text="Windows may warn because the installer isn't signed: More info → Run anyway")
    return e


def mod_embed(m):
    e = discord.Embed(title=m["name"], url=f"https://github.com/{m['repo']}", colour=PAPER,
                      description=m.get("description") or "No description.")
    e.add_field(name="Version", value=f"v{m['version']}")
    e.add_field(name="Author", value=m["author"])
    e.add_field(name="Size", value=mb(m["size"]))
    notes = m.get("warnings", 0)
    e.add_field(name="Safety", value="✅ passed" + (f" · {notes} admin note{'s' if notes != 1 else ''}" if notes else ""), inline=False)
    e.set_footer(text="Install: Altar app → Browse → Install. It updates by itself.")
    return e


async def find_mod(query):
    q = query.lower().strip()
    mods = await bot.mods()
    return next((m for m in mods if m["id"] == q or m["name"].lower() == q), None) or \
        next((m for m in mods if q in m["name"].lower()), None)


# ---------------------------------------------------------------- commands

@bot.tree.command(description="Get the latest Altar installer")
async def download(inter: discord.Interaction):
    await inter.response.defer()
    try:
        rel, exe = await bot.latest()
        await inter.followup.send(embed=release_embed(rel, exe))
    except Exception:
        await inter.followup.send(f"Grab it here: https://github.com/{REPO}/releases/latest")


@bot.tree.command(description="List mods in the Altar library")
@app_commands.describe(search="Filter by name, author or description")
async def mods(inter: discord.Interaction, search: str | None = None):
    await inter.response.defer()
    try:
        items = await bot.mods()
    except Exception:
        return await inter.followup.send("Couldn't load the library right now. Try again in a minute.")
    if search:
        s = search.lower()
        items = [m for m in items if s in f"{m['name']} {m['author']} {m.get('description', '')}".lower()]
    if not items:
        return await inter.followup.send("No mods found." if search else f"The library is empty. Be the first: {SITE}#submit")
    e = discord.Embed(title=f"Altar library · {len(items)} mod{'s' if len(items) != 1 else ''}", url=SITE + "#mods", colour=BLOOD)
    for m in items[:15]:
        desc = (m.get("description") or "")[:90]
        e.add_field(name=f"{m['name']}  v{m['version']}", value=f"by {m['author']}" + (f"\n{desc}" if desc else ""), inline=False)
    if len(items) > 15:
        e.set_footer(text=f"…and {len(items) - 15} more on the site")
    await inter.followup.send(embed=e)


@bot.tree.command(description="Details for one mod")
@app_commands.describe(name="Mod name")
async def mod(inter: discord.Interaction, name: str):
    await inter.response.defer()
    m = await find_mod(name)
    if not m:
        return await inter.followup.send(f"No mod called **{discord.utils.escape_markdown(name)}**. Try `/mods`.")
    await inter.followup.send(embed=mod_embed(m))


@mod.autocomplete("name")
async def mod_names(inter: discord.Interaction, current: str):
    try:
        items = await bot.mods()
    except Exception:
        return []
    c = current.lower()
    return [app_commands.Choice(name=m["name"][:100], value=m["id"]) for m in items if c in m["name"].lower()][:25]


@bot.tree.command(description="How to upload your mod to the Altar library")
async def submit(inter: discord.Interaction):
    e = discord.Embed(title="Upload a mod", url=SITE + "#submit", colour=BLOOD, description=(
        "1. Put your mod in a **public GitHub repo** (with `metadata.xml` / `main.lua`). A release tag like `v1.0.0` is best.\n"
        f"2. Fill in the [submission form]({SUBMIT}).\n"
        "3. A bot runs the **safety check** and comments the report on your issue.\n"
        "4. The **admins** review it. Once approved it's on the site and in the Altar app.\n\n"
        "Check progress any time with `/status <issue number>`."))
    await inter.response.send_message(embed=e)


@bot.tree.command(description="Check a mod submission")
@app_commands.describe(issue="The submission's issue number (the #123 on GitHub)")
async def status(inter: discord.Interaction, issue: int):
    await inter.response.defer()
    try:
        it = await bot.get(f"{API}/issues/{issue}")
    except Exception:
        return await inter.followup.send(f"Couldn't find submission #{issue}.")
    labels = {l["name"] for l in it.get("labels", [])}
    if "mod-submission" not in labels:
        return await inter.followup.send(f"#{issue} isn't a mod submission.")
    if it["state"] == "closed":
        st = "❌ Rejected" if "rejected" in labels else "✅ Published"
    elif "needs-fixes" in labels:
        st = "🛠️ Failed the safety check: see the report on the issue"
    elif "safety-passed" in labels:
        st = "⏳ Passed the safety check, waiting for the admins"
    else:
        st = "🔍 Being checked"
    e = discord.Embed(title=it["title"], url=it["html_url"], colour=PAPER, description=st)
    e.set_footer(text=f"#{issue} by {it['user']['login']}")
    await inter.followup.send(embed=e)


@bot.tree.command(description="Mods waiting for admin review")
@app_commands.default_permissions(manage_guild=True)
async def pending(inter: discord.Interaction):
    await inter.response.defer(ephemeral=True)
    try:
        prs = [p for p in await bot.get(f"{API}/pulls?state=open&per_page=50") if p["head"]["ref"].startswith("submission/")]
    except Exception:
        return await inter.followup.send("Couldn't reach GitHub.", ephemeral=True)
    if not prs:
        return await inter.followup.send("Nothing waiting. 🎉", ephemeral=True)
    e = discord.Embed(title=f"{len(prs)} waiting for review", colour=BLOOD)
    for p in prs[:20]:
        e.add_field(name=re.sub(r"^Mod:\s*", "", p["title"]), value=f"[Review]({p['html_url']}/files)", inline=False)
    await inter.followup.send(embed=e, ephemeral=True)


@bot.tree.command(description="Who runs the Altar library")
async def admins(inter: discord.Interaction):
    await inter.response.defer()
    try:
        idx = await bot.get(INDEX)
    except Exception:
        return await inter.followup.send("Couldn't load the team right now.")
    roles = idx.get("roles", {})
    e = discord.Embed(title="Altar admins", colour=BLOOD,
                      description=f"A mod goes live after {idx.get('approvals_required', 1)} admin approval(s).")
    for a in idx.get("admins", []):
        e.add_field(name=f"{a['github']} · {a['role']}", value=roles.get(a["role"], "-"), inline=False)
    await inter.followup.send(embed=e)


@bot.event
async def on_ready():
    print(f"Altar bot online as {bot.user} in {len(bot.guilds)} server(s)")
    await bot.change_presence(activity=discord.Game("The Binding of Isaac · /download"))


if __name__ == "__main__":
    bot.run(os.environ["DISCORD_TOKEN"])
