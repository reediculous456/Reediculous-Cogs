from redbot.core import commands, Config
from redbot.core.bot import Red
import discord
import random
import asyncio
import io
from datetime import datetime, time, timezone
from discord.ext import tasks
import pytz

class QuoteOfTheDay(commands.Cog):
    """Post a random quote to a specified channel at a specified time each day."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=2024061601, force_registration=True)
        default_guild = {
            "quotes": [],
            "posted_quotes": [],
            "channel_id": None,
            "post_time": None,
            "timezone": None,
            "enabled": False
        }
        self.config.register_guild(**default_guild)
        self.poster_task.start()

    def cog_unload(self):
        self.poster_task.cancel()

    @commands.group()
    @commands.guild_only()
    @commands.admin()
    async def quoteotd(self, ctx: commands.Context):
        """Group of commands to manage quote posting."""
        return

    @quoteotd.command()
    async def add(self, ctx: commands.Context, quote: str):
        """Add a new quote."""
        async with self.config.guild(ctx.guild).quotes() as quotes:
            quotes.append(quote)
        await ctx.send("Quote added.")

    @quoteotd.command()
    async def remove(self, ctx: commands.Context, quote: str):
        """Remove a quote."""
        async with self.config.guild(ctx.guild).quotes() as quotes:
            if quote in quotes:
                quotes.remove(quote)
                await ctx.send("Quote removed.")
            else:
                await ctx.send("Quote not found.")

    @quoteotd.command()
    async def bulkadd(self, ctx: commands.Context, quotes: str = None):
        """Bulk add quotes separated by '|'. (Example: quote1 | quote2 | quote3) or you can upload a .txt file with quotes separated by new lines."""
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

    # TODO: use a menu to display quotes
    @quoteotd.command()
    async def list(self, ctx: commands.Context, page: commands.positive_int = 1):
        """List quotes in pages of 15 quotes, navigable via emoji reactions by guild admins."""
        quotes = await self.config.guild(ctx.guild).quotes()
        if not quotes:
            await ctx.send("No quotes available.")
            return

        quotes_per_page = 15
        pages = (len(quotes) + quotes_per_page - 1) // quotes_per_page
        if page < 1 or page > pages:
            await ctx.send(f"Invalid page number. Please choose a page between 1 and {pages}.")
            return

        # Build embeds for each page
        embeds = []
        for p in range(1, pages + 1):
            start = (p - 1) * quotes_per_page
            end = start + quotes_per_page
            embed = discord.Embed(title=f"Quotes (Page {p}/{pages})")
            embed.color = await ctx.embed_color()
            for idx, quote in enumerate(quotes[start:end], start=start + 1):
                embed.add_field(name=f"Quote {idx}", value=discord.utils.escape_markdown(quote), inline=False)
            embeds.append(embed)

        current = max(1, min(page, pages)) - 1
        message = await ctx.send(embed=embeds[current])

        # If only one page, nothing to paginate
        if pages <= 1:
            return

        prev_emoji = "◀️"
        next_emoji = "▶️"
        stop_emoji = "⏹️"
        emojis = (prev_emoji, next_emoji, stop_emoji)

        for e in emojis:
            try:
                await message.add_reaction(e)
            except Exception:
                pass

        def check(reaction: discord.Reaction, user: discord.User):
            if user.bot:
                return False
            if reaction.message.id != message.id:
                return False
            if str(reaction.emoji) not in emojis:
                return False
            member = ctx.guild.get_member(user.id)
            if not member:
                return False
            # Only allow guild admins/managers to page
            if member.guild_permissions.administrator or member.guild_permissions.manage_guild:
                return True
            return False

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=120.0, check=check)
            except asyncio.TimeoutError:
                try:
                    await message.clear_reactions()
                except Exception:
                    pass
                break
            else:
                emoji = str(reaction.emoji)
                if emoji == prev_emoji:
                    current = (current - 1) % pages
                    try:
                        await message.edit(embed=embeds[current])
                    except Exception:
                        pass
                elif emoji == next_emoji:
                    current = (current + 1) % pages
                    try:
                        await message.edit(embed=embeds[current])
                    except Exception:
                        pass
                elif emoji == stop_emoji:
                    try:
                        await message.clear_reactions()
                    except Exception:
                        pass
                    break

                # try to remove the user's reaction to keep UI clean
                try:
                    await message.remove_reaction(reaction.emoji, user)
                except Exception:
                    pass

    @quoteotd.command()
    async def export(self, ctx: commands.Context, filename: str = "quotes.txt"):
        """Export all current quotes to a text file and send it in the channel."""
        quotes = await self.config.guild(ctx.guild).quotes()
        if not quotes:
            await ctx.send("No quotes available to export.")
            return

        content = "\n".join(quotes)
        bio = io.BytesIO(content.encode("utf-8"))
        bio.seek(0)
        try:
            await ctx.send("Here are the exported quotes:", file=discord.File(bio, filename=filename))
        except Exception:
            await ctx.send("Failed to send the file. Ensure the bot has permission to upload files.")

    @quoteotd.command()
    async def clear(self, ctx: commands.Context):
        """Clear all current quotes — requires reaction confirmation from an admin."""
        quotes = await self.config.guild(ctx.guild).quotes()
        if not quotes:
            await ctx.send("There are no quotes to clear.")
            return

        confirm_msg = await ctx.send(
            "This will permanently delete all quotes. React ✅ to confirm or ❌ to cancel. (30s)"
        )

        confirm_emoji = "✅"
        cancel_emoji = "❌"

        try:
            await confirm_msg.add_reaction(confirm_emoji)
            await confirm_msg.add_reaction(cancel_emoji)
        except Exception:
            pass

        def check(reaction: discord.Reaction, user: discord.User):
            if user.bot:
                return False
            if reaction.message.id != confirm_msg.id:
                return False
            if str(reaction.emoji) not in (confirm_emoji, cancel_emoji):
                return False
            member = ctx.guild.get_member(user.id)
            if not member:
                return False
            # Only allow guild admins/managers to confirm
            return member.guild_permissions.administrator or member.guild_permissions.manage_guild

        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            try:
                await confirm_msg.clear_reactions()
            except Exception:
                pass
            await ctx.send("Clear cancelled (timeout).")
            return

        if str(reaction.emoji) == cancel_emoji:
            try:
                await confirm_msg.clear_reactions()
            except Exception:
                pass
            await ctx.send("Clear cancelled.")
            return

        # Confirmed
        await self.config.guild(ctx.guild).quotes.set([])
        await self.config.guild(ctx.guild).posted_quotes.set([])
        try:
            await confirm_msg.clear_reactions()
        except Exception:
            pass
        await ctx.send("All quotes have been cleared.")

    @quoteotd.command()
    async def setchannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the channel to post quotes in."""
        await self.config.guild(ctx.guild).channel_id.set(channel.id)
        await ctx.send(f"Channel set to {channel.mention}.")

    @quoteotd.command()
    async def settime(self, ctx: commands.Context, hour: commands.positive_int, minute: commands.positive_int):
        """Set the time to post quotes (24-hour format)."""
        timezone_str = await self.config.guild(ctx.guild).timezone()
        if not timezone_str:
            prefix = ctx.prefix
            await ctx.send(f"Please set the guild's time zone first using `{prefix}quoteotd settimezone <timezone>`.")
            return

        try:
            user_time = datetime.combine(datetime.today(), time(hour, minute))
            user_timezone = pytz.timezone(timezone_str)
            user_time = user_timezone.localize(user_time)
            utc_time = user_time.astimezone(pytz.utc).time()
            await self.config.guild(ctx.guild).post_time.set(utc_time.strftime("%H:%M"))
            await ctx.send(f"Post time set to {utc_time.strftime('%H:%M')} UTC.")
        except ValueError:
            await ctx.send("Invalid time format. Please ensure the hour and minute are valid numbers.")
        except pytz.UnknownTimeZoneError:
            await ctx.send("The specified timezone is invalid. Please set a valid timezone first.")

    @quoteotd.command()
    async def settimezone(self, ctx: commands.Context, timezone: str):
        """Set the time zone for the guild."""
        try:
            pytz.timezone(timezone)  # validate the time zone
            await self.config.guild(ctx.guild).timezone.set(timezone)
            await ctx.send(f"Time zone set to {timezone}.")
        except pytz.UnknownTimeZoneError:
            await ctx.send("Invalid time zone. Please provide a valid time zone.")

    @quoteotd.command()
    async def enabled(self, ctx: commands.Context, enabled: bool):
        """Enable or disable the daily quote posting."""
        await self.config.guild(ctx.guild).enabled.set(enabled)
        status = "enabled" if enabled else "disabled"
        await ctx.send(f"Quote posting has been {status}.")

    @tasks.loop(minutes=1.0)
    async def poster_task(self):
        for guild in self.bot.guilds:
            guild_data = await self.config.guild(guild).all()
            if guild_data["enabled"] and guild_data["post_time"]:
                post_time = datetime.strptime(guild_data["post_time"], "%H:%M").time()
                now = datetime.now(timezone.utc).time()
                if now >= post_time and (datetime.combine(datetime.now(timezone.utc), now) - datetime.combine(datetime.now(timezone.utc), post_time)).total_seconds() < 60:
                    await self.post_quote(guild)

    @poster_task.before_loop
    async def before_poster_task(self):
        await self.bot.wait_until_ready()

    async def post_quote(self, guild: discord.Guild):
        guild_data = await self.config.guild(guild).all()
        channel = guild.get_channel(guild_data["channel_id"])
        if not channel:
            return

        quotes = guild_data["quotes"]
        posted_quotes = guild_data["posted_quotes"]

        if not quotes:
            await channel.send("No quotes available.")
            return

        if len(posted_quotes) >= len(quotes):
            posted_quotes = []
            await self.config.guild(guild).posted_quotes.set(posted_quotes)

        available_quotes = [q for q in quotes if q not in posted_quotes]
        if not available_quotes:
            available_quotes = quotes  # Fallback in case of any unexpected issue

        quote = random.choice(available_quotes)
        posted_quotes.append(quote)

        await self.config.guild(guild).posted_quotes.set(posted_quotes)
        await channel.send(quote)

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete."""
        return
