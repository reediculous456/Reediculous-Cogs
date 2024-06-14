from .quote_otd import QuoteOfTheDay

async def setup(bot):
    await bot.add_cog(QuoteOfTheDay(bot))