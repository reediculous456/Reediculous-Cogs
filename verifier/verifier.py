from datetime import datetime, timezone
from typing import Literal, Optional

import discord
from discord.ext import tasks
from red_commons.logging import getLogger
from redbot.core import Config, checks, commands
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import humanize_list

log = getLogger("red.reediculous456.Verifier")

default_greeting = "Welcome {0.name} to {1.name}!"
default_goodbye = "See you later {0.name}!"
default_bot_msg = "Hello {0.name}, fellow bot!"
default_settings = {
    "GREETING": [default_greeting],
    "ON": False,
    "LEAVE_ON": False,
    "LEAVE_CHANNEL": None,
    "GROUPED": False,
    "GOODBYE": [default_goodbye],
    "CHANNEL": None,
    "WHISPER": False,
    "BOTS_MSG": default_bot_msg,
    "BOTS_GOODBYE_MSG": "Goodbye {0.name}, fellow bot!",
    "BOTS_ROLE": None,
    "EMBED": False,
    "JOINED_TODAY": False,
    "MINIMUM_DAYS": 0,
    "DELETE_PREVIOUS_GREETING": False,
    "DELETE_AFTER_GREETING": None,
    "DELETE_PREVIOUS_GOODBYE": False,
    "DELETE_AFTER_GOODBYE": None,
    "LAST_GREETING": None,
    "FILTER_SETTING": None,
    "LAST_GOODBYE": None,
    "MENTIONS": {"users": True, "roles": False, "everyone": False},
    "GOODBYE_MENTIONS": {"users": True, "roles": False, "everyone": False},
    "EMBED_DATA": {
        "title": None,
        "colour": 0,
        "colour_goodbye": 0,
        "footer": None,
        "thumbnail": "avatar",
        "image": None,
        "image_goodbye": None,
        "icon_url": None,
        "author": True,
        "timestamp": True,
        "mention": False,
    },
}

class Verifier(commands.Cog):
  """My custom cog"""

  def __init__(self, bot):
    self.bot = bot
    self.config = Config.get_conf(self, 144465786453, force_registration=True)
    self.config.register_guild(**default_settings)
    self.joined = {}
    self.today_count = {"now": datetime.now(timezone.utc)}
    self.detect_joins.start()

  @commands.group()
  @checks.admin_or_permissions(manage_channels=True)
  @commands.guild_only()
  async def verifyset(self, ctx: commands.Context) -> None:
      """Sets verifier module settings"""
      pass

  @tasks.loop(seconds=10)
  async def detect_joins(self) -> None:
      clear_guilds = []
      for guild_id, members in self.joined.items():
          if members:
              last_time_id = await self.config.guild_from_id(guild_id).LAST_GREETING()
              if last_time_id is not None:
                  last_time = (
                      datetime.now(timezone.utc) - discord.utils.snowflake_time(last_time_id)
                  ).total_seconds()
                  if len(members) > 1 and last_time <= 30.0:
                      continue
              try:
                  await self.send_member_join(members, self.bot.get_guild(guild_id))
                  clear_guilds.append(guild_id)
              except Exception:
                  log.exception("Error in group welcome:")
      for guild_id in clear_guilds:
          try:
              del self.joined[guild_id]
          except KeyError:
              pass