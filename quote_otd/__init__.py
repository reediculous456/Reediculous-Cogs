from .quote_otd import QuoteOfTheDay
from redbot.core.utils import get_end_user_data_statement

async def setup(bot):
    await bot.add_cog(QuoteOfTheDay(bot))

__red_end_user_data_statement__ = get_end_user_data_statement(__file__)
