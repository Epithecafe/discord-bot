#!/usr/bin/env bash
# ==============================================================================
# Script de déploiement automatique pour Debian 11 / 12 (Bullseye / Bookworm)
# Usage: sudo bash deploy/deploy_debian.sh
# ==============================================================================

set -euo pipefail

APP_NAME="chabeille"
APP_DIR="/opt/${APP_NAME}"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
CURRENT_USER="${SUDO_USER:-$(whoami)}"

echo "=== [1/6] Vérification des droits administrateur ==="
if [ "$EUID" -ne 0 ]; then
  echo "❌ Ce script doit être exécuté avec les privilèges root (sudo)."
  exit 1
fi

echo "=== [2/6] Installation des paquets système Debian requis ==="
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git sqlite3

echo "=== [3/6] Préparation du dossier de l'application (${APP_DIR}) ==="
mkdir -p "${APP_DIR}"
mkdir -p "${APP_DIR}/data"

# Si le script est exécuté depuis le dépôt Git, on copie les fichiers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Copie des fichiers depuis ${SCRIPT_DIR} vers ${APP_DIR}..."
cp -r "${SCRIPT_DIR}/src" "${APP_DIR}/"
cp "${SCRIPT_DIR}/main.py" "${APP_DIR}/"
cp "${SCRIPT_DIR}/requirements.txt" "${APP_DIR}/"

if [ ! -f "${APP_DIR}/.env" ]; then
  if [ -f "${SCRIPT_DIR}/.env" ]; then
    echo "Copie du fichier .env existant..."
    cp "${SCRIPT_DIR}/.env" "${APP_DIR}/.env"
  else
    echo "Création d'un modèle .env à configurer..."
    cp "${SCRIPT_DIR}/.env.example" "${APP_DIR}/.env"
  fi
fi

echo "=== [4/6] Création de l'environnement virtuel Python ==="
if [ ! -d "${APP_DIR}/venv" ]; then
  python3 -m venv "${APP_DIR}/venv"
fi
"${APP_DIR}/venv/bin/pip" install --upgrade pip
"${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

echo "=== [5/6] Configuration des permissions et du service systemd ==="
chown -R "${CURRENT_USER}:${CURRENT_USER}" "${APP_DIR}"
chmod 700 "${APP_DIR}/data"

# Adaptation du fichier systemd avec l'utilisateur courant
sed -e "s|User=debian|User=${CURRENT_USER}|g" "${SCRIPT_DIR}/systemd/chabeille.service" > "${SERVICE_FILE}"
systemctl daemon-reload

echo "=== [6/6] Déploiement terminé ! ==="
echo ""
echo "👉 Prochaines étapes :"
echo "1. Éditez le fichier ${APP_DIR}/.env pour renseigner votre DISCORD_TOKEN :"
echo "   sudo nano ${APP_DIR}/.env"
echo ""
echo "2. Démarrez et activez le service au démarrage :"
echo "   sudo systemctl enable --now ${APP_NAME}"
echo ""
echo "3. Consultez les logs en temps réel avec :"
echo "   sudo journalctl -u ${APP_NAME} -f"
echo ""
