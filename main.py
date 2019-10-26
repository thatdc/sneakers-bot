from sneakerBot import Sneakerbot
import config

token = config.BOT_CONFIG['token']
channel_id = config.BOT_CONFIG['channel']
ads_save_file = config.BOT_CONFIG['ads_save_file']
user_save_file = config.BOT_CONFIG['user_save_file']
feedback_save_file = config.BOT_CONFIG['feedback_save_file']
bot = Sneakerbot(token, channel_id, ads_save_file, user_save_file, feedback_save_file)
bot.run()
