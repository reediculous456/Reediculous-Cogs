from .web_verifier import WebVerifier
from redbot.core.utils import get_end_user_data_statement

async def setup(bot):
    await bot.add_cog(WebVerifier(bot))

__red_end_user_data_statement__ = get_end_user_data_statement(__file__)
