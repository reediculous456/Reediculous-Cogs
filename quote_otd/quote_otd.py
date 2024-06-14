from redbot.core import commands, Config
import discord
import random
from datetime import datetime, time
import asyncio

class QuoteOfTheDay(commands.Cog):
    """Post a random quote to a specified channel at a specified time each day."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        default_guild = {
            "quotes": [],
            "posted_quotes": [],
            "channel_id": None,
            "post_time": None,
            "enabled": False
        }
        self.config.register_guild(**default_guild)
        self.task = self.bot.loop.create_task(self.poster_task())

    def cog_unload(self):
        self.task.cancel()

    @commands.group()
    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    async def quote(self, ctx):
        """Group of commands to manage quote posting."""
        return

    @quote.command()
    async def add(self, ctx, *, quote: str):
        """Add a new quote."""
        async with self.config.guild(ctx.guild).quotes() as quotes:
            quotes.append(quote)
        await ctx.send("Quote added.")

    @quote.command()
    async def remove(self, ctx, *, quote: str):
        """Remove a quote."""
        async with self.config.guild(ctx.guild).quotes() as quotes:
            if quote in quotes:
                quotes.remove(quote)
                await ctx.send("Quote removed.")
            else:
                await ctx.send("Quote not found.")

    @quote.command()
    async def bulkadd(self, ctx, *, quotes: str):
        """Bulk add quotes separated by '|'. Example: quote1 | quote2 | quote3"""
        new_quotes = [q.strip() for q in quotes.split('|')]
        async with self.config.guild(ctx.guild).quotes() as current_quotes:
            current_quotes.extend(new_quotes)
        await ctx.send(f"Added {len(new_quotes)} quotes.")

    @quote.command()
    async def setchannel(self, ctx, channel: discord.TextChannel):
        """Set the channel to post quotes in."""
        await self.config.guild(ctx.guild).channel_id.set(channel.id)
        await ctx.send(f"Channel set to {channel.mention}.")

    @quote.command()
    async def settime(self, ctx, hour: int, minute: int):
        """Set the time to post quotes (24-hour format)."""
        if hour is None or minute is None:
            await ctx.send_help(ctx.command)
            return
        post_time = time(hour, minute)
        await self.config.guild(ctx.guild).post_time.set(post_time.strftime("%H:%M"))
        await ctx.send(f"Post time set to {post_time.strftime('%H:%M')}.")

    @quote.command()
    async def enabled(self, ctx: commands.Context, enabled: bool):
        """Enable or disable the daily quote posting."""
        if enabled is None:
            await ctx.send_help(ctx.command)
            return
        await self.config.guild(ctx.guild).enabled.set(enabled)
        status = "enabled" if enabled else "disabled"
        await ctx.send(f"Quote posting has been {status}.")

    async def poster_task(self):
        while True:
            for guild in self.bot.guilds:
                guild_data = await self.config.guild(guild).all()
                if guild_data["enabled"]:
                    post_time = datetime.strptime(guild_data["post_time"], "%H:%M").time()
                    now = datetime.utcnow().time()
                    if now >= post_time and (now - post_time).total_seconds() < 60:
                        await self.post_quote(guild)
            await asyncio.sleep(60)

    async def post_quote(self, guild):
        guild_data = await self.config.guild(guild).all()
        channel = guild.get_channel(guild_data["channel_id"])
        if not channel:
            return

        quotes = guild_data["quotes"]
        posted_quotes = guild_data["posted_quotes"]

        if not quotes:
            await channel.send("No quotes available.")
            return

        if len(posted_quotes) == len(quotes):
            posted_quotes.clear()

        available_quotes = [q for q in quotes if q not in posted_quotes]
        quote = random.choice(available_quotes)
        posted_quotes.append(quote)

        await self.config.guild(guild).posted_quotes.set(posted_quotes)
        await channel.send(quote)
