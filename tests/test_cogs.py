import unittest
from unittest.mock import AsyncMock, MagicMock
from src.cogs.members import MembersCog, normalize_date, user_has_role
from src.config import Config


class TestCogHelpers(unittest.TestCase):
    def test_normalize_date(self):
        # Format ISO
        self.assertEqual(normalize_date("2026-09-01"), "2026-09-01")
        # Format JJ/MM/AAAA
        self.assertEqual(normalize_date("01/09/2026"), "2026-09-01")
        # Format JJ-MM-AAAA
        self.assertEqual(normalize_date("15-11-2026"), "2026-11-15")
        # Format invalide
        self.assertIsNone(normalize_date("date_invalide"))
        # None ou vide -> retourne aujourd'hui au format AAAA-MM-JJ
        today = normalize_date(None)
        self.assertIsNotNone(today)
        self.assertEqual(len(today), 10)

    def test_user_has_role(self):
        # Simuler un membre sans rôle bureau
        member = MagicMock()
        member.guild_permissions.administrator = False
        role1 = MagicMock()
        role1.name = "Membre"
        role2 = MagicMock()
        role2.name = "Visiteur"
        member.roles = [role1, role2]

        self.assertFalse(user_has_role(member, "bureau"))
        self.assertTrue(user_has_role(member, "Membre"))
        self.assertTrue(user_has_role(member, "membre"))  # Insensible à la casse

        # Simuler un membre avec rôle Bureau
        role_bureau = MagicMock()
        role_bureau.name = "Bureau"
        member.roles.append(role_bureau)
        self.assertTrue(user_has_role(member, "bureau"))

        # Simuler un administrateur
        admin_member = MagicMock()
        admin_member.guild_permissions.administrator = True
        admin_member.roles = []
        self.assertTrue(user_has_role(admin_member, "bureau"))


class TestOnMemberJoin(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.bot = MagicMock()
        self.db = MagicMock()
        self.config = Config(
            discord_token="fake_token",
            guild_id=123,
            role_bureau="bureau",
            role_membre="Membre",
            auto_assign_member_role=True,
            db_path=MagicMock(),
            log_level="INFO",
        )
        self.cog = MembersCog(self.bot, self.db, self.config)

    async def test_on_member_join_reassigns_role_if_in_db(self):
        # Le membre est présent dans la base de données
        self.db.get_member = AsyncMock(return_value={
            "discord_id": "999",
            "full_name": "Jean Dupont",
            "last_membership_date": "2026-09-01",
        })

        member = MagicMock()
        member.id = 999
        member.guild.name = "Mon Serveur"
        role_membre = MagicMock()
        role_membre.name = "Membre"
        member.guild.roles = [role_membre]
        member.roles = []
        member.add_roles = AsyncMock()

        await self.cog.on_member_join(member)

        # Vérifie que le rôle a bien été réattribué
        member.add_roles.assert_called_once_with(
            role_membre,
            reason="Réattribution automatique : membre enregistré (Jean Dupont)",
        )

    async def test_on_member_join_does_nothing_if_not_in_db(self):
        # Le membre n'est PAS dans la base
        self.db.get_member = AsyncMock(return_value=None)

        member = MagicMock()
        member.id = 888
        member.add_roles = AsyncMock()

        await self.cog.on_member_join(member)

        member.add_roles.assert_not_called()


if __name__ == "__main__":
    unittest.main()
