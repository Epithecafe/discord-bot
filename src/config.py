import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Charge les variables d'environnement depuis le fichier .env
load_dotenv()

@dataclass(frozen=True)
class Config:
    discord_token: str
    guild_id: int | None
    role_bureau: str
    role_membre: str
    auto_assign_member_role: bool
    db_path: Path
    log_level: str

def load_config() -> Config:
    token = os.getenv("DISCORD_TOKEN")
    if not token or token == "votre_token_ici":
        raise ValueError(
            "DISCORD_TOKEN n'est pas configuré. Veuillez renseigner votre token dans le fichier .env."
        )

    guild_id_str = os.getenv("GUILD_ID", "").strip()
    guild_id = int(guild_id_str) if guild_id_str.isdigit() else None

    role_bureau = os.getenv("ROLE_BUREAU", "bureau").strip()
    role_membre = os.getenv("ROLE_MEMBRE", "Membre").strip()

    auto_assign = os.getenv("AUTO_ASSIGN_MEMBER_ROLE", "true").strip().lower() in ("true", "1", "yes")

    db_path_str = os.getenv("DB_PATH", "data/members.db").strip()
    db_path = Path(db_path_str)

    log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()

    return Config(
        discord_token=token,
        guild_id=guild_id,
        role_bureau=role_bureau,
        role_membre=role_membre,
        auto_assign_member_role=auto_assign,
        db_path=db_path,
        log_level=log_level,
    )
