import discord
import random
import asyncio
import discord
from discord.ext import commands, tasks

class Prescence(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.prescence_default.start()
        self.ctfu_rgblighting.start()

    def cog_unload(self):
        self.prescence_default.cancel()

    @tasks.loop(seconds=60.0)
    async def prescence_default(self):
    	await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f'{len(self.bot.users)} users.'))

    @tasks.loop(seconds=30.0)
    async def ctfu_rgblighting(self):
    	ctfuserver = self.bot.get_guild(694217343173394432)
    	role = ctfuserver.get_role(701007133994647622)
    	await role.edit(colour=discord.Colour(random.randint(0, 0xFFFFFF)))

    @prescence_default.before_loop
    async def before_running(self):
        print('Bot setting up... Adding presence...')
        await self.bot.wait_until_ready()

    @ctfu_rgblighting.before_loop
    async def before_running(self):
        print('Bot setting up... Adding RGB Lighting for CTFU...')
        await self.bot.wait_until_ready()

def setup(bot):
	bot.add_cog(Prescence(bot))
