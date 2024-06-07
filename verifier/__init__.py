from .verifier import Verifier

async def setup(bot):
    await bot.add_cog(Verifier(bot))