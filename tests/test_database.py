import asyncio
import tempfile
import unittest
from pathlib import Path
from src.database import Database

class TestDatabase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_members.db"
        self.db = Database(self.db_path)
        await self.db.initialize()

    async def asyncTearDown(self):
        self.temp_dir.cleanup()

    async def test_add_and_get_member(self):
        result = await self.db.add_or_renew_member(
            discord_id="123456789",
            username="johndoe",
            full_name="John Doe",
            membership_date="2026-09-01",
            registered_by="987654321",
        )
        self.assertFalse(result["is_renewal"])
        self.assertEqual(result["full_name"], "John Doe")

        member = await self.db.get_member("123456789")
        self.assertIsNotNone(member)
        self.assertEqual(member["discord_id"], "123456789")
        self.assertEqual(member["username"], "johndoe")
        self.assertEqual(member["full_name"], "John Doe")
        self.assertEqual(member["last_membership_date"], "2026-09-01")
        self.assertEqual(len(member["history"]), 1)
        self.assertEqual(member["history"][0]["membership_date"], "2026-09-01")

    async def test_renew_member(self):
        # Première adhésion
        await self.db.add_or_renew_member(
            discord_id="123456789",
            username="johndoe",
            full_name="John Doe",
            membership_date="2025-09-01",
        )

        # Ré-adhésion l'année suivante
        result2 = await self.db.add_or_renew_member(
            discord_id="123456789",
            username="johndoe_updated",
            full_name="Johnathan Doe",
            membership_date="2026-09-01",
        )
        self.assertTrue(result2["is_renewal"])

        member = await self.db.get_member("123456789")
        self.assertEqual(member["username"], "johndoe_updated")
        self.assertEqual(member["full_name"], "Johnathan Doe")
        self.assertEqual(member["last_membership_date"], "2026-09-01")
        self.assertEqual(len(member["history"]), 2)

    async def test_export_csv_and_binary(self):
        await self.db.add_or_renew_member(
            discord_id="111",
            username="alice",
            full_name="Alice Smith",
            membership_date="2026-01-10",
        )
        await self.db.add_or_renew_member(
            discord_id="222",
            username="bob",
            full_name="Bob Martin",
            membership_date="2026-02-15",
        )

        csv_content = await self.db.export_csv()
        self.assertIn("Alice Smith", csv_content)
        self.assertIn("Bob Martin", csv_content)
        self.assertIn("111", csv_content)
        self.assertIn("222", csv_content)

        db_bytes = self.db.get_db_file_bytes()
        self.assertGreater(len(db_bytes), 0)

if __name__ == "__main__":
    unittest.main()
