import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import json
import pytz
import os
import random
from datetime import datetime, timedelta

STREAK = 0
COMMANDS_CHANNEL_ID = 1495506889385971893
STREAK_PASS_THRESHOLD = 5

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.environ.get("DISCORD_CHANNEL_ID", "0"))
MESSAGE_TIME = os.environ.get("DAILY_MESSAGE_TIME", "09:00")
TIMEZONE = os.environ.get("TIMEZONE", "UTC")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))

BOT_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(BOT_DIR, "images")

# Debug: Print the path when bot starts
print(f"[DEBUG] Looking for images at: {IMAGES_DIR}")
print(f"[DEBUG] Directory exists: {os.path.exists(IMAGES_DIR)}")
if os.path.exists(IMAGES_DIR):
    files = os.listdir(IMAGES_DIR)
    print(f"[DEBUG] Files in images directory: {files}")

PAIRS = [
    {
        "message": "@everyone Heyyy endmin, hope you're doing okay today… I mean, not to pressure you or anything but…\nDID YOU DO YOUR DAILYS YET??? ",
        "image": "image1.jpg",
    },
    {
        "message": "@everyone Hey endmin… quick question… small tiny question… nothing serious…\nWHERE. ARE. YOUR. DAILYS.",
        "image": "image2.jpg",
    },
    {
        "message": "@everyone Hey endmin :) hope you're having a good day… just wondering…\nARE YOUR DAILYS DONE OR ARE WE SLACKING TODAY???",
        "image": "image3.jpg",
    },
    {
        "message": "@everyone Hey my dear endmin… how are you today? I was just thinking about you and wanted to check in…\ntell me…\nhave you done your dailys yet? 💛",
        "image": "image4.jpg",
    },
    {
        "message": "@everyone Hey my deares Endmin… how are you today? I was just thinking about you and wanted to check in…\ntell me…\nhave you done your dailys yet? 💛",
        "image": "image5.jpg",
    },
]

EIGHT_BALL_RESPONSES = [
    "It is certain.", "It is decidedly so.", "Without a doubt.",
    "Yes, definitely.", "You may rely on it.", "As I see it, yes.",
    "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
    "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
    "Cannot predict now.", "Concentrate and ask again.",
    "Don't count on it.", "My reply is no.", "My sources say no.",
    "Outlook not so good.", "Very doubtful.",
]

ROAST_MESSAGES = [
    "Coming soon... 👀",
]

BOT_START_TIME = datetime.utcnow()

# Tracks the last day each user ran /list, keyed by user_id -> "YYYY-MM-DD" in TIMEZONE
LAST_LIST_USE = {}

# When True, users can only run /list once per day. Togglable via /dailylimit.
DAILY_LIMIT_ENABLED = True

# Persistent state file
STATE_FILE = os.path.join(os.path.dirname(__file__), "bot_state.json")

# Track today's scores: user_id -> score (reset each day)
DAILY_SCORES = {}


def load_state() -> None:
    global STREAK, LAST_LIST_USE, DAILY_LIMIT_ENABLED, DAILY_SCORES
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        STREAK = int(data.get("streak", 0))
        LAST_LIST_USE = {int(k): v for k, v in data.get("last_list_use", {}).items()}
        DAILY_LIMIT_ENABLED = bool(data.get("daily_limit_enabled", True))
        DAILY_SCORES = {int(k): v for k, v in data.get("daily_scores", {}).items()}
        print(
            f"[INFO] Loaded state: streak={STREAK}, "
            f"{len(LAST_LIST_USE)} user(s) tracked, "
            f"daily_limit={'on' if DAILY_LIMIT_ENABLED else 'off'}"
        )
    except FileNotFoundError:
        print("[INFO] No state file yet — starting fresh")
    except Exception as e:
        print(f"[ERROR] Failed to load state file: {e}")


def save_state() -> None:
    try:
        data = {
            "streak": STREAK,
            "last_list_use": {str(k): v for k, v in LAST_LIST_USE.items()},
            "daily_limit_enabled": DAILY_LIMIT_ENABLED,
            "daily_scores": {str(k): v for k, v in DAILY_SCORES.items()},
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to save state file: {e}")


load_state()


def _today_key() -> str:
    try:
        tz = pytz.timezone(TIMEZONE)
    except Exception:
        tz = pytz.utc
    return datetime.now(tz).strftime("%Y-%m-%d")


def get_seconds_until_next_send(hour: int, minute: int, tz) -> float:
    now = datetime.now(tz)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


async def send_daily_pair(channel):
    pair = random.choice(PAIRS)
    image_path = os.path.join(IMAGES_DIR, pair["image"])
    with open(image_path, "rb") as img_file:
        await channel.send(
            pair["message"],
            file=discord.File(img_file, filename=pair["image"])
        )
    return pair


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


@bot.event
async def on_ready():
    print(f"[INFO] Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"[INFO] Target channel ID : {CHANNEL_ID}")
    print(f"[INFO] Message time      : {MESSAGE_TIME} ({TIMEZONE})")
    print(f"[INFO] Rotating between  : {len(PAIRS)} message+image pairs")
    try:
        synced = await bot.tree.sync()
        print(f"[INFO] Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"[ERROR] Failed to sync slash commands: {e}")


@bot.tree.command(name="ping", description="Check if the bot is alive")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"Pong! I'm alive and well. Latency: {latency}ms")


@bot.tree.command(name="perlica", description="Send a random Perlica image")
async def perlica(interaction: discord.Interaction):
    images = [f for f in os.listdir(IMAGES_DIR) if f.endswith(".jpg")]
    if not images:
        await interaction.response.send_message("No images found!")
        return
    chosen = random.choice(images)
    image_path = os.path.join(IMAGES_DIR, chosen)
    with open(image_path, "rb") as img_file:
        await interaction.response.send_message(file=discord.File(img_file, filename=chosen))
    print(f"[INFO] /perlica used by {interaction.user} — sent {chosen}")


@bot.tree.command(name="roll", description="Roll a dice")
@app_commands.describe(sides="Number of sides on the dice (default 6)")
async def roll(interaction: discord.Interaction, sides: int = 6):
    if sides < 2:
        await interaction.response.send_message("A dice needs at least 2 sides!")
        return
    result = random.randint(1, sides)
    await interaction.response.send_message(f"🎲 You rolled a **{result}** (d{sides})")


@bot.tree.command(name="coinflip", description="Flip a coin")
async def coinflip(interaction: discord.Interaction):
    result = random.choice(["Heads", "Tails"])
    await interaction.response.send_message(f"🪙 **{result}!**")


@bot.tree.command(name="8ball", description="Ask the magic 8-ball a question")
@app_commands.describe(question="Your question for the 8-ball")
async def eight_ball(interaction: discord.Interaction, question: str):
    response = random.choice(EIGHT_BALL_RESPONSES)
    await interaction.response.send_message(f"🎱 *{question}*\n**{response}**")


@bot.tree.command(name="uptime", description="Show how long the bot has been running")
async def uptime(interaction: discord.Interaction):
    delta = datetime.utcnow() - BOT_START_TIME
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    days = hours // 24
    hours = hours % 24
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    await interaction.response.send_message(f"I've been running for **{' '.join(parts)}**")

@bot.tree.command(name="testdaily", description="Test the daily message feature (owner only)")
async def testdaily(interaction: discord.Interaction):
    if OWNER_ID == 0 or interaction.user.id != OWNER_ID:
        await interaction.response.send_message(
            "❌ Only the bot owner can use this command.",
            ephemeral=True,
        )
        return
    
    await interaction.response.defer()
    
    # Validate channel ID
    if CHANNEL_ID == 0:
        await interaction.followup.send(
            "❌ DISCORD_CHANNEL_ID environment variable is not set."
        )
        return
    
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        await interaction.followup.send(
            f"❌ Could not find channel with ID {CHANNEL_ID}. Make sure the bot has access to it."
        )
        return
    
    # Check if images directory exists
    if not os.path.exists(IMAGES_DIR):
        await interaction.followup.send(
            f"❌ Images directory not found at: {IMAGES_DIR}"
        )
        print(f"[ERROR] Images directory missing: {IMAGES_DIR}")
        return
    
    # Check if image files exist
    images = [f for f in os.listdir(IMAGES_DIR) if f.endswith(".jpg")]
    if not images:
        await interaction.followup.send(
            f"❌ No .jpg image files found in {IMAGES_DIR}"
        )
        print(f"[ERROR] No images found in {IMAGES_DIR}")
        return
    
    try:
        # Send the daily pair
        pair = await send_daily_pair(channel)
        await interaction.followup.send(
            f"✅ Test message sent!\n"
            f"**Image:** {pair['image']}\n"
            f"**Message preview:** {pair['message'][:100]}..."
        )
        print(f"[INFO] Test daily message sent by {interaction.user}")
        
        # Send the follow-up message
        await asyncio.sleep(2)
        await channel.send(
            f"@everyone Also don't forget to say if you did or didn't do your dailys, "
            f"in the commands channel <#{COMMANDS_CHANNEL_ID}>."
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Bot is missing permissions to send messages in the target channel."
        )
        print("[ERROR] Missing permissions to send messages in test channel.")
    except FileNotFoundError as e:
        await interaction.followup.send(
            f"❌ Error: Image file not found.\n"
            f"Details: {str(e)}"
        )
        print(f"[ERROR] Image file not found: {e}")
    except Exception as e:
        await interaction.followup.send(
            f"❌ Error sending test message: {str(e)}"
        )
        print(f"[ERROR] Failed to send test message: {e}")


@bot.tree.command(name="nextdaily", description="Time until the next daily reminder")
async def nextdaily(interaction: discord.Interaction):
    try:
        hour, minute = [int(x) for x in MESSAGE_TIME.split(":")]
        tz = pytz.timezone(TIMEZONE)
    except Exception:
        await interaction.response.send_message("Couldn't calculate the next daily time. Check the bot configuration.")
        return
    seconds = get_seconds_until_next_send(hour, minute, tz)
    now = datetime.now(tz)
    next_send = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if next_send <= now:
        next_send += timedelta(days=1)
    h, rem = divmod(int(seconds), 3600)
    m = rem // 60
    await interaction.response.send_message(
        f"Next daily message in **{h}h {m}m** — at {next_send.strftime('%Y-%m-%d %H:%M %Z')}"
    )


@bot.tree.command(name="poll", description="Create a yes/no poll")
@app_commands.describe(question="The poll question")
async def poll(interaction: discord.Interaction, question: str):
    embed = discord.Embed(
        title="HEhehe",
        description=question,
        color=discord.Color.blurple()
    )
    embed.set_footer(text=f"Asked by {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)
    msg = await interaction.original_response()
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")


@bot.tree.command(name="roast", description="Get a roast")
async def roast(interaction: discord.Interaction):
    if len(ROAST_MESSAGES) == 1 and ROAST_MESSAGES[0] == "Coming soon... 👀":
        await interaction.response.send_message("Roast messages are coming soon! 👀")
        return
    chosen = random.choice(ROAST_MESSAGES)
    await interaction.response.send_message(chosen)
    print(f"[INFO] /roast used by {interaction.user}")


@bot.tree.command(name="streak", description="Show the current daily streak")
async def streak(interaction: discord.Interaction):
    await interaction.response.send_message(f"🔥 Current daily streak: **{STREAK} days**")


@bot.tree.command(
    name="dailylimit",
    description="Enable or disable the once-per-day /list restriction (owner only)",
)
@app_commands.describe(enabled="True to enforce once-per-day, False to allow unlimited /list uses")
async def dailylimit(interaction: discord.Interaction, enabled: bool):
    global DAILY_LIMIT_ENABLED
    if OWNER_ID == 0 or interaction.user.id != OWNER_ID:
        await interaction.response.send_message(
            "❌ Only the bot owner can use this command.",
            ephemeral=True,
        )
        return
    DAILY_LIMIT_ENABLED = enabled
    save_state()
    status = "**enabled**" if enabled else "**disabled**"
    note = (
        "users can only run `/list` once per day."
        if enabled
        else "users can run `/list` as many times as they want."
    )
    await interaction.response.send_message(
        f"🔒 Daily `/list` restriction is now {status} — {note}"
    )
    print(f"[INFO] /dailylimit set to {enabled} by {interaction.user}")


@bot.tree.command(name="mb", description="Confess you didn't do your dailys")
async def mb(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"Unfortunately {interaction.user.mention} didn't complete his dailys, "
        f"he either forgot or was too busy to play the game, he'll remember next time ! ♡"
    )


@bot.tree.command(name="reminder", description="Set a personal reminder")
@app_commands.describe(
    minutes="How many minutes from now (1–1440)",
    message="What to remind you about",
)
async def reminder(interaction: discord.Interaction, minutes: int, message: str):
    if minutes < 1:
        await interaction.response.send_message("Please set a reminder for at least 1 minute.")
        return
    if minutes > 1440:
        await interaction.response.send_message("Maximum reminder time is 1440 minutes (24 hours).")
        return

    await interaction.response.send_message(
        f"Got it! I'll remind you about **{message}** in **{minutes} minute(s)**."
    )

    user = interaction.user
    channel = interaction.channel

    async def send_reminder():
        try:
            await asyncio.sleep(minutes * 60)
            if channel is not None:
                await channel.send(f"{user.mention} Reminder: **{message}**")
        except Exception as e:
            print(f"[ERROR] Reminder failed for {user}: {e}")

    asyncio.create_task(send_reminder())
    print(f"[INFO] /reminder set by {user} — {minutes}min — {message}")


@bot.tree.command(name="list", description="Start the interactive Arknights daily checklist")
async def list_cmd(interaction: discord.Interaction):
    print(f"[DEBUG] /list called by {interaction.user}", flush=True)
    await interaction.response.defer()

    today = _today_key()
    if DAILY_LIMIT_ENABLED and LAST_LIST_USE.get(interaction.user.id) == today:
        await interaction.followup.send(
            f"{interaction.user.mention} you already checked your daily today! Come back tomorrow ♡",
            ephemeral=True,
        )
        return

    questions = [
        "Have you collected your ship parts?",
        "Did you get all rare resources?",
        "Have you collected/shared clues?",
        "Did you do your friends' boost?",
        "Have you completed all depot missions?",
        "Did you sign in to SKPORT?",
        "Did you use all your daily sanity?",
        "Did you do your environmental monitoring?",
        "Did you complete all available events?",
        "Have you done all the quests?"
    ]

    user = interaction.user
    channel = interaction.channel

    def check(m):
        return m.author == user and m.channel == channel

    preview = "\n".join([f"⬜ {q}" for q in questions])
    embed = discord.Embed(
        title="📋 Daily Checklist",
        description=preview,
        color=discord.Color.orange()
    )
    await interaction.followup.send(embed=embed)
    await channel.send("Do you want to go **step-by-step** or answer **all at once**? (type `step` or `all`)")

    try:
        mode_msg = await bot.wait_for("message", timeout=30.0, check=check)
    except asyncio.TimeoutError:
        await channel.send("⏰ You took too long. Cancelled.")
        return

    mode = mode_msg.content.lower()

    if mode == "step":
        await channel.send("Starting step-by-step checklist...")
        score = 0
        for q in questions:
            await channel.send(f"❓ {q}")
            try:
                msg = await bot.wait_for("message", timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await channel.send("⏰ Timeout. Stopping checklist.")
                return
            answer = msg.content.lower()
            if answer == "yes":
                score += 1
                await channel.send("👍 Good.")
            elif answer == "no":
                await channel.send("⏭ Skipped.")
            else:
                await channel.send("⚠️ Invalid answer, counted as no.")
        await channel.send("✅ Checklist completed!")

        total = len(questions)
        if score < total:
            missing = total - score
            await channel.send(
                f"You have **{missing}** missing task(s). "
                "Do you want to **do them now** or **skip**? (type `yes` or `no`)"
            )
            try:
                decision_msg = await bot.wait_for("message", timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await channel.send("⏰ Too slow. Counting current score.")
                await apply_streak_result(channel, interaction.user.id, score, total)
                return
            decision = decision_msg.content.lower()
            if decision == "yes":
                await channel.send("👍 No problem, just re-use `/list` when you're done!")
                return
            elif decision == "no":
                await apply_streak_result(channel, interaction.user.id, score, total)
                return
            else:
                await channel.send("Invalid choice — counting current score.")
                await apply_streak_result(channel, interaction.user.id, score, total)
                return
        else:
            await apply_streak_result(channel, interaction.user.id, score, total)

    elif mode == "all":
        await channel.send("Okay! Answer **yes** if you completed everything, or **no** if you missed something.")
        try:
            msg = await bot.wait_for("message", timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await channel.send("⏰ Too slow. Cancelled.")
            return
        answer = msg.content.lower()

        if answer == "yes":
            await channel.send(f"📊 Perfect! You completed **{len(questions)}/{len(questions)}** tasks.")
            await apply_streak_result(channel, interaction.user.id, len(questions), len(questions))
            return

        elif answer == "no":
            await channel.send(
                "❌ What are you missing? "
                "Reply with question numbers separated by spaces (example: `1 5 6`)"
            )
            try:
                msg2 = await bot.wait_for("message", timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await channel.send("⏰ Too slow. Cancelled.")
                return
            missing_numbers = msg2.content.split()

            await channel.send("Do you want to **do them now** or **skip**? (type `yes` or `no`)")
            try:
                msg3 = await bot.wait_for("message", timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await channel.send("⏰ Too slow. Cancelled.")
                return
            decision = msg3.content.lower()

            if decision == "yes":
                await channel.send("👍 No problem, just re-use `/list` when you're done!")
                return
            elif decision == "no":
                total = len(questions)
                done_count = max(0, total - len(missing_numbers))
                await channel.send(
                    f"Final Score:\n"
                    f"Done: **{done_count}/{total}**\n"
                    f"Missing: **{len(missing_numbers)} tasks**"
                )
                await apply_streak_result(channel, interaction.user.id, done_count, total)
                return
            else:
                await channel.send("Invalid choice. Use `yes` or `no`.")
                return
        else:
            await channel.send("Please answer only `yes` or `no`.")
    else:
        await channel.send("Invalid option. Use `step` or `all`.")


async def apply_streak_result(channel, user_id: int, score: int, total: int):
    global STREAK, DAILY_SCORES
    today = _today_key()
    
    # Store this user's score for today
    DAILY_SCORES[user_id] = score
    
    # Check if this score qualifies (≥ threshold)
    user_qualified = score >= STREAK_PASS_THRESHOLD
    
    if user_qualified:
        await channel.send(
            f"✅ **Score: {score}/{total}** — You qualified for the streak! (≥{STREAK_PASS_THRESHOLD})"
        )
        print(f"[INFO] User {user_id} scored {score}/{total} — qualifies for streak")
    else:
        await channel.send(
            f"❌ **Score: {score}/{total}** — You didn't qualify for the streak. (needed ≥{STREAK_PASS_THRESHOLD})"
        )
        print(f"[INFO] User {user_id} scored {score}/{total} — does not qualify for streak")
    
    # Check how many users qualified today
    qualified_users = [uid for uid, s in DAILY_SCORES.items() if s >= STREAK_PASS_THRESHOLD]
    
    print(f"[DEBUG] Qualified users today: {len(qualified_users)} — {qualified_users}")
    
    # If exactly 2 users qualified, increase streak
    if len(qualified_users) >= 2:
        STREAK += 1
        await channel.send(
            f"🔥 **BOTH USERS QUALIFIED!** The shared streak is now **{STREAK} days**! 🎉"
        )
        print(f"[INFO] Streak increased to {STREAK} (both users qualified)")
    elif len(qualified_users) == 1:
        await channel.send(
            f"⏳ Waiting for the second user to qualify... (1/2 qualified)"
        )
        print(f"[INFO] 1/2 users qualified today")
    
    # Mark this user as having used /list today
    LAST_LIST_USE[user_id] = today
    save_state()


HELP_PAGES = [
    {
        "title": "📖 Help — Page 1/4 — Overview",
        "color": discord.Color.blurple(),
        "description": (
            "Welcome! Use the buttons below to flip through the pages.\n\n"
            "**🎮 Fun** — games & random stuff\n"
            "**📅 Daily** — Arknights dailys tracking\n"
            "**🛠 Utility** — bot info & helpers"
        ),
        "fields": [],
    },
    {
        "title": "🎮 Help — Page 2/4 — Fun",
        "color": discord.Color.green(),
        "description": "Just for fun!",
        "fields": [
            ("/8ball <question>", "Ask the magic 8-ball"),
            ("/roll [sides]", "Roll a dice (default 6 sides)"),
            ("/coinflip", "Flip a coin"),
            ("/roast", "Get a roast (coming soon)"),
            ("/perlica", "Send a random Perlica image"),
            ("/say", "Say 'im here'"),
        ],
    },
    {
        "title": "📅 Help — Page 3/4 — Daily",
        "color": discord.Color.orange(),
        "description": "Track your Arknights Endfield dailys.",
        "fields": [
            ("/list", "Start the daily checklist (score ≥5 grows the streak)"),
            ("/mb", "Confess you didn't do your dailys"),
            ("/streak", "Show the current shared daily streak"),
            ("/nextdaily", "Time until the next daily reminder"),
            ("/dailylimit <enabled>", "Owner: toggle the once-per-day /list restriction"),
        ],
    },
    {
        "title": "🛠 Help — Page 4/4 — Utility",
        "color": discord.Color.greyple(),
        "description": "Useful bot commands.",
        "fields": [
            ("/ping", "Check the bot latency"),
            ("/uptime", "How long the bot has been running"),
            ("/reminder <min> <msg>", "Get a reminder after X minutes"),
            ("/poll <question>", "Create a yes/no poll"),
            ("/help", "Show this help menu"),
        ],
    },
]


def build_help_embed(page_index: int) -> discord.Embed:
    page = HELP_PAGES[page_index]
    embed = discord.Embed(
        title=page["title"],
        description=page["description"],
        color=page["color"],
    )
    for name, value in page["fields"]:
        embed.add_field(name=name, value=value, inline=False)
    embed.set_footer(text=f"Page {page_index + 1} of {len(HELP_PAGES)}")
    return embed


class HelpView(discord.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.page = 0
        self._update_buttons()

    def _update_buttons(self):
        self.prev_button.disabled = self.page == 0
        self.next_button.disabled = self.page == len(HELP_PAGES) - 1

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Only the user who ran `/help` can flip pages. Run `/help` yourself!",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = max(0, self.page - 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=build_help_embed(self.page), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = min(len(HELP_PAGES) - 1, self.page + 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=build_help_embed(self.page), view=self)

    @discord.ui.button(label="✖ Close", style=discord.ButtonStyle.danger)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()


@bot.tree.command(name="help", description="Show the interactive help menu")
async def help_command(interaction: discord.Interaction):
    view = HelpView(author_id=interaction.user.id)
    await interaction.response.send_message(embed=build_help_embed(0), view=view)


@bot.tree.command(name="say", description="Say 'im here'")
async def say(interaction: discord.Interaction):
    await interaction.response.send_message("im here")


async def daily_message_loop():
    await bot.wait_until_ready()

    try:
        hour, minute = [int(x) for x in MESSAGE_TIME.split(":")]
    except ValueError:
        print(f"[ERROR] Invalid DAILY_MESSAGE_TIME format '{MESSAGE_TIME}'. Use HH:MM (e.g. 09:00)")
        return

    try:
        tz = pytz.timezone(TIMEZONE)
    except pytz.UnknownTimeZoneError:
        print(f"[ERROR] Unknown timezone '{TIMEZONE}'. Defaulting to UTC.")
        tz = pytz.utc

    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        print(f"[ERROR] Could not find channel with ID {CHANNEL_ID}. Make sure the bot has access to it.")
        return

    print(f"[INFO] Daily message scheduled for {hour:02d}:{minute:02d} {TIMEZONE} in #{channel.name}")

    while not bot.is_closed():
        seconds = get_seconds_until_next_send(hour, minute, tz)
        now = datetime.now(tz)
        next_send = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_send <= now:
            next_send += timedelta(days=1)
        print(f"[INFO] Next message in {int(seconds // 3600)}h {int((seconds % 3600) // 60)}m — at {next_send.strftime('%Y-%m-%d %H:%M %Z')}")
        await asyncio.sleep(seconds)

        channel = bot.get_channel(CHANNEL_ID)
        if channel is not None:
            try:
                pair = await send_daily_pair(channel)
                print(f"[INFO] Daily message sent at {datetime.now(tz).strftime('%Y-%m-%d %H:%M %Z')}")
                print(f"[INFO] Pair used: {pair['image']} — {pair['message'][:50]}...")
                await asyncio.sleep(10)
                await channel.send(
                    f"@everyone Also don't forget to say if you did or didn't do your dailys, "
                    f"in the commands channel <#{COMMANDS_CHANNEL_ID}>."
                )
                
                # Reset daily scores at midnight
                global DAILY_SCORES
                DAILY_SCORES = {}
                print("[INFO] Daily scores reset for new day")
            except discord.Forbidden:
                print("[ERROR] Missing permissions to send messages in this channel.")
            except Exception as e:
                print(f"[ERROR] Failed to send message: {e}")
        else:
            print(f"[ERROR] Channel {CHANNEL_ID} not found when trying to send message.")

        await asyncio.sleep(60)


async def main():
    if not TOKEN:
        print("[ERROR] DISCORD_BOT_TOKEN is not set. Please add it as a secret.")
        return

    if CHANNEL_ID == 0:
        print("[ERROR] DISCORD_CHANNEL_ID is not set. Please add it as an environment variable.")
        return

    async with bot:
        bot.loop.create_task(daily_message_loop())
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
