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
    async def quoteotd(self, ctx):
        """Group of commands to manage quote posting."""
        return

    @quoteotd.command()
    async def add(self, ctx, *, quote: str):
        """Add a new quote."""
        async with self.config.guild(ctx.guild).quotes() as quotes:
            quotes.append(quote)
        await ctx.send("Quote added.")

    @quoteotd.command()
    async def remove(self, ctx, *, quote: str):
        """Remove a quote."""
        async with self.config.guild(ctx.guild).quotes() as quotes:
            if quote in quotes:
                quotes.remove(quote)
                await ctx.send("Quote removed.")
            else:
                await ctx.send("Quote not found.")

    @quoteotd.command()
    async def bulkadd(self, ctx, *, quotes: str = None):
        """Bulk add quotes separated by '|'. Example: quote1 | quote2 | quote3"""
        if ctx.message.attachments:
            attachment = ctx.message.attachments[0]
            if attachment.filename.endswith(".txt"):
                content = (await attachment.read()).decode('utf-8')
                new_quotes = [q.strip() for q in content.split('|')]
            else:
                await ctx.send("Please upload a valid .txt file.")
                return
        elif quotes:
            new_quotes = [q.strip() for q in quotes.split('|')]
        else:
            await ctx.send_help(ctx.command)
            return

        async with self.config.guild(ctx.guild).quotes() as current_quotes:
            current_quotes.extend(new_quotes)

        await ctx.send(f"Added {len(new_quotes)} quotes.")

    @quoteotd.command()
    async def list(self, ctx, page: int = 1):
        """List quotes in pages of 15 quotes."""
        quotes = await self.config.guild(ctx.guild).quotes()
        if not quotes:
            await ctx.send("No quotes available.")
            return

        quotes_per_page = 15
        pages = (len(quotes) + quotes_per_page - 1) // quotes_per_page
        if page < 1 or page > pages:
            await ctx.send(f"Invalid page number. Please choose a page between 1 and {pages}.")
            return

        start = (page - 1) * quotes_per_page
        end = start + quotes_per_page
        quote_list = quotes[start:end]
        embed = discord.Embed(title=f"Quotes (Page {page}/{pages})")
        for idx, quote in enumerate(quote_list, start=start + 1):
            embed.add_field(name=f"Quote {idx}", value=discord.utils.escape_markdown(quote), inline=False)

        await ctx.send(embed=embed)

    @quoteotd.command()
    async def setchannel(self, ctx, channel: discord.TextChannel):
        """Set the channel to post quotes in."""
        await self.config.guild(ctx.guild).channel_id.set(channel.id)
        await ctx.send(f"Channel set to {channel.mention}.")

    @quoteotd.command()
    async def settime(self, ctx, hour: int, minute: int):
        """Set the time to post quotes (24-hour format)."""
        if hour is None or minute is None:
            await ctx.send_help(ctx.command)
            return
        post_time = time(hour, minute)
        await self.config.guild(ctx.guild).post_time.set(post_time.strftime("%H:%M"))
        await ctx.send(f"Post time set to {post_time.strftime('%H:%M')}.")

    @quoteotd.command()
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
