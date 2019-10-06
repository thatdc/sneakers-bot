from sneakerBot import Sneakerbot
import config

token = config.BOT_CONFIG['token']
bot = Sneakerbot(token)
bot.run()
