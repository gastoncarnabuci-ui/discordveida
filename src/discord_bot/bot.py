from __future__ import annotations

import logging
import os

import discord
from discord import app_commands
from discord.ext import commands

from .ai import AnswerService, UserCooldown

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("discord_answers_bot")

MAX_REPLY_LENGTH = 1900


def format_reply(text: str) -> str:
    """Keep generated messages below Discord's message-size limit."""
    text = text.strip()
    if len(text) <= MAX_REPLY_LENGTH:
        return text
    return text[: MAX_REPLY_LENGTH - 1].rstrip() + "…"


def build_bot() -> commands.Bot:
    intents = discord.Intents.default()
    intents.message_content = True
    answer_service = AnswerService()

    class SarcasticBot(commands.Bot):
        async def setup_hook(self) -> None:
            guild_id = os.getenv("DISCORD_GUILD_ID")
            if guild_id:
                try:
                    guild = discord.Object(id=int(guild_id))
                except ValueError as error:
                    raise RuntimeError("DISCORD_GUILD_ID debe ser un número.") from error
                self.tree.copy_global_to(guild=guild)
                commands_synced = await self.tree.sync(guild=guild)
                logger.info("Synchronized %s command(s) to the test server.", len(commands_synced))
            else:
                commands_synced = await self.tree.sync()
                logger.info("Synchronized %s global command(s).", len(commands_synced))

        async def close(self) -> None:
            await answer_service.close()
            await super().close()

    bot = SarcasticBot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready() -> None:
        if bot.user is not None:
            logger.info("Connected as %s (ID: %s).", bot.user.name, bot.user.id)

    @bot.tree.command(name="preguntar", description="Hazle una pregunta a la supercomputadora.")
    @app_commands.describe(pregunta="Tu pregunta (máximo 1500 caracteres)")
    async def preguntar(interaction: discord.Interaction, pregunta: str) -> None:
        await interaction.response.defer(thinking=True)
        channel_id = interaction.channel_id or interaction.user.id
        try:
            answer = await answer_service.answer(
                user_id=interaction.user.id,
                channel_id=channel_id,
                question=pregunta,
            )
        except UserCooldown:
            answer = "Un segundo. Incluso una supercomputadora merece procesar una sola pregunta a la vez."
        await interaction.followup.send(
            format_reply(answer),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @bot.event
    async def on_message(message: discord.Message) -> None:
        if message.author.bot or bot.user is None or bot.user not in message.mentions:
            return

        question = message.content
        question = question.replace(f"<@{bot.user.id}>", "").replace(
            f"<@!{bot.user.id}>", ""
        ).strip()
        if not question:
            await message.reply(
                "Me invocaste sin una pregunta. Qué despliegue de eficiencia humana.",
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return

        async with message.channel.typing():
            try:
                answer = await answer_service.answer(
                    user_id=message.author.id,
                    channel_id=message.channel.id,
                    question=question,
                )
            except UserCooldown:
                answer = "Dame un instante antes de la siguiente pregunta. Mis circuitos no son una ventanilla de atención."

        await message.reply(
            format_reply(answer),
            mention_author=False,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    return bot


def main() -> None:
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit("Falta el secreto DISCORD_BOT_TOKEN.")

    bot = build_bot()
    try:
        bot.run(token, log_handler=None)
    except discord.PrivilegedIntentsRequired as error:
        raise SystemExit(
            "Discord rechazó el acceso al contenido de mensajes. "
            "Activa Message Content Intent en el Developer Portal y reinicia el bot."
        ) from error
