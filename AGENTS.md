Je veux faire un bot discord. Ce bot est censé gérer le membrage des gens de mon association sur son serveur discord.

La liste des membres sera stockée sur une base de donnée sqlite.

Il y a plusieurs commandes :

- /member <login> <full name> : Ajouter à la base de donnée l'id du profil discord, le nom complet ("John Doe"), et la date de membrage. Accessible seulement aux gens qui ont le rôle "bureau"
- /info <login> : Envoie en MP les infos de membrage, avec la dernière date de membrage. Accessible seulement aux gens qui ont le rôle "Membre"
- /export : Envoie l'ensemble de la base de donnée. Accessible seulement aux gens qui ont le rôle "bureau"
