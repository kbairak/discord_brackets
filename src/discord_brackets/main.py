import os

import discord

from . import db, views

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = discord.Bot(intents=intents)


@bot.event
async def on_ready():
    await db.init_db()
    print("Database loaded")
    bot.add_view(views.CollectionView())
    bot.add_view(views.RoundView([]))


@bot.command(description="Create a new tournament bracket")
async def brackets(ctx: discord.ApplicationContext, title: str) -> None:
    if not ctx.guild_id or not ctx.channel_id:
        await ctx.respond("This command can only be used in a server channel.", ephemeral=True)
        return
    title = title.strip()
    if not title:
        await ctx.respond("Please provide a valid title for the tournament.", ephemeral=True)
        return
    if await db.tournament_exists_in_channel(ctx.guild_id, ctx.channel_id):
        await ctx.respond(
            "A tournament already exists in this channel. Please use a different channel or end "
            "the existing tournament first.",
            ephemeral=True,
        )
        return
    tournament_id = await db.create_tournament(ctx.author.id, ctx.guild_id, ctx.channel_id, title)
    await ctx.respond(await db.get_options_text(tournament_id), view=views.CollectionView())
    message = await ctx.interaction.original_response()
    await message.pin()
    await db.pin(tournament_id, message.id)


def main():
    print("Starting bot")
    token = os.getenv("DISCORD_BOT_TOKEN")
    bot.run(token)


if __name__ == "__main__":
    main()
