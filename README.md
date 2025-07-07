Create a startgg api Token
https://developer.start.gg/docs/authentication/

Replace the value of "START_GG_KEY" in .env by your token

Create your discord bot :
https://discord.com/developers/applications

Go to "New application" , chose your name, and create id

Go to "Bot" in the left tab
Click on "Reset Token" 
Now you can copy your token DON'T SHARE IT

in the .env file replace the "DISCORD_BOT_TOKEN" by your token

Go back to the discord website, in the same page scroll down and find the "Privileged Gateway Intents"
Check the "Server Members intent" and the "Message contente intent"

Go to "OAuth2" on the left tab 
On the "OAuth2 URL Generator" check "Bot"

Scroll down and in the bot permissions check "Administrator" 

Copy the link and paste it in your navigator , select the server for your tournament



You need to have at least python 3.11 install
Execute the "setup.py" file (you need to execute it only one time)

Your bot is ready to use ! 

Now you can just execute the "discord_bot.py" file to start your bot 

Use the command "/setup_tournament" to start your tournament