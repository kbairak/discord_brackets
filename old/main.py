import os

import discord
from bot import BracketsCog
from database import init_db

# Create bot instance
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = discord.Bot(intents=intents)


@bot.event
async def on_ready():
    """Called when the bot is ready."""
    if bot.user:
        print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Initializing database...")
    await init_db()
    print("Bot is ready!")


def main():
    """Main entry point."""
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("Error: DISCORD_BOT_TOKEN not found in environment variables!")
        print("Please set the DISCORD_BOT_TOKEN environment variable.")
        return

    # Add the brackets cog
    bot.add_cog(BracketsCog(bot))

    # Run the bot
    print("Starting bot...")
    bot.run(token)


if __name__ == "__main__":
    main()
