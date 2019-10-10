from telegram.ext import (Updater, ConversationHandler, CommandHandler, CallbackQueryHandler,
                            MessageHandler, filters)
from telegram import KeyboardButton, ReplyKeyboardMarkup, ParseMode
from stages import Stages
from ads import Ads
from adTypes import AdTypes
import botDialogs
import logging
import uuid

class Sneakerbot(object):
    def __init__(self, bot_token):
        # Data structures to keep track of users' activities
        self.user_stage = {} # Users dictionary -> {username : state}

        # Save all the ads
        self.ads = []
        self.pending_ads = {}

        # Enable logging
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Init bot tools to retrieve data
        self.updater = Updater(bot_token, use_context=True)
        self.dispatcher = self.updater.dispatcher

        for handler in self.get_handlers():
            self.dispatcher.add_handler(handler)

    def start(self, update, context):
        """Start the bot"""
        user = update.message.from_user
        bot = context.bot
        self.logger.info("User %s started the conversation.", user.name)
        # Register the user
        self.user_stage[user.id] = Stages.MENU

        self.set_keyboard(user, update)

    def get_keyboards(self):
        keyboards = {}

        keyboards[Stages.MENU] = (botDialogs.KEYBOARD_TEXTS['menu_dialog'], [  # Menu keyboard
            [KeyboardButton("Crea annuncio"),
            KeyboardButton("I miei annunci")]
        ])
        keyboards[Stages.AD_CONFIRM] = (botDialogs.KEYBOARD_TEXTS['ad_insert_confirm'], [
            [KeyboardButton("Confermo"),
            KeyboardButton("Reset")]
        ])
        # Do this shit somehow better
        keyboards[Stages.REGION_SELECT] = (botDialogs.KEYBOARD_TEXTS['region_select'], [
            [KeyboardButton("Abruzzo"), KeyboardButton("Basilicata"), KeyboardButton("Calabria")],
            [KeyboardButton("Campania"), KeyboardButton("Emilia Romagna"), KeyboardButton("Friuli-Venezia Giulia")],
            [KeyboardButton("Lazio"), KeyboardButton("Liguria"), KeyboardButton("Lombardia")],
            [KeyboardButton("Marche"), KeyboardButton("Molise"), KeyboardButton("Piemonte")],
            [KeyboardButton("Puglia"), KeyboardButton("Sardegna"), KeyboardButton("Sicilia")],
            [KeyboardButton("Toscana"), KeyboardButton("Trentino-Alto Adige"), KeyboardButton("Umbria")],
            [KeyboardButton("Val d'Aosta"), KeyboardButton("Veneto")],
        ])
        # Also this
        keyboards[Stages.CONDITION_SELECTION] = (botDialogs.KEYBOARD_TEXTS['condition_selection'],[
            [KeyboardButton("Nuove"), KeyboardButton("Usate")]
        ])
        keyboards[Stages.AD_INSERT] = (botDialogs.KEYBOARD_TEXTS['ad_complete_confirm'], [
            [KeyboardButton("Confermo"),
            KeyboardButton("Reset")]
        ])
        keyboards[Stages.AD_TYPE_SELECT] = (botDialogs.KEYBOARD_TEXTS['ad_type_select'], [
            [KeyboardButton("Cerco"),
            KeyboardButton("Vendo")]
        ])

        return keyboards

    def set_keyboard(self, user, update):
        # Get current user stage and respective keyboard
        current_stage = self.user_stage[user.id]
        keyboard = self.get_keyboards()[current_stage]

        # Apply keyboard
        reply_markup = ReplyKeyboardMarkup(keyboard=keyboard[1], resize_keyboard=True, one_time_keyboard=True)
        update.message.reply_text(text=keyboard[0], reply_markup=reply_markup)

    def get_handlers(self):
        handlers = []
        handlers.append(CommandHandler("start", self.start))
        handlers.append(MessageHandler(filters.Filters.regex(r'Crea annuncio'), self.new_ads))
        handlers.append(MessageHandler(filters.Filters.regex(r'I miei annunci'), self.my_ads))
        handlers.append(MessageHandler(filters.Filters.regex(r'Reset'), self.reset))
        handlers.append(CommandHandler("reset", self.reset))
        handlers.append(MessageHandler(filters.Filters.regex(r'Confermo'), self.confirm_operation))
        handlers.append(MessageHandler(filters.Filters.text, self.text_handle))
        handlers.append(MessageHandler(filters.Filters.photo, self.image_handler))

        return handlers

    def reset(self, update, context):
        message = update.message
        user = message.from_user
        chat_id = message.chat_id
        bot = context.bot

        self.logger.info("User %s aborted his ad, going back to menu...", user.name)

        self.user_stage[user.id] = Stages.MENU
        self.set_keyboard(user, update)

    def my_ads(self, update, context):
        message = update.message
        user = message.from_user
        chat_id = message.chat_id
        bot = context.bot

        self.logger.info("Sending ads info to %s", user.name)

        my_ads = filter(lambda x: x.user == user.id, self.ads)
        for a in my_ads:
            self.send_ad(bot, chat_id, a, user, True)

        self.set_keyboard(user, update)

    def confirm_operation(self, update, context):
        message = update.message
        user = message.from_user
        chat_id = message.chat_id
        bot = context.bot

        if user.id not in self.user_stage.keys(): # Check user
            bot.send_message(chat_id, botDialogs.DIALOGS['need_reset'])
            return

        if self.user_stage[user.id] is Stages.AD_CONFIRM:
            # Create a new ad object
            self.pending_ads[user.id] = Ads(user.id)
            self.ad_type_select(update, context)
        elif self.user_stage[user.id] is Stages.AD_INSERT:
            self.insert_ad(update, context)

    def ad_type_select(self, update, context):
        message = update.message
        user = message.from_user
        chat_id = message.chat_id
        bot = context.bot

        if user.id not in self.user_stage.keys(): # Check user
            bot.send_message(chat_id, botDialogs.DIALOGS['need_reset'])
            return

        self.user_stage[user.id] = Stages.AD_TYPE_SELECT
        self.set_keyboard(user, update)

    def new_ads(self, update, context):
        message = update.message
        user = message.from_user
        chat_id = message.chat_id
        bot = context.bot

        if user.id not in self.user_stage.keys() or self.user_stage[user.id] is not Stages.MENU: # Check current stage
            bot.send_message(chat_id, "Comando non permesso in questo momento")
            return

        self.user_stage[user.id] = Stages.AD_CONFIRM # Set right stage
        # Send the notices about posting an ad
        bot.send_message(chat_id, botDialogs.DIALOGS['create_ad_info'])
        # Set the correct keyboard
        self.set_keyboard(user, update)

        self.logger.info("User %s is creating a new ad", user.name)

    def region_select(self, update, context):
        message = update.message
        user = message.from_user
        chat_id = message.chat_id
        bot = context.bot

        if user.id not in self.user_stage.keys() or self.user_stage[user.id] is not Stages.AD_TYPE_SELECT: # Check current stage
            bot.send_message(chat_id, "Comando non permesso in questo momento")
            return

        self.user_stage[user.id] = Stages.REGION_SELECT

        # Set the correct keyboard
        self.set_keyboard(user, update)

    def insert_ad(self, update, context):
        message = update.message
        user = message.from_user
        chat_id = message.chat_id
        bot = context.bot

        bot.send_message(chat_id, botDialogs.DIALOGS['ad_success'])

        # Insert the ad
        self.ads.append(self.pending_ads[user.id])

        # Back to the menu
        self.user_stage[user.id] = Stages.MENU
        self.set_keyboard(user, update)

        self.logger.info("User %s confirmed his Ad", user.name)

    def text_handle(self, update, context):
        message = update.message
        user = message.from_user
        chat_id = message.chat_id
        bot = context.bot

        if user.id not in self.user_stage.keys(): # Check user
            bot.send_message(chat_id, botDialogs.DIALOGS['need_reset'])
            return

        # Ad type selection
        if self.user_stage[user.id] is Stages.AD_TYPE_SELECT:
            if message.text == "Cerco":
                self.pending_ads[user.id].type = AdTypes.BUY
                self.region_select(update, context)
            elif message.text == "Vendo":
                self.pending_ads[user.id].type = AdTypes.SELL
                self.region_select(update, context)
            else:
                print(message.text)
                bot.send_message(chat_id, botDialogs.DIALOGS['type_not_valid'])
                set_keyboard(user, update)
            return

        # Region selection
        if self.user_stage[user.id] is Stages.REGION_SELECT:
            self.pending_ads[user.id].region = message.text # Insert region name
            self.logger.info("User %s selected region %s for its Ad", user.name, message.text)
            self.user_stage[user.id] = Stages.SHOE_NAME_SELECTION # Change stage
            bot.send_message(chat_id, botDialogs.KEYBOARD_TEXTS['shoe_name_selection']) # Prompt selection text
            return

        # Shoe name insertion
        if self.user_stage[user.id] is Stages.SHOE_NAME_SELECTION:
            self.pending_ads[user.id].shoe_name = message.text
            self.logger.info("User %s inserted shoe name: %s", user.name, message.text)
            self.user_stage[user.id] = Stages.NUMBER_SELECTION # Change stage
            bot.send_message(chat_id, botDialogs.KEYBOARD_TEXTS['number_selection']) # Prompt selection text
            return

        # Shoe number selection
        if self.user_stage[user.id] is Stages.NUMBER_SELECTION:
            if not message.text.isdigit():
                bot.send_message(chat_id, botDialogs.DIALOGS['digit_error'])
            else:
                self.pending_ads[user.id].number = int(message.text)
                self.logger.info("User %s inserted shoe number: %d", user.name, int(message.text))
                self.user_stage[user.id] = Stages.CONDITION_SELECTION
                self.set_keyboard(user, update)
            return

        # Condition selection
        if self.user_stage[user.id] is Stages.CONDITION_SELECTION:
            self.pending_ads[user.id].condition = message.text
            self.logger.info("User %s inserted condition: %s", user.name, message.text)
            self.user_stage[user.id] = Stages.PRICE_SELECTION
            if self.pending_ads[user.id].type is AdTypes.SELL:
                bot.send_message(chat_id, botDialogs.KEYBOARD_TEXTS['price_selection_sell'])
            elif self.pending_ads[user.id].type is AdTypes.BUY:
                bot.send_message(chat_id, botDialogs.KEYBOARD_TEXTS['price_selection_buy'])
            return

        # Price selection
        if self.user_stage[user.id] is Stages.PRICE_SELECTION:
            if not message.text.isdigit():
                bot.send_message(chat_id, botDialogs.DIALOGS['digit_error'])
            else:
                self.pending_ads[user.id].price = int(message.text)
                self.logger.info("User %s inserted price: %d", user.name, int(message.text))
                if self.pending_ads[user.id].type is AdTypes.SELL:
                    self.user_stage[user.id] = Stages.PHOTO_INSERTION
                    bot.send_message(chat_id, botDialogs.KEYBOARD_TEXTS['photo_insertion'])
                elif self.pending_ads[user.id].type is AdTypes.BUY :
                    self.send_ad_preview(update, context)
                    self.user_stage[user.id] = Stages.AD_INSERT
                    self.set_keyboard(user, update)
            return

    def send_ad_preview(self, update, context):
        message = update.message
        user = message.from_user
        chat_id = message.chat_id
        bot = context.bot

        ad = self.pending_ads[user.id]
        self.send_ad(bot, chat_id, ad, user)

    def send_ad(self, bot, chat_id, ad, user, review=False):


        caption = self.format_ad(ad, user, review)

        if ad.type is AdTypes.BUY:
            bot.send_message(chat_id=chat_id, text=caption, parse_mode=ParseMode.MARKDOWN)
        elif ad.type is AdTypes.SELL:
            bot.send_photo(chat_id=chat_id, photo=ad.photo, caption=caption,
                            parse_mode=ParseMode.MARKDOWN)

    def image_handler(self, update, context):
        message = update.message
        user = message.from_user
        chat_id = message.chat_id
        bot = context.bot

        if user.id not in self.user_stage.keys(): # Check user
            bot.send_message(chat_id, botDialogs.DIALOGS['need_reset'])
            return

        if self.user_stage[user.id] is not Stages.PHOTO_INSERTION:
            bot.send_message(chat_id, botDialogs.DIALOGS['photo_not_requested'])
        else:
            self.logger.info("User %s sent his shoe photo: id->%s", user.name, message.photo[0].file_id)
            self.pending_ads[user.id].photo = message.photo[0].file_id
            self.send_ad_preview(update, context)
            self.user_stage[user.id] = Stages.AD_INSERT
            self.set_keyboard(user, update)

        return

    def format_pending_ad(self, user, review=False):
        ad = self.pending_ads[user.id]
        return self.format_ad(ad, user, review)

    def format_ad(self, ad, user, review=False):
        if ad.type is AdTypes.SELL:
            caption = 'Vendo *' + ad.shoe_name + '*'
            caption = caption + '\nLuogo: ' + ad.region
            caption = caption + '\nCondizione: ' + ad.condition + ' | ' + str(ad.price) + '€'
            caption = caption +'\nNumero: '+str(ad.number)
            caption = caption + '\nContattare: ' + user.name
        else:
            caption = 'Cerco *' + ad.shoe_name + '*'
            caption = caption + '\nLuogo: ' + ad.region
            caption = caption + '\nCondizione: ' + ad.condition + ' | ' + 'Budget: ' + str(ad.price) + '€'
            caption = caption +'\nNumero: '+str(ad.number)
            caption = caption + '\nContattare: ' + user.name

        if review:
            caption = caption + '\nID: ' + ad.id

        return caption

    def run(self):
        # Start the bot
        self.updater.start_polling()
        # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT
        self.updater.idle()
