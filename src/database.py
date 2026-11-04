import csv
import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
import aiosqlite

logger = logging.getLogger("chabeille.database")

class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    async def initialize(self) -> None:
        """Crée le dossier parent et les tables SQLite si nécessaires."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS members (
                    discord_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_membership_date TEXT NOT NULL
                );
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS memberships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_id TEXT NOT NULL,
                    membership_date TEXT NOT NULL,
                    registered_by TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (discord_id) REFERENCES members(discord_id) ON DELETE CASCADE
                );
                """
            )
            await db.commit()
            logger.info("Base de données initialisée à %s", self.db_path)

    async def add_or_renew_member(
        self,
        discord_id: str,
        username: str,
        full_name: str,
        membership_date: str,
        registered_by: str | None = None,
    ) -> dict[str, Any]:
        """Ajoute un nouveau membre ou renouvelle l'adhésion d'un membre existant."""
        now_iso = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            # Vérifier si le membre existe déjà
            async with db.execute(
                "SELECT discord_id, last_membership_date FROM members WHERE discord_id = ?",
                (discord_id,),
            ) as cursor:
                existing = await cursor.fetchone()

            if existing:
                # Mettre à jour last_membership_date si la nouvelle date est plus récente ou égale
                previous_date = existing[1]
                new_last_date = max(previous_date, membership_date)
                await db.execute(
                    """
                    UPDATE members
                    SET username = ?, full_name = ?, last_membership_date = ?
                    WHERE discord_id = ?
                    """,
                    (username, full_name, new_last_date, discord_id),
                )
                is_renewal = True
            else:
                await db.execute(
                    """
                    INSERT INTO members (discord_id, username, full_name, created_at, last_membership_date)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (discord_id, username, full_name, now_iso, membership_date),
                )
                is_renewal = False

            # Enregistrer l'événement dans l'historique des adhésions
            await db.execute(
                """
                INSERT INTO memberships (discord_id, membership_date, registered_by, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (discord_id, membership_date, registered_by, now_iso),
            )
            await db.commit()

        return {
            "discord_id": discord_id,
            "username": username,
            "full_name": full_name,
            "membership_date": membership_date,
            "is_renewal": is_renewal,
        }

    async def get_member(self, discord_id: str) -> dict[str, Any] | None:
        """Récupère un membre et son historique complet d'adhésions."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT discord_id, username, full_name, created_at, last_membership_date FROM members WHERE discord_id = ?",
                (discord_id,),
            ) as cursor:
                member_row = await cursor.fetchone()

            if not member_row:
                return None

            async with db.execute(
                """
                SELECT membership_date, registered_by, created_at
                FROM memberships
                WHERE discord_id = ?
                ORDER BY membership_date DESC, id DESC
                """,
                (discord_id,),
            ) as cursor:
                history_rows = await cursor.fetchall()

        return {
            "discord_id": member_row["discord_id"],
            "username": member_row["username"],
            "full_name": member_row["full_name"],
            "created_at": member_row["created_at"],
            "last_membership_date": member_row["last_membership_date"],
            "history": [dict(row) for row in history_rows],
        }

    async def get_all_members(self) -> list[dict[str, Any]]:
        """Récupère tous les membres avec leur historique concaténé."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT 
                    m.discord_id,
                    m.username,
                    m.full_name,
                    m.created_at,
                    m.last_membership_date,
                    COUNT(h.id) AS total_adhesions,
                    GROUP_CONCAT(h.membership_date, ' ; ') AS historique_dates
                FROM members m
                LEFT JOIN memberships h ON m.discord_id = h.discord_id
                GROUP BY m.discord_id
                ORDER BY m.last_membership_date DESC, m.full_name ASC
                """
            ) as cursor:
                rows = await cursor.fetchall()

        return [dict(row) for row in rows]

    async def export_csv(self) -> str:
        """Génère le contenu CSV de tous les membres."""
        members = await self.get_all_members()
        output = io.StringIO()
        writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)

        # En-têtes CSV
        writer.writerow(
            [
                "ID Discord",
                "Pseudo Discord",
                "Nom complet",
                "Dernière date de membrage",
                "Date de création fiche",
                "Nombre d'adhésions",
                "Historique des dates",
            ]
        )

        for m in members:
            writer.writerow(
                [
                    m.get("discord_id", ""),
                    m.get("username", ""),
                    m.get("full_name", ""),
                    m.get("last_membership_date", ""),
                    m.get("created_at", ""),
                    m.get("total_adhesions", 0),
                    m.get("historique_dates", "") or m.get("last_membership_date", ""),
                ]
            )

        return output.getvalue()

    def get_db_file_bytes(self) -> bytes:
        """Retourne le contenu binaire du fichier SQLite."""
        if not self.db_path.exists():
            return b""
        with open(self.db_path, "rb") as f:
            return f.read()
