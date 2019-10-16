from sneakerBot import Sneakerbot
import config

token = config.BOT_CONFIG['token']
channel_id = config.BOT_CONFIG['channel']
save_file = config.BOT_CONFIG['save_file']
bot = Sneakerbot(token, channel_id, save_file)
bot.run()
