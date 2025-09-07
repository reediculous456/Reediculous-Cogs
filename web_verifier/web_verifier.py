import discord
import asyncio
import re
import jwt
import time
import logging
from aiohttp import web
from redbot.core import commands, Config
from redbot.core.bot import Red
from discord.utils import get

log = logging.getLogger("red.reediculous-cogs.web_verifier")

class WebVerifier(commands.Cog):
    """A cog that handles user verification with JWT tokens and web requests."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=10061999, force_registration=True)
        self.forbidden_help_message = (
            "please enable direct messages from server members to complete the verification process.\n"
            'On desktop: click the server name, then "Privacy Settings", and turn on "Direct Messages"\n'
            'On Mobile: click the server name, then scroll down and turn on "Allow Direct Messages"'
        )
        default_guild = {
            "question": {},
            "role_id": None,
            "kick_on_fail": False,
            "verification_enabled": False,
            "jwt_secret": None,
            "verification_url": "",
            "verified_members": {},  # Store user_id -> member_id mappings
        }
        self.config.register_guild(**default_guild)
        self.web_app = None
        self.web_runner = None

    async def cog_load(self):
        """Start the web server when the cog loads."""
        await self.start_web_server()

    async def cog_unload(self):
        """Stop the web server when the cog unloads."""
        await self.stop_web_server()

    async def start_web_server(self):
        """Start the aiohttp web server for handling verification requests."""
        try:
            self.web_app = web.Application()
            self.web_app.router.add_get("/verify", self.handle_verification)
            self.web_runner = web.AppRunner(self.web_app)
            await self.web_runner.setup()
            site = web.TCPSite(self.web_runner, "localhost", 8080)
            await site.start()
            log.info("Verification web server started on http://localhost:8080")
        except Exception as e:
            log.error(f"Failed to start verification web server: {e}")

    async def stop_web_server(self):
        """Stop the aiohttp web server."""
        if self.web_runner:
            await self.web_runner.cleanup()

    async def handle_verification(self, request):
        """Handle incoming verification requests with JWT tokens."""
        jwt_token = request.query.get("jwt")

        if not jwt_token:
            return web.Response(text="Missing JWT token", status=400)

        try:
            # We need to find which guild this token belongs to by trying all guild secrets
            decoded_payload = None
            guild_id = None

            for guild in self.bot.guilds:
                try:
                    secret = await self.config.guild(guild).jwt_secret()
                    if secret:
                        decoded_payload = jwt.decode(
                            jwt_token, secret, algorithms=["HS256"]
                        )
                        guild_id = decoded_payload.get("guild_id")
                        if guild_id == guild.id:
                            break
                except jwt.InvalidTokenError:
                    continue

            if not decoded_payload or not guild_id:
                return web.Response(text="Invalid JWT token", status=401)

            # Extract data from JWT - member_id should be in the payload now
            user_id = decoded_payload.get("user_id")
            username = decoded_payload.get("username")
            member_id = decoded_payload.get("member_id")

            if not all([user_id, username, guild_id]):
                return web.Response(text="Missing required fields in JWT", status=400)

            if not member_id:
                return web.Response(
                    text="Missing member_id in JWT payload", status=400
                )

            # Find the guild and user
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return web.Response(text="Guild not found", status=404)

            member = guild.get_member(user_id)
            if not member:
                return web.Response(text="Member not found", status=404)

            # Save the member ID for this user
            async with self.config.guild(guild).verified_members() as verified_members:
                verified_members[str(user_id)] = member_id

            # Grant the verified role
            role_id = await self.config.guild(guild).role_id()
            role = get(guild.roles, id=role_id)

            if role:
                await member.add_roles(role)
                try:
                    await member.send(
                        f"Congratulations! You have been verified with member ID: {member_id}"
                    )
                except discord.Forbidden:
                    pass  # Can't send DM

                return web.Response(
                    text=f"Successfully verified {username} (ID: {user_id}) with member ID: {member_id}",
                    status=200,
                )
            else:
                return web.Response(text="Verification role not configured", status=500)

        except jwt.ExpiredSignatureError:
            return web.Response(text="JWT token has expired", status=401)
        except jwt.InvalidTokenError:
            return web.Response(text="Invalid JWT token", status=401)
        except Exception as e:
            return web.Response(text=f"Server error: {str(e)}", status=500)

    async def generate_verification_jwt(
        self, member: discord.Member, guild: discord.Guild
    ):
        """Generate a JWT token for verification."""
        secret = await self.config.guild(guild).jwt_secret()
        if not secret:
            raise ValueError("JWT secret not configured. Please set a secret using the setsecret command.")

        payload = {
            "user_id": member.id,
            "username": str(member),
            "guild_id": guild.id,
            "exp": int(time.time()) + 1800,  # 30 minutes expiration
            "iat": int(time.time()),
        }

        token = jwt.encode(payload, secret, algorithm="HS256")
        return token

    async def get_prefix(self, member: discord.Member):
        # Retrieve the prefix for the guild
        prefixes = await self.bot.get_prefix(member)
        if isinstance(prefixes, list):
            return prefixes[0]
        return prefixes

    def normalize_answer(self, answer: str):
        # Remove non-alphanumeric characters and convert to lowercase
        return re.sub(r"[^a-zA-Z0-9]", "", answer).lower()

    async def ask_question_and_generate_url(
        self, member: discord.Member, guild: discord.Guild, channel: discord.TextChannel
    ):
        """Ask the static question and generate verification URL."""
        prefix = await self.get_prefix(member)
        config = await self.config.guild(guild).all()
        question = config["question"]
        role_id = config["role_id"]
        role = get(guild.roles, id=role_id)
        kick_on_fail = config["kick_on_fail"]
        verification_url = config["verification_url"]

        if not role:
            try:
                await member.send(
                    "The admins of this server have enabled verification questions but have not set the role to be granted upon correct answers. Please contact them to have this corrected."
                )
            except discord.Forbidden:
                await channel.send(f"{member.mention}, {self.forbidden_help_message}")
            return

        if not question or not question.get("question"):
            try:
                await member.send(
                    "The admins of this server have enabled verification questions but have not set any questions. Please contact them to have this corrected."
                )
            except discord.Forbidden:
                await channel.send(f"{member.mention}, {self.forbidden_help_message}")
            return

        def check(m):
            return m.author == member and isinstance(m.channel, discord.DMChannel)

        try:
            await member.send(
                "Welcome! Please answer the following question correctly to gain access to the server. You have 90 seconds to answer."
            )
            await member.send(f"**{question['question']}**")

            # Wait for the user's answer
            msg = await self.bot.wait_for("message", check=check, timeout=90.0)
            normalized_response = self.normalize_answer(msg.content)
            if not any(
                normalized_response == self.normalize_answer(answer)
                for answer in question["answers"]
            ):
                if kick_on_fail and guild.me.guild_permissions.kick_members:
                    await member.send(
                        "Incorrect answer. You have been removed from the server."
                    )
                    await guild.kick(member)
                else:
                    await member.send(
                        "Incorrect answer. Please contact an admin if you believe this is a mistake."
                    )
                return

            # Only generate JWT token if answer is correct
            jwt_token = await self.generate_verification_jwt(member, guild)

            # Create verification URL
            verification_link = f"{verification_url}?jwt={jwt_token}"

            # Send the verification URL to the user
            message = f"""Correct! Now visit this link to complete verification:
{verification_link}

This link will expire in 30 minutes."""

            await member.send(message)

        except ValueError as e:
            # JWT secret not configured
            log.error(f"JWT secret not configured: {e}")
            try:
                await member.send(
                    "The verification system is not properly configured. Please contact an admin."
                )
            except discord.Forbidden:
                await channel.send(
                    f"{member.mention}, the verification system is not properly configured. Please contact an admin."
                )
        except discord.Forbidden:
            await channel.send(f"{member.mention}, {self.forbidden_help_message}")
        except Exception as e:
            log.error(f"Error generating verification URL: {e}")
            try:
                await member.send(
                    "There was an error generating your verification link. Please contact an admin."
                )
            except discord.Forbidden:
                await channel.send(
                    f"{member.mention}, there was an error generating your verification link. Please contact an admin."
                )
        except asyncio.TimeoutError:
            await member.send(
                f"You took too long to respond. To restart this process run the command {prefix}verify in the server."
            )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        verification_enabled = await self.config.guild(
            member.guild
        ).verification_enabled()
        if verification_enabled:
            await self.ask_question_and_generate_url(
                member, member.guild, member.guild.system_channel
            )

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
            await self.ask_question_and_generate_url(member, ctx.guild, ctx.channel)

    @commands.guild_only()
    @commands.command()
    async def unverify(self, ctx: commands.Context):
        """Unlink your discord account from your member ID and remove the verified role."""
        member = ctx.author
        role_id = await self.config.guild(ctx.guild).role_id()
        role = get(ctx.guild.roles, id=role_id)

        if role and role not in member.roles:
            await ctx.send("You are not verified.")
        else:
            if role:
                await member.remove_roles(role)
            async with self.config.guild(ctx.guild).verified_members() as verified_members:
                if str(member.id) in verified_members:
                    del verified_members[str(member.id)]
            await ctx.send("You have been unverified.")

    @commands.group()
    @commands.admin_or_permissions(manage_channels=True)
    @commands.guild_only()
    async def verifyset(self, ctx: commands.Context) -> None:
        """Sets verification module settings."""
        return

    @verifyset.command()
    async def verifiedrole(self, ctx: commands.Context, role: discord.Role):
        """Set the role to be granted upon verification."""
        await self.config.guild(ctx.guild).role_id.set(role.id)
        await ctx.send(f"The verified role has been set to {role.name}.")

    @verifyset.command()
    async def question(self, ctx: commands.Context, question_text: str, *answers: str):
        """Set the verification question."""
        question_data = {"question": question_text, "answers": list(answers)}
        await self.config.guild(ctx.guild).question.set(question_data)
        await ctx.send("Question added.")

    @verifyset.command()
    async def url(self, ctx: commands.Context, url: str):
        """Set the verification URL base (where users will be sent for verification)."""
        if not url.startswith(('http://', 'https://')):
            await ctx.send("URL must start with http:// or https://")
            return

        await self.config.guild(ctx.guild).verification_url.set(url)
        await ctx.send(f"The verification URL has been set to: {url}")

    @verifyset.command()
    async def status(self, ctx: commands.Context):
        """View current verification settings."""
        config = await self.config.guild(ctx.guild).all()

        role = get(ctx.guild.roles, id=config["role_id"]) if config["role_id"] else None
        role_name = role.name if role else "Not set"

        question_text = config["question"].get("question", "Not set") if config["question"] else "Not set"

        embed = discord.Embed(title="Verification Settings", color=0x00ff00)
        embed.add_field(name="Enabled", value=config["verification_enabled"], inline=True)
        embed.add_field(name="Verified Role", value=role_name, inline=True)
        embed.add_field(name="Kick on Fail", value=config["kick_on_fail"], inline=True)
        embed.add_field(name="Verification URL", value=config["verification_url"] or "Not set", inline=False)
        embed.add_field(name="Question", value=question_text, inline=False)

        # Enhanced JWT secret status
        secret_status = "✅ Configured" if config["jwt_secret"] and len(config["jwt_secret"]) >= 24 else "❌ Not set or too short"
        embed.add_field(name="JWT Secret", value=secret_status, inline=True)

        verified_count = len(config["verified_members"])
        embed.add_field(name="Verified Members", value=verified_count, inline=True)

        # Add warnings for incomplete configuration
        warnings = []
        if not config["jwt_secret"] or len(config["jwt_secret"]) < 24:
            warnings.append("⚠️ JWT secret not configured or too short")
        if not config["question"]:
            warnings.append("⚠️ Verification question not set")
        if not config["role_id"]:
            warnings.append("⚠️ Verified role not set")
        if not config["verification_url"]:
            warnings.append("⚠️ Verification URL not set")

        if warnings:
            embed.add_field(name="Configuration Warnings", value="\n".join(warnings), inline=False)

        await ctx.send(embed=embed)

    @verifyset.command()
    async def showquestion(self, ctx: commands.Context):
        """Show the verification question."""
        question = await self.config.guild(ctx.guild).question()
        if not question or not question.get("question"):
            await ctx.send("No verification question set.")
            return

        question_text = f'Q: "{question["question"]}" A: {", ".join(question["answers"])}'
        await ctx.send(f"Verification Question:\n{question_text}\n\nThis post will be deleted in 60 seconds.", delete_after=60)

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
    async def viewmembers(self, ctx: commands.Context):
        """View all verified members and their member IDs."""
        verified_members = await self.config.guild(ctx.guild).verified_members()
        if not verified_members:
            await ctx.send("No verified members found.")
            return

        member_list = []
        for user_id, member_id in verified_members.items():
            member = ctx.guild.get_member(int(user_id))
            if member:
                member_list.append(
                    f"{member.display_name} ({member.id}): Member ID {member_id}"
                )
            else:
                member_list.append(f"Unknown User ({user_id}): Member ID {member_id}")

        if member_list:
            message = "Verified Members:\n" + "\n".join(member_list)
            # Split long messages
            if len(message) > 2000:
                for i in range(0, len(message), 1900):
                    await ctx.send(message[i : i + 1900])
            else:
                await ctx.send(message)

    @verifyset.command()
    async def checkuser(self, ctx: commands.Context, user: discord.Member):
        """Check if a user is verified and show their member ID."""
        verified_members = await self.config.guild(ctx.guild).verified_members()
        user_id = str(user.id)

        if user_id in verified_members:
            member_id = verified_members[user_id]
            role_id = await self.config.guild(ctx.guild).role_id()
            role = get(ctx.guild.roles, id=role_id)
            has_role = role in user.roles if role else False

            embed = discord.Embed(title="User Verification Status", color=0x00ff00)
            embed.add_field(name="User", value=user.mention, inline=True)
            embed.add_field(name="Member ID", value=member_id, inline=True)
            embed.add_field(name="Has Verified Role", value=has_role, inline=True)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"{user.display_name} is not verified.")

    @verifyset.command()
    async def removemember(self, ctx: commands.Context, user: discord.Member):
        """Remove a member's verification record."""
        async with self.config.guild(ctx.guild).verified_members() as verified_members:
            if str(user.id) in verified_members:
                del verified_members[str(user.id)]
                await ctx.send(f"Removed verification record for {user.display_name}.")
            else:
                await ctx.send(
                    f"{user.display_name} is not in the verified members list."
                )

    @verifyset.command()
    async def setsecret(self, ctx: commands.Context, *, secret: str):
        """Set the JWT secret for verification tokens.

        The secret must be at least 24 characters long for security.
        This will invalidate all existing verification tokens.
        """
        if len(secret) < 24:
            await ctx.send("❌ JWT secret must be at least 24 characters long for security.")
            return

        await self.config.guild(ctx.guild).jwt_secret.set(secret)
        await ctx.send(
            "✅ JWT secret has been set successfully. All existing verification tokens are now invalid."
        )

    async def red_delete_data_for_user(self, **kwargs):
        """Delete user data when requested."""
        user_id = kwargs.get("user_id")
        if user_id:
            # Remove user from all guild verification records
            for guild in self.bot.guilds:
                async with self.config.guild(
                    guild
                ).verified_members() as verified_members:
                    if str(user_id) in verified_members:
                        del verified_members[str(user_id)]
