import logging
import discord
from discord.ext import commands

from src.config import Config
from src.database import Database

logger = logging.getLogger("chabeille.bot")


class ChabeilleBot(commands.Bot):
    def __init__(self, config: Config, db: Database):
        intents = discord.Intents.default()
        intents.members = True  # Nécessaire pour gérer les membres et leurs rôles
        intents.message_content = False  # Slash commands only

        super().__init__(
            command_prefix="!",  # Non utilisé car nous utilisons des commandes slash
            intents=intents,
        )
        self.config = config
        self.db = db

    async def setup_hook(self) -> None:
        """Initialise la base de données, charge les extensions et synchronise les commandes slash."""
        logger.info("Initialisation de la base de données...")
        await self.db.initialize()

        logger.info("Chargement des cogs...")
        await self.load_extension("src.cogs.members")

        logger.info("Synchronisation des commandes slash...")
        if self.config.guild_id:
            guild = discord.Object(id=self.config.guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            logger.info("Synchronisé %d commande(s) sur le serveur ID %d", len(synced), self.config.guild_id)
        else:
            synced = await self.tree.sync()
            logger.info("Synchronisé %d commande(s) globalement", len(synced))

    async def on_ready(self) -> None:
        logger.info("================================================")
        logger.info("Connecté avec succès sous : %s (ID: %s)", self.user, self.user.id if self.user else "N/A")
        logger.info("Serveurs connectés : %d", len(self.guilds))
        logger.info("================================================")

        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="les adhésions | /info",
        )
        await self.change_presence(activity=activity)
