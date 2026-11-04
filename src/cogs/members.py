import io
import logging
from datetime import datetime
import discord
from discord import app_commands
from discord.ext import commands

from src.config import Config
from src.database import Database

logger = logging.getLogger("chabeille.cogs.members")


def normalize_date(date_str: str | None) -> str | None:
    """Valide et convertit une date en format ISO AAAA-MM-JJ.
    
    Supporte AAAA-MM-JJ, JJ/MM/AAAA et JJ-MM-AAAA.
    """
    if not date_str or not date_str.strip():
        return datetime.now().strftime("%Y-%m-%d")

    clean_str = date_str.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(clean_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def user_has_role(member: discord.Member, role_name: str) -> bool:
    """Vérifie si un membre possède un rôle (insensible à la casse) ou est administrateur."""
    if member.guild_permissions.administrator:
        return True
    target = role_name.strip().lower()
    return any(role.name.strip().lower() == target for role in member.roles)


class MembersCog(commands.Cog, name="Gestion des membres"):
    def __init__(self, bot: commands.Bot, db: Database, config: Config):
        self.bot = bot
        self.db = db
        self.config = config

    # ------------------------------------------------------------------
    # Commande /member
    # ------------------------------------------------------------------
    @app_commands.command(
        name="member",
        description="Ajouter un membre ou enregistrer un renouvellement d'adhésion (rôle bureau requis)",
    )
    @app_commands.describe(
        user="Le compte Discord du membre",
        full_name="Le nom complet du membre (ex: John Doe)",
        date="Date de membrage au format AAAA-MM-JJ ou JJ/MM/AAAA (optionnel, aujourd'hui par défaut)",
    )
    async def member(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        full_name: str,
        date: str | None = None,
    ):
        # Vérification du contexte de serveur
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "❌ Cette commande doit être exécutée au sein d'un serveur Discord.",
                ephemeral=True,
            )
            return

        # Vérification du rôle bureau
        if not user_has_role(interaction.user, self.config.role_bureau):
            await interaction.response.send_message(
                f"❌ Vous n'avez pas la permission d'exécuter cette commande. Rôle requis : **{self.config.role_bureau}**.",
                ephemeral=True,
            )
            return

        # Validation de la date
        membership_date = normalize_date(date)
        if membership_date is None:
            await interaction.response.send_message(
                "❌ Format de date invalide. Utilisez le format `AAAA-MM-JJ` (ex: `2026-09-01`) ou `JJ/MM/AAAA` (ex: `01/09/2026`).",
                ephemeral=True,
            )
            return

        cleaned_full_name = full_name.strip()
        if not cleaned_full_name:
            await interaction.response.send_message(
                "❌ Le nom complet ne peut pas être vide.",
                ephemeral=True,
            )
            return

        # Enregistrement dans SQLite
        try:
            result = await self.db.add_or_renew_member(
                discord_id=str(user.id),
                username=str(user),
                full_name=cleaned_full_name,
                membership_date=membership_date,
                registered_by=str(interaction.user.id),
            )
        except Exception as exc:
            logger.exception("Erreur lors de l'enregistrement en base de données : %s", exc)
            await interaction.response.send_message(
                "❌ Une erreur interne est survenue lors de l'enregistrement en base de données.",
                ephemeral=True,
            )
            return

        # Attribution automatique du rôle Discord "Membre" si configuré
        role_status_msg = "Non attribué"
        if self.config.auto_assign_member_role and interaction.guild:
            target_role = discord.utils.find(
                lambda r: r.name.strip().lower() == self.config.role_membre.strip().lower(),
                interaction.guild.roles,
            )
            if target_role:
                if target_role not in user.roles:
                    try:
                        await user.add_roles(
                            target_role,
                            reason=f"Adhésion enregistrée par {interaction.user} via /member",
                        )
                        role_status_msg = f"Rôle **{target_role.name}** attribué"
                    except discord.Forbidden:
                        role_status_msg = f"⚠️ Impossible d'attribuer le rôle **{target_role.name}** (permissions insuffisantes)"
                    except Exception as err:
                        role_status_msg = f"⚠️ Erreur lors de l'attribution du rôle : {err}"
                else:
                    role_status_msg = f"Possède déjà le rôle **{target_role.name}**"
            else:
                role_status_msg = f"⚠️ Rôle **{self.config.role_membre}** introuvable sur le serveur"

        # Construction de l'embed de confirmation
        title = "🔄 Adhésion renouvelée" if result["is_renewal"] else "✅ Nouveau membre enregistré"
        color = discord.Color.green() if not result["is_renewal"] else discord.Color.blue()

        embed = discord.Embed(title=title, color=color, timestamp=datetime.now())
        embed.add_field(name="Membre Discord", value=f"{user.mention} (`{user}`)", inline=True)
        embed.add_field(name="ID Discord", value=f"`{user.id}`", inline=True)
        embed.add_field(name="Nom complet", value=cleaned_full_name, inline=False)
        embed.add_field(name="Date de membrage", value=membership_date, inline=True)
        embed.add_field(name="Rôle serveur", value=role_status_msg, inline=True)
        embed.set_footer(text=f"Enregistré par {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed)

    # ------------------------------------------------------------------
    # Commande /info
    # ------------------------------------------------------------------
    @app_commands.command(
        name="info",
        description="Recevoir par message privé ses informations et sa date de membrage (rôle Membre requis)",
    )
    @app_commands.describe(
        user="Membre dont vous souhaitez consulter les informations (optionnel, vous-même par défaut)",
    )
    async def info(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
    ):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "❌ Cette commande doit être exécutée au sein d'un serveur Discord.",
                ephemeral=True,
            )
            return

        # Accessible aux personnes ayant le rôle "Membre" ou "bureau"
        has_member_perm = user_has_role(interaction.user, self.config.role_membre)
        has_bureau_perm = user_has_role(interaction.user, self.config.role_bureau)

        if not (has_member_perm or has_bureau_perm):
            await interaction.response.send_message(
                f"❌ Vous n'avez pas la permission d'exécuter cette commande. Rôle requis : **{self.config.role_membre}**.",
                ephemeral=True,
            )
            return

        target_user = user or interaction.user
        target_id = str(target_user.id)

        try:
            data = await self.db.get_member(target_id)
        except Exception as exc:
            logger.exception("Erreur lors de la lecture en base de données : %s", exc)
            await interaction.response.send_message(
                "❌ Une erreur interne est survenue lors de la récupération des données.",
                ephemeral=True,
            )
            return

        if not data:
            target_label = "votre profil" if target_user.id == interaction.user.id else f"le membre {target_user.mention}"
            await interaction.response.send_message(
                f"ℹ️ Aucune information de membrage trouvée pour {target_label}.",
                ephemeral=True,
            )
            return

        # Formatage de l'historique
        history_list = data.get("history", [])
        if history_list:
            history_text = "\n".join(
                f"• **{h['membership_date']}** (enregistré le {h['created_at'][:10]})"
                for h in history_list[:5]
            )
            if len(history_list) > 5:
                history_text += f"\n*... et {len(history_list) - 5} autre(s) adhésion(s)*"
        else:
            history_text = f"• **{data['last_membership_date']}**"

        embed = discord.Embed(
            title="📋 Informations d'adhésion",
            color=discord.Color.gold(),
            timestamp=datetime.now(),
        )
        embed.set_thumbnail(url=target_user.display_avatar.url)
        embed.add_field(name="Nom complet", value=data["full_name"], inline=False)
        embed.add_field(name="Compte Discord", value=f"{target_user.mention} (`{data['username']}`)", inline=True)
        embed.add_field(name="ID Discord", value=f"`{data['discord_id']}`", inline=True)
        embed.add_field(name="Dernière date de membrage", value=f"📅 **{data['last_membership_date']}**", inline=False)
        embed.add_field(name="Historique des adhésions", value=history_text, inline=False)
        embed.set_footer(text=f"Serveur : {interaction.guild.name}")

        # Envoi en message privé
        try:
            await interaction.user.send(embed=embed)
            await interaction.response.send_message(
                "📩 Vos informations de membrage vous ont été envoyées en message privé !",
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "⚠️ Impossible de vous envoyer un message privé. Veuillez autoriser les MP provenant des membres de ce serveur dans vos paramètres Discord.",
                ephemeral=True,
            )
        except Exception as err:
            logger.exception("Erreur lors de l'envoi du MP : %s", err)
            await interaction.response.send_message(
                f"⚠️ Une erreur est survenue lors de l'envoi du message privé : {err}",
                ephemeral=True,
            )

    # ------------------------------------------------------------------
    # Commande /export
    # ------------------------------------------------------------------
    @app_commands.command(
        name="export",
        description="Exporter l'ensemble de la base de données des membres (CSV et SQLite, rôle bureau requis)",
    )
    async def export(self, interaction: discord.Interaction):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "❌ Cette commande doit être exécutée au sein d'un serveur Discord.",
                ephemeral=True,
            )
            return

        # Vérification du rôle bureau
        if not user_has_role(interaction.user, self.config.role_bureau):
            await interaction.response.send_message(
                f"❌ Vous n'avez pas la permission d'exporter la base de données. Rôle requis : **{self.config.role_bureau}**.",
                ephemeral=True,
            )
            return

        # Différer la réponse car l'export peut prendre quelques instants
        await interaction.response.defer(ephemeral=True)

        try:
            today_str = datetime.now().strftime("%Y-%m-%d")

            # 1. Génération du fichier CSV
            csv_str = await self.db.export_csv()
            # Encodage UTF-8 avec BOM pour assurer l'ouverture directe dans Microsoft Excel
            csv_bytes = csv_str.encode("utf-8-sig")
            csv_file = discord.File(
                fp=io.BytesIO(csv_bytes),
                filename=f"membres_{today_str}.csv",
            )

            # 2. Fichier SQLite brut
            db_bytes = self.db.get_db_file_bytes()
            files_to_send = [csv_file]
            if db_bytes:
                db_file = discord.File(
                    fp=io.BytesIO(db_bytes),
                    filename=f"members_{today_str}.db",
                )
                files_to_send.append(db_file)

            members_list = await self.db.get_all_members()
            total_members = len(members_list)

            await interaction.followup.send(
                content=(
                    f"📊 **Export de la base de données** ({total_members} membre(s) enregistré(s)) :\n"
                    f"• Fichier CSV (ouvrable dans Excel/LibreOffice/Google Sheets)\n"
                    f"• Fichier SQLite `.db` (sauvegarde brute)\n\n"
                    f"🔒 *Ce message est éphémère et visible uniquement par vous pour des raisons de confidentialité.*"
                ),
                files=files_to_send,
                ephemeral=True,
            )
        except Exception as exc:
            logger.exception("Erreur lors de l'export des données : %s", exc)
            await interaction.followup.send(
                content=f"❌ Erreur lors de l'export : {exc}",
                ephemeral=True,
            )

    # ------------------------------------------------------------------
    # Événement : retour d'un membre sur le serveur
    # ------------------------------------------------------------------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Réattribue automatiquement le rôle Membre si l'utilisateur est déjà dans la base."""
        if not self.config.auto_assign_member_role:
            return

        try:
            member_data = await self.db.get_member(str(member.id))
            if not member_data:
                return

            logger.info(
                "Le membre %s (ID: %s) a rejoint le serveur et figure dans la base SQLite (adhésion : %s).",
                member,
                member.id,
                member_data.get("last_membership_date"),
            )

            target_role = discord.utils.find(
                lambda r: r.name.strip().lower() == self.config.role_membre.strip().lower(),
                member.guild.roles,
            )

            if not target_role:
                logger.warning(
                    "Impossible de réattribuer le rôle : rôle '%s' introuvable sur le serveur %s.",
                    self.config.role_membre,
                    member.guild.name,
                )
                return

            if target_role in member.roles:
                return

            try:
                await member.add_roles(
                    target_role,
                    reason=f"Réattribution automatique : membre enregistré ({member_data.get('full_name')})",
                )
                logger.info(
                    "Rôle '%s' réattribué avec succès à %s (%s).",
                    target_role.name,
                    member,
                    member.id,
                )
            except discord.Forbidden:
                logger.warning(
                    "Permissions insuffisantes pour attribuer le rôle '%s' à %s (vérifier la hiérarchie des rôles).",
                    target_role.name,
                    member,
                )
            except Exception as role_err:
                logger.exception(
                    "Erreur lors de la réattribution du rôle '%s' à %s : %s",
                    target_role.name,
                    member,
                    role_err,
                )
        except Exception as exc:
            logger.exception("Erreur lors du traitement de l'arrivée du membre %s : %s", member, exc)


async def setup(bot: commands.Bot):
    """Fonction de chargement du Cog."""
    db: Database = bot.db  # type: ignore
    config: Config = bot.config  # type: ignore
    await bot.add_cog(MembersCog(bot, db, config))
