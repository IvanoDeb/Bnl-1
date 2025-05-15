import os
import discord
from discord.ext import commands
from aiohttp import web
import asyncio

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot je online kao {bot.user}')

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

# Web server da Render ne ubije proces
async def handle(request):
    return web.Response(text="Bot radi.")

app = web.Application()
app.add_routes([web.get('/', handle)])

async def start_web():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080)))
    await site.start()

asyncio.get_event_loop().create_task(start_web())

# Pokretanje bota
bot.run(os.getenv("DISCORD_TOKEN"))
