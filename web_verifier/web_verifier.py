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
        self.config = Config.get_conf(self, identifier=10071999)
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
            "verify_on_join": True,
        }
        default_global = {
            "question": {},
            "verification_url": "",
            "jwt_secret": None,
            "port": 8080,  # Default port for the web server
            "verified_members": {},  # Store user_id -> member_id mappings (now global)
            "incorrect_answers": {},  # Store normalized incorrect answers with counts and timestamps
        }
        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)
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
            self.web_app.router.add_get("/", lambda request: web.Response(text="You do not have access to this page!"))
            self.web_app.router.add_post("/discord-auth/return", self.handle_verification)
            self.web_runner = web.AppRunner(self.web_app)
            await self.web_runner.setup()
            port = await self.config.port()
            site = web.TCPSite(self.web_runner, "0.0.0.0", port)
            await site.start()
            log.info(f"Verification web server started on http://localhost:{port}")
        except Exception as e:
            log.error(f"Failed to start verification web server: {e}")

    async def stop_web_server(self):
        """Stop the aiohttp web server."""
        if self.web_runner:
            await self.web_runner.cleanup()

    async def handle_verification(self, request):
        """Handle incoming verification requests with JWT tokens."""
        try:
            # Get JWT from POST request body
            data = await request.json()
            jwt_token = data.get("jwt")
        except Exception:
            # Fallback to query parameter if JSON parsing fails
            jwt_token = request.query.get("jwt")

        if not jwt_token:
            return web.Response(text="Missing JWT token", status=400)

        try:
            secret = await self.config.jwt_secret()
            try:
                decoded_payload = jwt.decode(
                    jwt_token, secret, algorithms=["HS256"]
                )
                guild_id = decoded_payload.get("guild_id")
            except jwt.InvalidTokenError:
                return web.Response(text="Invalid JWT token", status=401)

            if not decoded_payload or not guild_id:
                return web.Response(text="Invalid JWT token", status=401)

            # Extract data from JWT - member_id should be in the payload now
            # Convert IDs to integers to ensure compatibility with discord.py
            try:
                user_id = int(decoded_payload.get("user_id"))
                guild_id = int(guild_id)
            except (ValueError, TypeError):
                return web.Response(text="Invalid user_id or guild_id in JWT", status=400)

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
            async with self.config.verified_members() as verified_members:
                verified_members[str(user_id)] = member_id

            await self.complete_verification(guild, member, member_id)

            # Grant the verified role in ALL other servers where this user exists and verification is enabled
            servers_updated = [guild.name]
            for other_guild in self.bot.guilds:
                if other_guild.id == guild.id:
                    continue  # Skip the originating guild

                other_member = other_guild.get_member(user_id)
                if not other_member:
                    continue  # User not in this server

                verification_enabled = await self.config.guild(other_guild).verification_enabled()
                if not verification_enabled:
                    continue  # Verification not enabled in this server

                other_role_id = await self.config.guild(other_guild).role_id()
                other_role = get(other_guild.roles, id=other_role_id) if other_role_id else None

                servers_updated.append(other_guild.name)
                # Dispatch verification event for this server too
                self.bot.dispatch('member_verified', other_guild, other_member, member_id)

                if other_role and other_role not in other_member.roles:
                    try:
                        await other_member.add_roles(other_role)
                    except discord.Forbidden:
                        log.warning(f"Could not grant verified role to {username} in {other_guild.name} - missing permissions")

            try:
                await member.send(
                    f"Congratulations! You have been verified with member ID: {member_id}. It may take a few minutes for your access to be updated."
                )
            except discord.Forbidden:
                pass  # Can't send DM

            return web.Response(
                text=f"Successfully verified {username} (ID: {user_id}) with member ID: {member_id}",
                status=201,
            )

        except jwt.ExpiredSignatureError:
            return web.Response(text="JWT token has expired", status=401)
        except jwt.InvalidTokenError:
            return web.Response(text="Invalid JWT token", status=401)
        except Exception as e:
            return web.Response(text=f"Server error: {str(e)}", status=500)

    async def complete_verification(self, guild: discord.Guild, member: discord.Member, member_id: str):
        # Grant the verified role in the originating guild
        role_id = await self.config.guild(guild).role_id()
        role = get(guild.roles, id=role_id) if role_id else None

        if role:
            await member.add_roles(role)

        self.bot.dispatch('member_verified', guild, member, member_id)

    async def generate_verification_jwt(
        self, member: discord.Member, guild: discord.Guild
    ):
        """Generate a JWT token for verification."""
        secret = await self.config.jwt_secret()
        if not secret:
            raise ValueError("JWT secret not configured. Please set a secret using the setsecret command.")

        payload = {
            "user_id": str(member.id),
            "username": str(member),
            "guild_id": str(guild.id),
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

    def normalize_answer(self, answer):
        """Normalize the answer by removing spaces and converting to lowercase."""
        return re.sub(r"[^a-zA-Z0-9]", "", answer).lower()

    async def log_incorrect_answer(self, user_id: int, guild_id: int, original_answer: str, normalized_answer: str):
        """Log an incorrect answer with normalized grouping and timestamp."""
        async with self.config.incorrect_answers() as incorrect_answers:
            # Use normalized answer as the key for grouping
            if normalized_answer not in incorrect_answers:
                incorrect_answers[normalized_answer] = {
                    "count": 0,
                    "original_forms": set(),
                    "first_seen": int(time.time()),
                    "last_seen": int(time.time()),
                    "users": set()
                }

            entry = incorrect_answers[normalized_answer]
            entry["count"] += 1
            entry["original_forms"].add(original_answer)
            entry["last_seen"] = int(time.time())
            entry["users"].add(f"{user_id}:{guild_id}")

            # Convert sets back to lists for JSON serialization
            entry["original_forms"] = list(entry["original_forms"])
            entry["users"] = list(entry["users"])

    async def get_question_config(self, guild: discord.Guild):
        """Get question config, checking guild first, then global fallback."""
        # First check guild config (takes precedence)
        guild_question = await self.config.guild(guild).question()
        if guild_question and guild_question.get("question"):
            return guild_question, "guild"

        # Fallback to global config
        global_question = await self.config.question()
        if global_question and global_question.get("question"):
            return global_question, "global"

        # No question set anywhere
        return None, None

    async def ask_question_and_generate_url(
        self, member: discord.Member, guild: discord.Guild, channel: discord.TextChannel
    ):
        """Ask the static question and generate verification URL."""
        prefix = await self.get_prefix(member)
        config = await self.config.guild(guild).all()
        question, _ = await self.get_question_config(guild)
        kick_on_fail = config["kick_on_fail"]
        verification_url = await self.config.verification_url()

        if not question:
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
                # Log the incorrect answer
                await self.log_incorrect_answer(member.id, guild.id, msg.content, normalized_response)

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
        """Trigger verification process when a member joins if enabled."""
        verification_enabled = await self.config.guild(member.guild).verification_enabled()
        verify_on_join = await self.config.guild(member.guild).verify_on_join()
        if verification_enabled:
            verified_members = await self.config.verified_members()
            if str(member.id) in verified_members:
                self.bot.dispatch('member_verified', member.guild, member, verified_members[str(member.id)])
                return
            if verify_on_join:
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
        verified_members = await self.config.verified_members()

        if str(member.id) in verified_members:
            await self.complete_verification(ctx.guild, member, verified_members[str(member.id)])
            await ctx.send("You are already verified.")
        else:
            await self.ask_question_and_generate_url(member, ctx.guild, ctx.channel)

    @commands.command()
    async def unverify(self, ctx: commands.Context):
        """Warn user they will be kicked, confirm with reactions, then kick and unverify. This is intended for is a user is no longer using a discord account."""
        member = ctx.author
        verified_members = await self.config.verified_members()
        if str(member.id) not in verified_members:
            await ctx.send("You are not verified.")
            return

        total_guilds = 0
        for guild in self.bot.guilds:
            guild_member = guild.get_member(member.id)
            if guild_member:
                total_guilds += 1

        # Warn and ask for confirmation
        confirm_msg = await ctx.send(
            f"{member.mention}, if you continue, you will be kicked from {total_guilds} servers and unverified. React with ✅ to confirm or ❌ to cancel.")
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")

        def check(reaction, user):
            return (
                user == member and reaction.message.id == confirm_msg.id and str(reaction.emoji) in ["✅", "❌"]
            )
        try:
            reaction, user = await self.bot.wait_for("reaction_add", check=check, timeout=30.0)
            await confirm_msg.delete()
        except asyncio.TimeoutError:
            await ctx.send("Unverify cancelled due to timeout.")
            await confirm_msg.delete()
            return

        if str(reaction.emoji) == "❌":
            await ctx.send("Unverify cancelled.")
            return

        # Remove role from ALL servers and kick from current server
        servers_processed = []
        kicked_from = []
        not_kicked_from = []

        # Remove from global verified members first
        async with self.config.verified_members() as global_verified:
            if str(member.id) in global_verified:
                del global_verified[str(member.id)]

        # Remove verified role from all servers where user exists
        for guild in self.bot.guilds:
            guild_member = guild.get_member(member.id)
            if not guild_member:
                continue

            verification_enabled = await self.config.guild(guild).verification_enabled()
            if not verification_enabled:
                continue

            role_id = await self.config.guild(guild).role_id()
            role = get(guild.roles, id=role_id) if role_id else None

            if role and role in guild_member.roles:
                try:
                    await guild_member.remove_roles(role)
                    servers_processed.append(guild.name)
                except discord.Forbidden:
                    pass  # Ignore permission errors

            try:
                await guild_member.kick(reason="User requested verification removal.")
                kicked_from.append(guild.name)
            except discord.Forbidden:
                not_kicked_from.append(guild.name)
                pass  # Ignore permission errors

        status_msg = f"{member.display_name} has been unverified"
        if servers_processed:
            status_msg += f" and removed from verified role in: {', '.join(servers_processed)}"
        if kicked_from:
            status_msg += f" and kicked from: {', '.join(kicked_from)}"
        else:
            status_msg += f" but could not be kicked from: {', '.join(not_kicked_from)} due to missing permissions"

        await ctx.send(status_msg + ".")

    @commands.group()
    @commands.admin()
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
    async def clearverifiedrole(self, ctx: commands.Context):
        """Clear the verified role setting for this guild."""
        current_role_id = await self.config.guild(ctx.guild).role_id()

        if not current_role_id:
            await ctx.send("No verified role is currently set for this guild.")
            return

        # Get the role name for confirmation message
        current_role = get(ctx.guild.roles, id=current_role_id)
        role_name = current_role.name if current_role else f"Role ID {current_role_id}"

        await self.config.guild(ctx.guild).role_id.set(None)
        await ctx.send(f"The verified role ({role_name}) has been cleared. No role will be granted upon verification until a new one is set.")

    @verifyset.command()
    async def question(self, ctx: commands.Context, question_text: str, *answers: str):
        """Set the verification question for this guild (overrides global question)."""
        question_data = {"question": question_text, "answers": list(answers)}
        await self.config.guild(ctx.guild).question.set(question_data)
        await ctx.send("Guild question added. This will override any global question for this server.")

    @verifyset.command()
    async def clearquestion(self, ctx: commands.Context):
        """Clear the guild verification question (only works if global question exists)."""
        # Check if there's a global question to fall back to
        global_question = await self.config.question()
        if not global_question or not global_question.get("question"):
            await ctx.send("❌ Cannot clear guild question: No global question is set to fall back to. Set a global question first with `verifyconfig globalquestion`.")
            return

        # Check if there's actually a guild question to clear
        guild_question = await self.config.guild(ctx.guild).question()
        if not guild_question or not guild_question.get("question"):
            await ctx.send("ℹ️ This guild doesn't have a custom question set. The global question is already being used.")
            return

        # Clear the guild question
        await self.config.guild(ctx.guild).question.set({})
        await ctx.send("✅ Guild question cleared. This server will now use the global question as fallback.")

    @verifyset.command()
    async def status(self, ctx: commands.Context):
        """View current verification settings."""
        config = await self.config.guild(ctx.guild).all()

        role = get(ctx.guild.roles, id=config["role_id"]) if config["role_id"] else None
        role_name = role.name if role else "Not set"

        # Get current question with source
        question, question_source = await self.get_question_config(ctx.guild)
        if question:
            source_text = "🌐 Global" if question_source == "global" else f"🏠 Guild ({ctx.guild.name})"
            question_text = f"{question['question']} ({source_text})"
        else:
            question_text = "Not set"

        embed = discord.Embed(title="Verification Settings", color=0x00ff00)
        embed.add_field(name="Enabled", value=config["verification_enabled"], inline=True)
        embed.add_field(name="Verified Role", value=role_name, inline=True)
        embed.add_field(name="Kick on Fail", value=config["kick_on_fail"], inline=True)
        embed.add_field(name="Verify on Join", value=config["verify_on_join"], inline=True)

        verification_url = await self.config.verification_url()
        embed.add_field(name="Verification URL", value=verification_url or "Not set", inline=False)
        embed.add_field(name="Question", value=question_text, inline=False)

        # Enhanced JWT secret status
        jwt_secret = await self.config.jwt_secret()
        secret_status = "✅ Configured" if jwt_secret and len(jwt_secret) >= 32 else "❌ Not set or too short"
        embed.add_field(name="JWT Secret", value=secret_status, inline=True)

        global_verified_members = await self.config.verified_members()
        verified_count = len(global_verified_members)
        embed.add_field(name="Verified Members", value=verified_count, inline=True)

        # Add warnings for incomplete configuration
        warnings = []
        if not jwt_secret or len(jwt_secret) < 32:
            warnings.append("⚠️ JWT secret not configured or too short")
        if not question:
            warnings.append("⚠️ Verification question not set (neither global nor guild-specific)")
        if not config["role_id"]:
            warnings.append("⚠️ Verified role not set")
        if not verification_url:
            warnings.append("⚠️ Verification URL not set")

        if warnings:
            embed.add_field(name="Configuration Warnings", value="\n".join(warnings), inline=False)

        await ctx.send(embed=embed)

    @verifyset.command()
    async def showquestion(self, ctx: commands.Context):
        """Show the verification question."""
        question, source = await self.get_question_config(ctx.guild)
        if not question:
            await ctx.send("No verification question set.")
            return

        question_text = f'Q: "{question["question"]}" A: {", ".join(question["answers"])}'
        source_text = "🌐 Global" if source == "global" else f"🏠 Guild ({ctx.guild.name})"
        await ctx.send(f"**Verification Question** ({source_text}):\n{question_text}\n\nThis post will be deleted in 60 seconds.", delete_after=60)

    @verifyset.command()
    async def setkickonfail(self, ctx: commands.Context, kick_on_fail: bool):
        """Enable or disable kicking the user on verification failure."""
        await self.config.guild(ctx.guild).kick_on_fail.set(kick_on_fail)
        status = "enabled" if kick_on_fail else "disabled"
        await ctx.send(f"Kicking on verification failure has been {status}.")

    @verifyset.command()
    async def verifyonjoin(self, ctx: commands.Context, verify_on_join: bool):
        """Enable or disable auto-start of verification on join."""
        await self.config.guild(ctx.guild).verify_on_join.set(verify_on_join)
        status = "enabled" if verify_on_join else "disabled"
        await ctx.send(f"Verification on join has been {status}.")

    @verifyset.command()
    async def enabled(self, ctx: commands.Context, verification_enabled: bool):
        """Enable or disable the verification process."""
        await self.config.guild(ctx.guild).verification_enabled.set(verification_enabled)
        status = "enabled" if verification_enabled else "disabled"
        await ctx.send(f"Verification has been {status}.")

    @verifyset.command()
    async def checkuser(self, ctx: commands.Context, user: discord.Member):
        """Check if a user is globally verified and show their member ID."""
        verified_members = await self.config.verified_members()
        user_id = str(user.id)

        if user_id in verified_members:
            if ctx.guild.get_member(user.id) is None:
                await ctx.send(f"{user.display_name} is not a member of this server.")
                return

            member_id = verified_members[user_id]
            role_id = await self.config.guild(ctx.guild).role_id()

            if role_id:
                role = get(ctx.guild.roles, id=role_id)
                has_role = role in user.roles if role else False

            # Check how many servers this user has verified role in
            verified_servers = []
            for guild in self.bot.guilds:
                guild_member = guild.get_member(user.id)
                if not guild_member:
                    continue

                verification_enabled = await self.config.guild(guild).verification_enabled()
                if not verification_enabled:
                    continue

                verified_servers.append(guild.name)

            embed = discord.Embed(title="User Verification Status", color=0x00ff00)
            embed.add_field(name="User", value=user.mention, inline=True)
            embed.add_field(name="Member ID", value=member_id, inline=True)
            if role_id:
                embed.add_field(name="Has Role (This Server)", value=has_role, inline=True)
            embed.add_field(name="Verified Servers", value=f"{len(verified_servers)} servers" if verified_servers else "None", inline=True)
            if verified_servers:
                embed.add_field(name="Server Names", value=", ".join(verified_servers), inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"{user.display_name} is not verified.")

    @commands.group()
    @commands.is_owner()
    async def verifyconfig(self, ctx: commands.Context) -> None:
        """Verifier settings and commands."""
        pass

    @verifyconfig.command("question")
    async def globalquestion(self, ctx: commands.Context, question_text: str, *answers: str):
        """Set the global verification question (fallback when no guild question is set)."""
        question_data = {"question": question_text, "answers": list(answers)}
        await self.config.question.set(question_data)
        await ctx.send("Global question added. This will be used as fallback for guilds that don't have their own question set.")

    @verifyconfig.command("clearquestion")
    async def clearglobalquestion(self, ctx: commands.Context):
        """Clear the global verification question."""
        await self.config.question.set({})
        await ctx.send("Global question cleared. Guilds without their own questions will have no verification question set.")

    @verifyconfig.command("showquestion")
    async def showglobalquestion(self, ctx: commands.Context):
        """Show the global verification question."""
        global_question = await self.config.question()
        if not global_question or not global_question.get("question"):
            await ctx.send("No global verification question is currently set.")
            return

        question_text = f'Q: "{global_question["question"]}" A: {", ".join(global_question["answers"])}'
        await ctx.send(f"**Global Verification Question** 🌐:\n{question_text}\n\nThis post will be deleted in 60 seconds.", delete_after=60)

    @verifyconfig.command()
    async def addmember(self, ctx: commands.Context, user: discord.Member, member_id: str):
        """Manually add a member's ID and verify them."""
        async with self.config.verified_members() as verified_members:
            verified_members[str(user.id)] = member_id

        # Grant the verified role in ALL servers where this user exists and verification is enabled
        for guild in self.bot.guilds:
            guild_member = guild.get_member(user.id)
            if not guild_member:
                continue

            verification_enabled = await self.config.guild(guild).verification_enabled()
            if not verification_enabled:
                continue

            role_id = await self.config.guild(guild).role_id()
            role = get(guild.roles, id=role_id) if role_id else None

            self.bot.dispatch('member_verified', guild, guild_member, member_id)

            if role and role not in guild_member.roles:
                try:
                    await guild_member.add_roles(role)
                    # Dispatch verification event for each server
                except discord.Forbidden:
                    pass  # Ignore permission errors

        await ctx.send(f"{user.name} has been manually verified with member ID: {member_id}.")

    @verifyconfig.command()
    async def removemember(self, ctx: commands.Context, user: discord.Member):
        """Remove a member's global verification record and roles from all servers."""
        verified_members = await self.config.verified_members()
        if str(user.id) not in verified_members:
            await ctx.send(f"{user.display_name} is not in the global verified members list.")
            return

        # Remove from global verified members
        async with self.config.verified_members() as global_verified:
            del global_verified[str(user.id)]

        # Remove verified role from all servers where user exists
        servers_processed = []
        for guild in self.bot.guilds:
            guild_member = guild.get_member(user.id)
            if not guild_member:
                continue

            verification_enabled = await self.config.guild(guild).verification_enabled()
            if not verification_enabled:
                continue

            role_id = await self.config.guild(guild).role_id()
            role = get(guild.roles, id=role_id) if role_id else None

            if role and role in guild_member.roles:
                try:
                    await guild_member.remove_roles(role)
                    servers_processed.append(guild.name)
                except discord.Forbidden:
                    pass  # Ignore permission errors

        status_msg = f"Removed verification record for {user.display_name}"
        if servers_processed:
            status_msg += f" and removed verified role from {len(servers_processed)} server(s): {', '.join(servers_processed)}"

        await ctx.send(status_msg + ".")

    @verifyconfig.command()
    async def checkuser(self, ctx: commands.Context, user: discord.Member):
        """Check if a user is globally verified and show their member ID."""
        verified_members = await self.config.verified_members()
        user_id = str(user.id)

        if user_id in verified_members:
            member_id = verified_members[user_id]
            role_id = await self.config.guild(ctx.guild).role_id()

            if role_id:
                role = get(ctx.guild.roles, id=role_id)
                has_role = role in user.roles if role else False

            # Check how many servers this user has verified role in
            verified_servers = []
            for guild in self.bot.guilds:
                guild_member = guild.get_member(user.id)
                if not guild_member:
                    continue

                verification_enabled = await self.config.guild(guild).verification_enabled()
                if not verification_enabled:
                    continue

                verified_servers.append(guild.name)

            embed = discord.Embed(title="User Verification Status", color=0x00ff00)
            embed.add_field(name="User", value=user.mention, inline=True)
            embed.add_field(name="Member ID", value=member_id, inline=True)
            if role_id:
                embed.add_field(name="Has Role (This Server)", value=has_role, inline=True)
            embed.add_field(name="Verified Servers", value=f"{len(verified_servers)} servers" if verified_servers else "None", inline=True)
            if verified_servers:
                embed.add_field(name="Server Names", value=", ".join(verified_servers), inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"{user.display_name} is not verified.")

    @verifyconfig.command()
    async def viewmembers(self, ctx: commands.Context):
        """View all verified members and their member IDs."""
        verified_members = await self.config.verified_members()
        if not verified_members:
            await ctx.send("No verified members found.")
            return

        member_list = []
        for user_id, member_id in verified_members.items():
            # Try to find the member in the current guild first, then any guild
            member = ctx.guild.get_member(int(user_id))
            if not member:
                # Look for the member in other guilds
                for guild in self.bot.guilds:
                    member = guild.get_member(int(user_id))
                    if member:
                        break

            if member:
                member_list.append(
                    f"{member.display_name} ({member.id}): Member ID {member_id}"
                )
            else:
                member_list.append(f"Unknown User ({user_id}): Member ID {member_id}")

        if member_list:
            message = f"Verified Members ({len(member_list)} total):\n" + "\n".join(member_list)
            # Split long messages
            if len(message) > 2000:
                for i in range(0, len(message), 1900):
                    await ctx.send(message[i : i + 1900])
            else:
                await ctx.send(message)

    @verifyconfig.command()
    async def setsecret(self, ctx: commands.Context, *, secret: str):
        """Set the JWT secret for verification tokens (global setting).

        The secret must be at least 32 characters long for security.
        This will invalidate all existing verification tokens across all servers.
        """
        if len(secret) < 32:
            await ctx.send("❌ JWT secret must be at least 32 characters long for security.")
            return

        await self.config.jwt_secret.set(secret)
        await ctx.send(
            "✅ JWT secret has been set successfully. All existing verification tokens are now invalid."
        )

    @verifyconfig.command()
    async def setport(self, ctx: commands.Context, port: int):
        """Set the port for the verification web server (global setting).

        The port must be between 1024 and 65535.
        """
        if port < 1024 or port > 65535:
            await ctx.send("❌ Port must be between 1024 and 65535.")
            return

        await self.config.port.set(port)
        await ctx.send(f"✅ Verification web server port has been set to {port}. Please restart the bot for the change to take effect.")

    @verifyconfig.command()
    async def url(self, ctx: commands.Context, url: str):
        """Set the verification URL base (where users will be sent for verification)."""
        if not url.startswith(('http://', 'https://')):
            await ctx.send("URL must start with http:// or https://")
            return

        await self.config.verification_url.set(url)
        await ctx.send(f"The verification URL has been set to: {url}")

    @verifyconfig.command()
    async def incorrectanswers(self, ctx: commands.Context, limit: int = 20):
        """View logged incorrect answers grouped by normalized form with statistics.

        Args:
            limit: Maximum number of entries to show (default: 20)
        """
        incorrect_answers = await self.config.incorrect_answers()

        if not incorrect_answers:
            await ctx.send("No incorrect answers have been logged yet.")
            return

        # Sort entries by count (descending) then by last seen (most recent first)
        sorted_entries = sorted(
            incorrect_answers.items(),
            key=lambda x: (x[1]["count"], x[1]["last_seen"]),
            reverse=True
        )

        # Limit the results
        if limit > 0:
            sorted_entries = sorted_entries[:limit]

        embed = discord.Embed(
            title=f"Incorrect Answers Log (Top {len(sorted_entries)})",
            description=f"Total unique incorrect answers: {len(incorrect_answers)}",
            color=0xff6b6b
        )

        current_time = int(time.time())

        for normalized_answer, data in sorted_entries:
            count = data["count"]
            original_forms = data.get("original_forms", [normalized_answer])
            first_seen = data["first_seen"]
            last_seen = data["last_seen"]
            unique_users = len(data.get("users", []))

            # Calculate time since last seen
            time_diff = current_time - last_seen
            if time_diff < 3600:  # Less than 1 hour
                time_str = f"{time_diff // 60}m ago"
            elif time_diff < 86400:  # Less than 1 day
                time_str = f"{time_diff // 3600}h ago"
            else:  # 1 day or more
                time_str = f"{time_diff // 86400}d ago"

            # Show up to 3 original forms, truncate if more
            forms_display = ", ".join(f'"{form}"' for form in original_forms[:3])
            if len(original_forms) > 3:
                forms_display += f" (+{len(original_forms) - 3} more)"

            field_name = f"#{count} attempts • {unique_users} users • {time_str}"
            field_value = f"**Forms:** {forms_display}\n**Normalized:** `{normalized_answer}`"

            # Truncate field value if too long
            if len(field_value) > 1024:
                field_value = field_value[:1020] + "..."

            embed.add_field(name=field_name, value=field_value, inline=False)

        # Add summary statistics
        total_attempts = sum(data["count"] for data in incorrect_answers.values())
        embed.set_footer(text=f"Total incorrect attempts: {total_attempts}")

        await ctx.send(embed=embed)

    @verifyconfig.command()
    async def clearincorrectanswers(self, ctx: commands.Context):
        """Clear all logged incorrect answers (requires confirmation)."""
        incorrect_answers = await self.config.incorrect_answers()

        if not incorrect_answers:
            await ctx.send("No incorrect answers to clear.")
            return

        total_entries = len(incorrect_answers)
        total_attempts = sum(data["count"] for data in incorrect_answers.values())

        # Ask for confirmation
        confirm_msg = await ctx.send(
            f"⚠️ This will permanently delete {total_entries} unique incorrect answers "
            f"({total_attempts} total attempts). React with ✅ to confirm or ❌ to cancel."
        )
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")

        def check(reaction, user):
            return (
                user == ctx.author and
                reaction.message.id == confirm_msg.id and
                str(reaction.emoji) in ["✅", "❌"]
            )

        try:
            reaction, user = await self.bot.wait_for("reaction_add", check=check, timeout=30.0)
            await confirm_msg.delete()
        except asyncio.TimeoutError:
            await ctx.send("Clear operation cancelled due to timeout.")
            await confirm_msg.delete()
            return

        if str(reaction.emoji) == "❌":
            await ctx.send("Clear operation cancelled.")
            return

        # Clear the data
        await self.config.incorrect_answers.set({})
        await ctx.send(f"✅ Cleared {total_entries} unique incorrect answers ({total_attempts} total attempts).")

    async def red_delete_data_for_user(self, **kwargs):
        """Delete user data when requested."""
        user_id = kwargs.get("user_id")
        if user_id:
            # Remove user from verification records
            async with self.config.verified_members() as verified_members:
                if str(user_id) in verified_members:
                    del verified_members[str(user_id)]
