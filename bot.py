import os
import discord
from discord.ext import commands, tasks
import datetime
from aiohttp import web
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

players = {}
budgets = {
    "GNK Dinamo Zagreb": 10_950_000,
    "HNK Hajduk Split": 33_200_000,
    "HNK Rijeka": 2_600_000,
    "NK Osijek": 3_000_000,
    "NK Istra 1961": 1_500_000,
    "NK Šibenik": 1_950_000,
    "HŠK Zrinjski Mostar": 5_000_000,
    "NK Široki Brijeg": 1_500_000,
    "FK Borac Banja Luka": 4_600_000,
    "FK Željezničar": 10_000_000,
    "FK Velež Mostar": 8_600_000
}

loans = {}

def format_currency(value):
    return f"{value:,}€".replace(",", ".")

@bot.event
async def on_ready():
    print(f'Bot is online as {bot.user}')
    check_loans.start()

@bot.command()
async def register(ctx, discord_user: discord.Member, roblox_username: str, club: str, contract: str):
    club_names = budgets.keys()
    if club not in club_names:
        await ctx.send(f"Club '{club}' does not exist. Please choose from: {', '.join(club_names)}")
        return

    if discord_user.id in players:
        await ctx.send(f"{discord_user.display_name} is already registered for {players[discord_user.id]['club']}.")
    else:
        players[discord_user.id] = {
            "discord": str(discord_user),
            "roblox": roblox_username,
            "club": club,
            "contract": contract
        }
        await ctx.send(f"Player {discord_user.display_name} registered to {club} with contract {contract}.")

@bot.command()
async def transfer(ctx, player: discord.Member, to_club: str, price: int):
    if player.id not in players:
        await ctx.send("Player is not registered.")
        return

    from_club = players[player.id]["club"]
    club_names = budgets.keys()
    if from_club not in club_names or to_club not in club_names:
        await ctx.send("One of the clubs does not exist.")
        return

    if budgets[to_club] < price:
        await ctx.send(f"{to_club} does not have enough budget.")
        return

    budgets[to_club] -= price
    budgets[from_club] += price
    players[player.id]["club"] = to_club

    await ctx.send(f"{player.display_name} transferred from {from_club} to {to_club} for {format_currency(price)}.")

@bot.command()
async def remove(ctx, player: discord.Member):
    if player.id in players:
        del players[player.id]
        await ctx.send(f"{player.display_name} removed from registry.")
    else:
        await ctx.send("Player not found.")

@bot.command(name="players_list")
async def players_list(ctx):
    if not players:
        await ctx.send("No players registered.")
        return

    message = "**Registered players:**\n"
    for p in players.values():
        message += f"{p['discord']} | Roblox: {p['roblox']} | Club: {p['club']} | Contract: {p['contract']}\n"
    await ctx.send(message)

@bot.command(name="budgets_list")
async def budgets_list(ctx):
    message = "**Club Budgets:**\n"
    for club, budget in budgets.items():
        message += f"{club}: {format_currency(budget)}\n"
    await ctx.send(message)

@bot.command()
async def loan(ctx, player: discord.Member, to_club: str, contract: str):
    if player.id not in players:
        await ctx.send("Player is not registered.")
        return

    club_names = budgets.keys()
    if to_club not in club_names:
        await ctx.send(f"Club '{to_club}' does not exist.")
        return

    try:
        duration_days = int(contract.replace("d", ""))
        end_date = datetime.datetime.utcnow() + datetime.timedelta(days=duration_days)
        loans[player.id] = {
            "original_club": players[player.id]["club"],
            "loaned_to": to_club,
            "end_date": end_date
        }
        players[player.id]["club"] = to_club
        await ctx.send(f"{player.display_name} loaned to {to_club} for {duration_days} days.")
    except Exception:
        await ctx.send("Invalid contract format. Use format like `10d` for 10 days.")

@tasks.loop(hours=24)
async def check_loans():
    now = datetime.datetime.utcnow()
    to_remove = []
    for player_id, loan in loans.items():
        if now >= loan["end_date"]:
            players[player_id]["club"] = loan["original_club"]
            to_remove.append(player_id)
    for pid in to_remove:
        del loans[pid]

@bot.command()
async def helpbot(ctx):
    await ctx.send("""
**Bot commands:**
/register [discord_user] [roblox_username] [club] [contract]  
/transfer [discord_user] [to_club] [price]  
/remove [discord_user]  
/players_list  
/budgets_list  
/loan [discord_user] [to_club] [contract, e.g. 10d]  
""")

# aiohttp web server for Render
async def handle(request):
    return web.Response(text="Bot is running")

app = web.Application()
app.add_routes([web.get('/', handle)])

port = int(os.environ.get("PORT", 8080))
runner = web.AppRunner(app)

async def start_web():
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

asyncio.get_event_loop().create_task(start_web())

bot.run(os.getenv("DISCORD_TOKEN")
