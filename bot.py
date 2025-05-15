import discord
from discord.ext import commands, tasks
import datetime

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

# Klubovi s budžetima (int)
budgets = {
    "GNK Dinamo Zagreb": 10950000,
    "HNK Hajduk Split": 33200000,
    "HNK Rijeka": 2600000,
    "NK Osijek": 3000000,
    "NK Istra 1961": 1500000,
    "NK Šibenik": 1950000,
    "HŠK Zrinjski Mostar": 5000000,
    "NK Široki Brijeg": 1500000,
    "FK Borac Banja Luka": 4600000,
    "FK Željezničar": 10000000,
    "FK Velež Mostar": 8600000
}

players = {}  # player_id : {discord, roblox, club, contract}
loans = {}    # player_id : {original_club, loaned_to, end_date}

allowed_clubs = list(budgets.keys())

@bot.event
async def on_ready():
    print(f'Bot is online as {bot.user}')
    check_loans.start()

def format_money(amount: int) -> str:
    return f"{amount:,}".replace(",", ".") + "€"

@bot.command()
async def register(ctx, discord_user: discord.Member, roblox_username: str, club: str, contract: str):
    club_title = club.title()
    # Provjeri je li klub u listi dozvoljenih klubova (case insensitive)
    matched_clubs = [c for c in allowed_clubs if c.lower() == club.lower()]
    if not matched_clubs:
        await ctx.send(f"Klub '{club}' nije validan. Izaberi jedan od: {', '.join(allowed_clubs)}")
        return
    club = matched_clubs[0]

    if discord_user.id in players:
        await ctx.send(f"{discord_user.display_name} je već registriran u klubu {players[discord_user.id]['club']}.")
        return

    players[discord_user.id] = {
        "discord": str(discord_user),
        "roblox": roblox_username,
        "club": club,
        "contract": contract
    }
    await ctx.send(f"Igrač {discord_user.display_name} je registriran u klub {club} s ugovorom {contract}.")

@bot.command()
async def transfer(ctx, player: discord.Member, to_club: str, price: int):
    if player.id not in players:
        await ctx.send("Igrač nije registriran.")
        return

    # Provjeri postojeće klubove i klub transfera
    from_club = players[player.id]["club"]

    matched_to = [c for c in allowed_clubs if c.lower() == to_club.lower()]
    if not matched_to:
        await ctx.send(f"Klub '{to_club}' nije validan. Izaberi jedan od: {', '.join(allowed_clubs)}")
        return
    to_club = matched_to[0]

    if budgets.get(from_club) is None or budgets.get(to_club) is None:
        await ctx.send("Jedan od klubova ne postoji.")
        return

    if budgets[to_club] < price:
        await ctx.send(f"Klub {to_club} nema dovoljno budžeta za transfer.")
        return

    # Uradi transfer: odbij iz to_club, dodaj u from_club
    budgets[to_club] -= price
    budgets[from_club] += price
    players[player.id]["club"] = to_club

    await ctx.send(f"{player.display_name} je prešao iz {from_club} u {to_club} za {format_money(price)}.")

@bot.command()
async def remove(ctx, player: discord.Member):
    if player.id in players:
        del players[player.id]
        await ctx.send(f"{player.display_name} je uklonjen iz registra.")
    else:
        await ctx.send("Igrač nije pronađen.")

@bot.command(name="players_list")
async def players_list(ctx):
    if not players:
        await ctx.send("Nema registriranih igrača.")
        return

    message = "**Registrirani igrači:**\n"
    for p in players.values():
        message += f"{p['discord']} | Roblox: {p['roblox']} | Klub: {p['club']} | Ugovor: {p['contract']}\n"
    await ctx.send(message)

@bot.command(name="budgets_list")
async def budgets_list(ctx):
    message = "**Budžeti klubova:**\n"
    for club, budget in budgets.items():
        message += f"{club}: {format_money(budget)}\n"
    await ctx.send(message)

@bot.command()
async def loan(ctx, player: discord.Member, to_club: str, contract: str):
    if player.id not in players:
        await ctx.send("Igrač nije registriran.")
        return

    matched_to = [c for c in allowed_clubs if c.lower() == to_club.lower()]
    if not matched_to:
        await ctx.send(f"Klub '{to_club}' nije validan. Izaberi jedan od: {', '.join(allowed_clubs)}")
        return
    to_club = matched_to[0]

    try:
        # Očekuje se format tipa "10d" (10 dana)
        if not contract.lower().endswith("d"):
            await ctx.send("Format ugovora je neispravan, koristi npr. '10d' za 10 dana.")
            return

        duration_days = int(contract[:-1])
        end_date = datetime.datetime.utcnow() + datetime.timedelta(days=duration_days)
    except Exception:
        await ctx.send("Format ugovora je neispravan, koristi npr. '10d' za 10 dana.")
        return

    loans[player.id] = {
        "original_club": players[player.id]["club"],
        "loaned_to": to_club,
        "end_date": end_date
    }
    players[player.id]["club"] = to_club
    await ctx.send(f"{player.display_name} je na pozajmici u {to_club} za {duration_days} dana.")

@tasks.loop(minutes=1)
async def check_loans():
    now = datetime.datetime.utcnow()
    to_remove = []
    for player_id, loan in loans.items():
        if now >= loan["end_date"]:
            players[player_id]["club"] = loan["original_club"]
            to_remove.append(player_id)
            print(f"Pozajmica završila za igrača {player_id}")

    for pid in to_remove:
        del loans[pid]

@bot.command()
async def helpbot(ctx):
    await ctx.send("""
**Dostupne komande:**
/register [@discord_user] [roblox_username] [club] [contract]  
/transfer [@discord_user] [to_club] [price]  
/remove [@discord_user]  
/players_list  
/budgets_list  
/loan [@discord_user] [to_club] [contract npr. 10d]  
""")

bot.run("MTM3MjMzNjA3ODYzNTQwNTQxMw.Gj-nyG.snZ9HfnF0gd0ioZLUtVBvRs2Z9Pg4Gx7LTaNfU")
