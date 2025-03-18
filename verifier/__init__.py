from .verifier import Verifier
from redbot.core.utils import get_end_user_data_statement

async def setup(bot):
    await bot.add_cog(Verifier(bot))

__red_end_user_data_statement__ = get_end_user_data_statement(__file__)
