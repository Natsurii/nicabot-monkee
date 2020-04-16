import discord
import random
import asyncio
import discord
from discord.ext import commands, tasks

class Prescence(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.prescence_default.start()

    def cog_unload(self):
        self.prescence_default.cancel()

    @tasks.loop(seconds=60.0)
    async def prescence_default(self):
    	await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f'{len(self.bot.users)} users.'))
    	
    @prescence_default.before_loop
    async def before_running(self):
        print('Bot setting up... Adding presence...')
        await self.bot.wait_until_ready()

def setup(bot):
	bot.add_cog(Prescence(bot))
