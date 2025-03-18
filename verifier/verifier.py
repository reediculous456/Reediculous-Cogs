import discord
import asyncio
import re
import random
from redbot.core import commands, Config
from redbot.core.bot import Red
from discord.utils import get

class Verifier(commands.Cog):
    """A cog that handles user verification with questions."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=10061998)
        self.forbidden_help_message = (
            'please enable direct messages from server members to complete the verification process.\n'
            'On desktop: click the server name, then "Privacy Settings", and turn on "Direct Messages"\n'
            'On Mobile: click the server name, then scroll down and turn on "Allow Direct Messages"'
        )
        default_guild = {
            "questions": [],
            "role_id": None,
            "kick_on_fail": False,
            "verification_enabled": False,
            "num_questions_to_ask": None
        }
        self.config.register_guild(**default_guild)

    async def get_prefix(self, member: discord.Member):
        # Retrieve the prefix for the guild
        prefixes = await self.bot.get_prefix(member)
        if isinstance(prefixes, list):
            return prefixes[0]
        return prefixes

    def normalize_answer(self, answer: str):
        # Remove non-alphanumeric characters and convert to lowercase
        return re.sub(r'[^a-zA-Z0-9]', '', answer).lower()

    async def ask_questions(self, member: discord.Member, guild: discord.Guild, channel: discord.TextChannel):
        prefix = await self.get_prefix(member)
        config = await self.config.guild(guild).all()
        questions = config['questions']
        role_id =config['role_id']
        role = get(guild.roles, id=role_id)
        kick_on_fail =config['kick_on_fail']
        num_questions_to_ask =config['num_questions_to_ask']

        if not role:
            try:
                await member.send("The admins of this server have enabled verification questions but have not set the role to be granted upon correct answers. Please contact them to have this corrected.")
            except discord.Forbidden:
                await channel.send(f"{member.mention}, {self.forbidden_help_message}")
            return

        if not questions:
            try:
                await member.send("The admins of this server have enabled verification questions but have not set any questions. Please contact them to have this corrected.")
            except discord.Forbidden:
                await channel.send(f"{member.mention}, {self.forbidden_help_message}")
            return

        sticky_questions = [q for q in questions if q.get("sticky")]
        non_sticky_questions = [q for q in questions if not q.get("sticky")]

        if num_questions_to_ask:
            if len(sticky_questions) > num_questions_to_ask:
                questions_to_ask = sticky_questions
            else:
                num_additional_questions = num_questions_to_ask - len(sticky_questions)
                questions_to_ask = sticky_questions + random.sample(non_sticky_questions, num_additional_questions)
        else:
            questions_to_ask = questions

        def check(m):
            return m.author == member and isinstance(m.channel, discord.DMChannel)

        try:
            await member.send("Welcome! Please answer the following questions correctly to gain access to the server. You have 90 seconds to answer each question.")
            for q in questions_to_ask:
                await member.send(q["question"])
                msg = await self.bot.wait_for('message', check=check, timeout=90.0)
                normalized_response = self.normalize_answer(msg.content)
                if not any(normalized_response == self.normalize_answer(answer) for answer in q["answers"]):
                    if kick_on_fail and guild.me.guild_permissions.kick_members:
                        await member.send("Incorrect answer. You have been removed from the server.")
                        await guild.kick(member)
                    else:
                        await member.send("Incorrect answer. Please contact an admin if you believe this is a mistake.")
                    return
            await member.send("Congratulations! You have answered all questions correctly.")
            await member.add_roles(role)
        except discord.Forbidden:
            await channel.send(f"{member.mention}, {self.forbidden_help_message}")
        except asyncio.TimeoutError:
            await member.send(f'You took too long to respond. To restart this process run the command {prefix}verify in the server.')

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        verification_enabled = await self.config.guild(member.guild).verification_enabled()
        if verification_enabled:
            await self.ask_questions(member, member.guild, member.guild.system_channel)

    @commands.guild_only()
    @commands.command()
    async def verify(self, ctx: commands.Context):
        """Manually trigger the verification process."""
        verification_enabled = await self.config.guild(ctx.guild).verification_enabled()
        if not verification_enabled:
            await ctx.send("Verification is currently disabled.")
            return

        member = ctx.author
        role_id = await self.config.guild(ctx.guild).role_id()
        role = get(ctx.guild.roles, id=role_id)

        if role in member.roles:
            await ctx.send("You are already verified.")
        else:
            await self.ask_questions(member, ctx.guild, ctx.channel)

    @commands.group()
    @commands.admin_or_permissions(manage_channels=True)
    @commands.guild_only()
    async def verifyset(self, ctx: commands.Context) -> None:
        """Sets verification module settings."""
        return

    @verifyset.command()
    async def verifiedrole(self, ctx: commands.Context, role: discord.Role):
        """Set the role to be granted upon correct answers."""
        await self.config.guild(ctx.guild).role_id.set(role.id)
        await ctx.send(f"The verified role has been set to {role.name}.")

    @verifyset.command()
    async def addquestion(self, ctx: commands.Context, question: str, *answers: str):
        """Add a question to the verification quiz. Provide multiple answers separated by spaces."""
        async with self.config.guild(ctx.guild).questions() as questions:
            questions.append({"question": question, "answers": list(answers), "sticky": False})
        await ctx.send("Question added.")

    @verifyset.command()
    async def removequestion(self, ctx: commands.Context, index: int):
        """Remove a question from the verification quiz by its index."""
        async with self.config.guild(ctx.guild).questions() as questions:
            if 0 < index <= len(questions):
                removed_question = questions.pop(index - 1)
                await ctx.send(f"Removed question: {removed_question['question']}")
            else:
                await ctx.send("Invalid question index.")

    @verifyset.command()
    async def editquestion(self, ctx: commands.Context, index: int, question: str, *answers: str):
        """Edit a question in the verification quiz by its index."""
        async with self.config.guild(ctx.guild).questions() as questions:
            if 0 < index <= len(questions):
                questions[index - 1] = {"question": question, "answers": list(answers), "sticky": questions[index - 1].get("sticky", False)}
                await ctx.send(f"Question {index} has been updated.")
            else:
                await ctx.send("Invalid question index.")

    @verifyset.command()
    async def listquestions(self, ctx: commands.Context):
        """List all verification questions."""
        questions = await self.config.guild(ctx.guild).questions()
        if not questions:
            await ctx.send("No verification questions set.")
            return

        question_list = "\n".join([f'{i+1}. Q: "{q["question"]}" A: {", ".join(q["answers"])} (Sticky: {"Yes" if q.get("sticky") else "No"})' for i, q in enumerate(questions)])
        await ctx.send(f"Verification Questions:\n{question_list}\n\nThis post will be deleted in 60 seconds.", delete_after=60)

    @verifyset.command()
    async def setkickonfail(self, ctx: commands.Context, kick_on_fail: bool):
        """Enable or disable kicking the user on verification failure."""
        await self.config.guild(ctx.guild).kick_on_fail.set(kick_on_fail)
        status = "enabled" if kick_on_fail else "disabled"
        await ctx.send(f"Kicking on verification failure has been {status}.")

    @verifyset.command()
    async def enabled(self, ctx: commands.Context, verification_enabled: bool):
        """Enable or disable the verification process."""
        await self.config.guild(ctx.guild).verification_enabled.set(verification_enabled)
        status = "enabled" if verification_enabled else "disabled"
        await ctx.send(f"Verification has been {status}.")

    @verifyset.command()
    async def numquestions(self, ctx: commands.Context, num_questions: int | bool):
        """Set the number of questions to ask during verification. Use true to ask all questions."""
        if num_questions is True:
          await self.config.guild(ctx.guild).num_questions_to_ask.set(None)
        else:
          await self.config.guild(ctx.guild).num_questions_to_ask.set(num_questions)

        await ctx.send(f"The number of questions to ask during verification has been set to {num_questions}.")

    @verifyset.command()
    async def stickyquestion(self, ctx: commands.Context, index: int, sticky: bool):
        """Set whether a question is sticky or not by its index."""
        async with self.config.guild(ctx.guild).questions() as questions:
            if 0 < index <= len(questions):
                questions[index - 1]["sticky"] = sticky
                status = "sticky" if sticky else "non-sticky"
                await ctx.send(f"Question {index} has been marked as {status}.")
            else:
                await ctx.send("Invalid question index.")

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete."""
        return
