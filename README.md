# 🐝 Chabeille - Bot Discord de Gestion des Membres

Bot Discord développé en Python (`discord.py`) avec base de données SQLite pour gérer l'adhésion et le suivi des membres d'une association. Prêt à être déployé sur un serveur Debian (via **systemd** ou **Docker**).

---

## 📋 Sommaire
1. [Fonctionnalités & Commandes](#-fonctionnalités--commandes)
2. [Configuration requise sur Discord](#-configuration-requise-sur-discord)
3. [Installation locale (Développement)](#-installation-locale-développement)
4. [Déploiement sur Debian](#-déploiement-sur-debian)
   - [Méthode A : Service Systemd (Recommandée)](#méthode-a--service-systemd-recommandée)
   - [Méthode B : Docker / Docker Compose](#méthode-b--docker--docker-compose)
5. [Structure du projet](#-structure-du-projet)
6. [Sauvegarde et maintenance](#-sauvegarde-et-maintenance)

---

## ⚡ Fonctionnalités & Commandes

Toutes les interactions se font via des **Commandes Slash** (`/`) avec vérification des permissions par rôles Discord (insensible à la casse ou par ID).

| Commande | Rôle requis | Description |
| :--- | :--- | :--- |
| `/member <user> <full_name> [date]` | **bureau** | Enregistre un membre (ID Discord, nom complet, date d'adhésion). Si le membre existe déjà, ajoute une ré-adhésion à son historique et met à jour sa dernière date. Attribue automatiquement le rôle `Membre` si activé. |
| `/info [user]` | **Membre** (ou bureau) | Envoie **en message privé (MP)** les informations de membrage et la dernière date d'adhésion du membre. Par défaut, consulte ses propres informations. |
| `/export` | **bureau** | Génère et envoie en réponse privée (**éphémère**) l'export complet : un fichier **CSV** (compatible Excel / Sheets) et la copie brute de la base de données **SQLite** (`.db`). |

> [!TIP]
> **Persistance automatique du rôle Membre** : Si un membre enregistré dans la base quitte le serveur puis le rejoint plus tard, l'événement `on_member_join` détecte automatiquement sa présence dans la base SQLite et lui réattribue immédiatement son rôle `Membre`.

---

## 🔑 Configuration requise sur Discord

### 1. Création de l'application et du bot
1. Rendez-vous sur le [Portail Développeur Discord](https://discord.com/developers/applications).
2. Cliquez sur **New Application**, nommez-la (ex: *Chabeille*).
3. Rendez-vous dans l'onglet **Bot** :
   - Cliquez sur **Reset Token** pour obtenir votre token de connexion (notez-le précieusement, il ira dans `.env`).
   - Descendez à la section **Privileged Gateway Intents** et activez impérativement :
     - ✅ **Server Members Intent** (nécessaire pour lire les rôles des membres et leur attribuer le rôle).

### 2. Inviter le bot sur votre serveur
1. Allez dans l'onglet **OAuth2** > **URL Generator**.
2. Dans **Scopes**, cochez :
   - `bot`
   - `applications.commands`
3. Dans **Bot Permissions**, cochez :
   - `Manage Roles` (Gérer les rôles)
   - `Send Messages`
   - `Attach Files`
   - `Embed Links`
4. Copiez le lien généré en bas de page et collez-le dans votre navigateur pour ajouter le bot à votre serveur.

> [!IMPORTANT]
> **Hiérarchie des rôles Discord** : Pour que le bot puisse attribuer le rôle `Membre`, le rôle attribué au bot dans les paramètres du serveur doit être positionné **au-dessus** du rôle `Membre` dans la liste des rôles de Discord.

---

## 💻 Installation locale (Développement)

```bash
# 1. Cloner ou naviguer dans le dossier du projet
cd /home/louis/projects/chabeille

# 2. Créer l'environnement virtuel et installer les dépendances
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Créer le fichier de configuration
cp .env.example .env
nano .env  # Renseignez votre DISCORD_TOKEN et éventuellement GUILD_ID

# 4. Lancer les tests unitaires
python3 -m unittest discover -s tests

# 5. Démarrer le bot
python3 main.py
```

---

## 🐧 Déploiement sur Debian

### Méthode A : Service Systemd (Recommandée)

Cette méthode fait tourner le bot en tâche de fond sur votre serveur Debian et le redémarre automatiquement en cas de crash ou de reboot du serveur.

#### Option 1 : Déploiement automatique via le script fourni

Sur votre machine Debian :
```bash
# Cloner le projet sur votre serveur
git clone <url_de_votre_depot> chabeille
cd chabeille

# Exécuter le script de déploiement en root
sudo bash deploy/deploy_debian.sh
```

Le script installe Python 3, prépare `/opt/chabeille`, installe les dépendances et configure le service systemd `/etc/systemd/system/chabeille.service`.

#### Option 2 : Déploiement manuel pas à pas

1. **Installer les dépendances système** :
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3 python3-venv python3-pip git sqlite3
   ```

2. **Copier le projet dans `/opt/chabeille`** :
   ```bash
   sudo mkdir -p /opt/chabeille/data
   sudo cp -r src /opt/chabeille/
   sudo cp main.py requirements.txt .env.example /opt/chabeille/
   sudo cp systemd/chabeille.service /etc/systemd/system/chabeille.service
   ```

3. **Créer l'environnement virtuel** :
   ```bash
   sudo python3 -m venv /opt/chabeille/venv
   sudo /opt/chabeille/venv/bin/pip install -r /opt/chabeille/requirements.txt
   ```

4. **Configurer `.env`** :
   ```bash
   sudo cp /opt/chabeille/.env.example /opt/chabeille/.env
   sudo nano /opt/chabeille/.env
   ```
   Renseignez votre `DISCORD_TOKEN`.

5. **Définir les permissions appropriées** :
   ```bash
   # Remplacez debian par votre utilisateur si nécessaire
   sudo chown -R debian:debian /opt/chabeille
   sudo chmod 700 /opt/chabeille/data
   ```

6. **Activer et démarrer le service** :
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now chabeille
   ```

7. **Consulter les logs** :
   ```bash
   sudo journalctl -u chabeille -f
   ```

---

### Méthode B : Docker / Docker Compose

Si vous avez déjà Docker sur votre Debian :

1. Préparez votre fichier `.env` :
   ```bash
   cp .env.example .env
   nano .env
   ```

2. Lancez le conteneur :
   ```bash
   docker compose up -d --build
   ```

3. Visualisez les logs :
   ```bash
   docker compose logs -f
   ```

La base de données sera persistée dans le dossier local `./data/`.

---

## 🗂️ Structure du projet

```
chabeille/
├── .env.example              # Exemple de fichier de configuration
├── .gitignore                # Fichiers ignorés par Git
├── requirements.txt          # Dépendances Python (discord.py, python-dotenv, aiosqlite)
├── Dockerfile                # Image conteneur Debian/Python
├── docker-compose.yml        # Orchestration Docker
├── main.py                   # Point d'entrée principal
├── src/
│   ├── __init__.py
│   ├── bot.py                # Client Discord et enregistrement des cogs
│   ├── config.py             # Chargement et validation de la configuration
│   ├── database.py           # Gestionnaire asynchrone SQLite (aiosqlite)
│   └── cogs/
│       ├── __init__.py
│       └── members.py        # Commandes slash : /member, /info, /export
├── systemd/
│   └── chabeille.service     # Définition de l'unité de service Debian
├── deploy/
│   └── deploy_debian.sh      # Script bash de déploiement automatique Debian
├── tests/
│   ├── test_cogs.py          # Tests des utilitaires (rôles, dates)
│   └── test_database.py      # Tests unitaires de la base SQLite
└── data/                     # Répertoire contenant la base SQLite (exclu de Git)
```

---

## 💾 Sauvegarde et maintenance

- **Base de données** : Le fichier de données se trouve dans `data/members.db`.
- **Sauvegarde à chaud** : Vous pouvez utiliser la commande `/export` directement dans Discord depuis n'importe où pour recevoir une copie complète instantanée en MP/éphémère, ou faire un simple backup Linux :
  ```bash
  sqlite3 /opt/chabeille/data/members.db ".backup '/chemin/de/sauvegarde/members_backup.db'"
  ```
- **Mises à jour du code** :
  ```bash
  cd /opt/chabeille
  git pull
  ./venv/bin/pip install -r requirements.txt
  sudo systemctl restart chabeille
  ```
