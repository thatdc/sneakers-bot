from sneakerBot import Sneakerbot
import config

token = config.BOT_CONFIG['token']
channel_id = config.BOT_CONFIG['channel']
bot = Sneakerbot(token, channel_id)
bot.run()
