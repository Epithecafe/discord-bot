import logging
import sys

from src.bot import ChabeilleBot
from src.config import load_config
from src.database import Database


def setup_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> None:
    try:
        config = load_config()
    except Exception as exc:
        print(f"\n[ERREUR DE CONFIGURATION] {exc}\n", file=sys.stderr)
        print("Veuillez copier le fichier .env.example vers .env et renseigner votre token Discord :", file=sys.stderr)
        print("  cp .env.example .env\n", file=sys.stderr)
        sys.exit(1)

    setup_logging(config.log_level)
    logger = logging.getLogger("chabeille.main")
    logger.info("Démarrage du bot Chabeille...")

    db = Database(config.db_path)
    bot = ChabeilleBot(config=config, db=db)

    try:
        bot.run(config.discord_token, log_handler=None)
    except KeyboardInterrupt:
        logger.info("Arrêt du bot par signal d'interruption.")
    except Exception as exc:
        logger.exception("Erreur inattendue lors de l'exécution du bot : %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
