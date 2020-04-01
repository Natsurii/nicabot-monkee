import hikari
import logging
import os

logging.basicConfig(level='INFO')
client = hikari.Client()

def find_token():
	with open('key.token', 'r') as file:
		token = file.read()
	return token

token = find_token()
#token = os.environ['TOKEN']

prefix = 'mhik++'


@client.event()
async def on_message_create(message):
	if message.author.is_bot:
		return

	if message.content.startswith(prefix + 'ping'):
		await message.channel.send(f'Yes I received your request. {client.heartbeat_latency *1000:.0f} milliseconds.')
	if message.content.startswith(prefix + 'help'):
		message_temp = f"**Nicabot_hikari 0.0.01 Framework** \nUsage: `{prefix}[command]` \nAvailable commands: \n`ping`"
		await message.channel.send(message_temp)
client.run(token)