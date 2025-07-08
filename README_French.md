Créer un token API pour start.gg
Allez sur :
https://developer.start.gg/docs/authentication/

Créez un token API start.gg

Dans le fichier .env, remplacez la valeur de START_GG_KEY par votre token


Créer votre bot Discord
Rendez-vous sur :
https://discord.com/developers/applications

Cliquez sur "New Application", choisissez un nom et créez-le

Dans l'onglet de gauche, allez dans "Bot"

Cliquez sur "Reset Token"

Copiez votre token (⚠️ NE LE PARTAGEZ JAMAIS ⚠️)

Dans le fichier .env, remplacez DISCORD_BOT_TOKEN par votre token


Configurer les Intents
Toujours dans la page "Bot", descendez jusqu'à "Privileged Gateway Intents"

Activez :

"Server Members Intent" (Intent des membres du serveur)

"Message Content Intent" (Intent du contenu des messages)


Autorisations et invitation
Allez dans "OAuth2" (onglet de gauche)

Dans "OAuth2 URL Generator", cochez "Bot"

Descendez et dans les permissions du bot, cochez "Administrator"

Copiez le lien généré et collez-le dans votre navigateur

Sélectionnez le serveur où organiser votre tournoi


Installation
Assurez-vous d'avoir Python 3.11 ou supérieur installé

Exécutez le fichier setup.py (une seule fois)

Allez dans le fichier .env et verifier la valeur de LANG :  LANG="en"

✅ Votre bot est prêt à l'emploie

Lancer le bot
Exécutez le fichier discord_bot.py pour démarrer le bot

Utilisez la commande /setup_tournament pour configurer votre tournoi

