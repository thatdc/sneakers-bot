from telegram.ext import (Updater, ConversationHandler, CommandHandler, CallbackQueryHandler,
                            MessageHandler, filters)
from telegram import (KeyboardButton, ReplyKeyboardMarkup, ParseMode, InlineKeyboardButton,
                        InlineKeyboardMarkup)
from datetime import (time, date, timedelta, datetime)
from stages import Stages
from ads import Ads
from adTypes import AdTypes
from copy import deepcopy
import botDialogs
import logging
import pickle
import os
import uuid
from html import escape
from validate import *
from generator import *
from user import User
from feedback import Feedback
import jsonpickle
import json
from copy import deepcopy
import hashlib

class Sneakerbot(object):
    def __init__(self, CONFIG):

        # Enable logging
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Data structures to keep track of users' activities
        self.user_stage = {} # Users dictionary -> {username : state}
        self.feedbacking = {} # pending feedback -> {from : to}

        self.channel_id = CONFIG['channel']
        self.group_id = ""
        self.ads_save_file = CONFIG['ads_save_file']

        # Save all the ads
        self.ads = []
        self.pending_ads = {}
        self.queue_ads = []

        # Misc
        self.timer = 15

        # Ads id things
        self.id_save_file = CONFIG['id_save_file']
        self.next_id = 0

        # Infos about users
        self.user_list = []
        self.feedback_list = []
        self.user_save_file = CONFIG['user_save_file']
        self.feedback_save_file = CONFIG['feedback_save_file']

        # Load data
        self.load_save_file()

        # Password
        self.password = CONFIG['password']
        self.admin_list = []

        # Init bot tools to retrieve data
        bot_token = CONFIG['token']
        self.updater = Updater(bot_token, use_context=True)
        self.dispatcher = self.updater.dispatcher

        self.updater.job_queue.run_daily(callback=self.delete_old_posts, time=time(hour=12, minute=00))

        for handler in self.get_handlers():
            self.dispatcher.add_handler(handler)

    def start(self, update, context):
        """Start the bot"""
        user = update.message.from_user
        bot = context.bot
        self.logger.info("User %s started the conversation.", user.name)

        # Register the user
        self.user_stage[user.id] = Stages.MENU
        self.add_user(user)

        # Check username
        if not user.username:
            bot.send_message(update.message.chat_id, botDialogs.DIALOGS['username_not_found'], parse_mode=ParseMode.HTML)

        self.set_keyboard(user, update, bot)

    def delete_old_posts(self, context):
        new_ads = []
        bot = self.updater.bot

        for ad in self.ads:
            if (datetime.now() - ad.post_date) > timedelta(days=29):
                bot.delete_message(self.channel_id, ad.message_id)
                self.logger.info("Message %s deleted", ad.message_id)
            else:
                new_ads.append(ad)

        self.ads = new_ads
        self.update_save_file(self.ads_save_file, self.ads)

    def add_user(self, usr):
        if usr.id not in [u.id for u in self.user_list]:
            self.user_list.append(User(usr.id, usr.name, usr.full_name))
            self.logger.info("User %s registered to the database", usr.name)
        self.update_save_file(self.user_save_file, self.user_list)

    def name_to_id(self, name):
        for usr in self.user_list:
            if usr.username == name:
                return usr.id
        raise Exception('Username not found')

    def begin_feedback(self, update, context):
        message = update.message
        user = message.from_user
        chat_id = message.chat_id
        bot = context.bot

        if user.id not in self.user_stage.keys(): # Check user
            bot.send_message(chat_id, botDialogs.DIALOGS['need_reset'])
            return

        if self.user_stage[user.id] is not Stages.MENU:
            bot.send_message(chat_id, botDialogs.DIALOGS['command_not_valid'])
            return

        self.user_stage[user.id] = Stages.INSERT_FEEDBACK
        bot.send_message(chat_id, botDialogs.KEYBOARD_TEXTS['insert_feedback'])

    def vote(self, bot, message, user_target, value):
        user = message.from_user
        chat_id = message.chat_id

        try:
            if user.id not in [fb.from_id for fb in self.feedback_list if fb.to_id == self.name_to_id(user_target)]:
                self.feedback_list.append(Feedback(user.id, self.name_to_id(user_target), value))
            else:
                for fb in self.feedback_list:
                    if fb.from_id == user.id and fb.to_id == self.name_to_id(user_target):
                        fb.value = value
            self.update_save_file(self.feedback_save_file, self.feedback_list)
            bot.send_message(chat_id, botDialogs.DIALOGS['vote_registered'])
            self.logger.info("User %s registered his feedback for user %s with a value %d", user.name, user_target, value)
        except Exception:
            bot.send_message(chat_id, botDialogs.DIALOGS['user_not_found'])

    def count_feedbacks(self, id, value):
        return len([fb for fb in self.feedback_list if fb.to_id == id and fb.value == value])

    def get_keyboards(self):
        keyboards = {}

        keyboards[Stages.MENU] = (botDialogs.KEYBOARD_TEXTS['menu_dialog'], [  # Menu keyboard
            [KeyboardButton("Crea annuncio"),
            KeyboardButton("I miei annunci"),
            KeyboardButton("Rimuovi un annuncio")],
            [KeyboardButton("Valuta un utente")]
        ])
        keyboards[Stages.AD_CONFIRM] = (botDialogs.KEYBOARD_TEXTS['ad_insert_confirm'], [
            [KeyboardButton("Confermo"),
            KeyboardButton("Reset")]
        ])
        keyboards[Stages.REGION_SELECT] = (botDialogs.KEYBOARD_TEXTS['region_select'], generate_regions())
        keyboards[Stages.CONDITION_SELECTION] = (botDialogs.KEYBOARD_TEXTS['condition_selection'], generate_conditions())
        keyboards[Stages.AD_INSERT] = (botDialogs.KEYBOARD_TEXTS['ad_complete_confirm'], [
            [KeyboardButton("Confermo"),
            KeyboardButton("Reset")]
        ])
        keyboards[Stages.AD_TYPE_SELECT] = (botDialogs.KEYBOARD_TEXTS['ad_type_select'], [
            [KeyboardButton("Cerco"),
            KeyboardButton("Vendo")]
        ])
        keyboards[Stages.BRAND_SELECTION] = (botDialogs.KEYBOARD_TEXTS['brand_selection'], generate_brands())
        keyboards[Stages.NUMBER_SELECTION] = (botDialogs.KEYBOARD_TEXTS['number_selection'], generate_sizes())
        keyboards[Stages.NOTE_INSERT_REQ] = (botDialogs.KEYBOARD_TEXTS['note_insert_req'], generate_bool_choice())
        keyboards[Stages.SET_AVAILABILITY] = (botDialogs.KEYBOARD_TEXTS['set_availability'], generate_bool_choice())
        keyboards[Stages.SET_SHIPPING] = (botDialogs.KEYBOARD_TEXTS['set_shipping'], generate_bool_choice())
        keyboards[Stages.ACCEPT_PAYPAL] = (botDialogs.KEYBOARD_TEXTS['accept_paypal'], generate_bool_choice())
        keyboards[Stages.EVALUATE_FEEDBACK] = (botDialogs.KEYBOARD_TEXTS['evaluate_feedback'], [
            [KeyboardButton('Positiva'),
            KeyboardButton('Negativa')]
        ])

        return keyboards

    def generate_delete_keyboard(self, update, context):
        message = update.message
        user = message.from_user
        chat_id = message.chat_id
        bot = context.bot

        if user.id not in self.user_stage.keys(): # Check user
            bot.send_message(chat_id, botDialogs.DIALOGS['need_reset'])
            return

        self.user_stage[user.id] = Stages.DELETE_AD

        kb = []
        my_ads = self.get_ads_by_user(user)

        ndx = 0
        buttons = []
        # Build a keyboard with 3 ads in the same row
        for ad in my_ads:
            buttons.append(InlineKeyboardButton(ad.shoe_name, callback_data=ad.id))
            ndx=ndx+1
            if ndx == 3:
                kb.append(buttons)
                ndx = 0
                buttons = []
        if buttons:
            kb.append(buttons)

        reply_markup = InlineKeyboardMarkup(kb)

        update.message.reply_text(botDialogs.KEYBOARD_TEXTS['delete_ad'], reply_markup=reply_markup)

        if len(my_ads) == 0:
            bot.send_message(chat_id, botDialogs.DIALOGS['no_ads_error'])

    def get_ad_by_id(self, ad_id):
        for ad in self.ads:
            if ad.id == ad_id:
                return ad

    def remove_from_channel(self, bot, ad):
        mess_id = ad.message_id
        if ad.type == AdTypes.BUY:
            bot.edit_message_text(text="<i>Annuncio rimosso</i>", chat_id=self.channel_id, message_id=mess_id, parse_mode=ParseMode.HTML)
        else:
            bot.edit_message_caption(caption="<i>Non più disponibile</i>", chat_id=self.channel_id, message_id=mess_id, parse_mode=ParseMode.HTML)

    def delete_ad(self, update, context):
        query = update.callback_query
        chat_id = query.message.chat_id
        user = query.from_user
        bot = context.bot

        if user.id not in self.user_stage.keys(): # Check user
            bot.send_message(chat_id, botDialogs.DIALOGS['need_reset'])
            return

        if self.user_stage[user.id] != Stages.DELETE_AD:
            bot.send_message(chat_id, botDialogs.DIALOGS['command_not_valid'])
            return

        selected_ad = self.get_ad_by_id(query.data)
        self.remove_from_channel(bot, selected_ad)

        self.ads = list(filter(lambda x: x.id != query.data, self.ads))
        self.update_save_file(self.ads_save_file, self.ads)

        self.logger.info("User %s deleted Ad with ID %s", user.name, query.data)

        self.user_stage[user.id] = Stages.MENU
        self.set_keyboard(user, update, bot, chat_id)

    def set_keyboard(self, user, update, bot, chat_id=None):
        if user.id not in self.user_stage.keys(): # Check user
            bot.send_message(chat_id, botDialogs.DIALOGS['need_reset'])
            return

        # Get current user stage and respective keyboard
        current_stage = self.user_stage[user.id]
        keyboard = self.get_keyboards()[current_stage]

        # Apply keyboard
        reply_markup = ReplyKeyboardMarkup(keyboard=keyboard[1], resize_keyboard=True, one_time_keyboard=True)
        if update.message:
            update.message.reply_text(text=keyboard[0], reply_markup=reply_markup)
        else:
            bot.send_message(chat_id=chat_id, text=keyboard[0], reply_markup=reply_markup)

    def get_handlers(self):
        handlers = []
        handlers.append(CommandHandler(command="start", callback=self.start, filters=filters.Filters.private))
        handlers.append(MessageHandler(filters.Filters.private & filters.Filters.regex(r'Crea annuncio'), self.new_ads))
        handlers.append(MessageHandler(filters.Filters.private & filters.Filters.regex(r'I miei annunci'), self.my_ads))
        handlers.append(MessageHandler(filters.Filters.private & filters.Filters.regex(r'Rimuovi un annuncio'), self.generate_delete_keyboard))
        handlers.append(MessageHandler(filters.Filters.private & filters.Filters.regex(r'Valuta un utente'), self.begin_feedback))
        handlers.append(MessageHandler(filters.Filters.private & filters.Filters.regex(r'Reset'), self.reset))
        handlers.append(CommandHandler(command="reset", callback=self.reset, filters=filters.Filters.private))
        handlers.append(MessageHandler(filters.Filters.private & filters.Filters.regex(r'Confermo'), self.confirm_operation))
        handlers.append(MessageHandler(filters.Filters.private & filters.Filters.text, self.text_handle))
        handlers.append(MessageHandler(filters.Filters.private & filters.Filters.photo, self.image_handler))
        handlers.append(CallbackQueryHandler(self.delete_ad))
        #handlers.append(CommandHandler(command="setgroup", callback=self.set_group, filters=filters.Filters.group))
        handlers.append(CommandHandler(command="setchannel", callback=self.set_channel, filters=filters.Filters.private))
        handlers.append(CommandHandler(command="newpassword", callback=self.new_password, filters=filters.Filters.private))
        handlers.append(CommandHandler(command="setadmin", callback=self.set_admin, filters=filters.Filters.private))
        #handlers.append(CommandHandler(command="block", callback=self.block_ad, filters=filters.Filters.group))
        #handlers.append(CommandHandler(command="settimer", callback=self.set_timer, filters=filters.Filters.private))

        return handlers

    def reset(self, update, context):
        message = update.message
        user = message.from_user
        chat_id = message.chat_id
        bot = context.bot

        if user.id not in self.user_stage.keys(): # Check user
            bot.send_message(chat_id, botDialogs.DIALOGS['need_start'])
            return

        self.logger.info("User %s aborted his ad, going back to menu...", user.name)

        self.user_stage[user.id] = Stages.MENU
        self.set_keyboard(user, update, bot)

    def set_timer(self, update, context):
        message = update.message
        user = message.from_user
        chat_id = message.chat_id
        bot = context.bot

        if user.id in self.admin_list:
            try:
                self.timer = context.args[0]
                bot.send_message(chat_id, botDialogs.DIALOGS['timer_success'])
            except (IndexError, ValueError):
                bot.send_message(chat_id, botDialogs.DIALOGS['timer_error'])
        else:
            bot.send_message(chat_id, botDialogs.DIALOGS['permission_denied'])

    def set_channel(self, update, context):
        message = update.message
        user = message.from_user
        chat_id = message.chat_id
        bot = context.bot

        if user.id in self.admin_list:
            new_channel = message.text.split(' ')[1]
            if new_channel.startswith('@'):
                self.channel_id = new_channel
                self.logger.info("User %s changed channel, new channel id: %s", user.name, new_channel)
                bot.send_message(chat_id, botDialogs.DIALOGS['channel_change_confirm'])
            else:
                bot.send_message(chat_id, botDialogs.DIALOGS['invalid_channel'])
        else:
            bot.send_message(chat_id, botDialogs.DIALOGS['permission_denied'])

    def my_ads(self, update, context):
        message = update.message
        user = message.from_user
        chat_id = message.chat_id
        bot = context.bot

        if user.id not in self.user_stage.keys(): # Check user
            bot.send_message(chat_id, botDialogs.DIALOGS['need_reset'])
            return
        elif self.user_stage[user.id] != Stages.MENU:
            bot.send_message(chat_id, botDialogs.DIALOGS['command_not_valid'])
            return

        self.logger.info("Sending ads info to %s", user.name)

        my_ads = self.get_ads_by_user(user)
        for a in my_ads:
            self.send_ad(bot, chat_id, a, user, True)
        self.set_keyboard(user, update, bot, chat_id)

    def get_ads_by_user(self, user):
        my_ads = filter(lambda x: x.user == user.id, self.ads)
        return list(my_ads)

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
        self.set_keyboard(user, update, bot)

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
        self.set_keyboard(user, update, bot)

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
        self.set_keyboard(user, update, bot)

    def insert_ad(self, update, context):
        message = update.message
        user = message.from_user
        chat_id = message.chat_id
        bot = context.bot

        bot.send_message(chat_id, botDialogs.DIALOGS['ad_success'])

        # Back to the menu
        self.user_stage[user.id] = Stages.MENU
        self.set_keyboard(user, update, bot)

        self.logger.info("User %s confirmed his Ad", user.name)

        self.pending_ads[user.id].id = hex(self.next_id)
        self.next_id += 1
        self.update_next_id()
        self.pending_ads[user.id].post_date = datetime.now()    
        ad = deepcopy(self.pending_ads[user.id])

        # Post on the channel
        self.post_to_channel_now(bot, user, ad)
        
        # Call delayed posting
        # DELETED: NO MORE REQUIRED BY COSTUMER
        #context.job_queue.run_once(self.post_to_channel, 60*int(self.timer), context=(ad, chat_id, user))

    def post_to_group(self, ad, user, bot):
        
        if not self.group_id:
            bot.send_message(chat_id, botDialogs.DIALOGS['no_group_found'])
            return

        self.logger.info("Posting Ad %s on the private group", ad.id)

        caption = self.format_ad(ad, user, review=True)
        if ad.type is AdTypes.BUY:
            sent_message = bot.send_message(chat_id=self.group_id, text=caption, parse_mode=ParseMode.HTML)
        elif ad.type is AdTypes.SELL:
            sent_message = bot.send_photo(chat_id=self.group_id, photo=ad.photo, caption=caption,
                            parse_mode=ParseMode.HTML)

    def post_to_channel_now(self, bot, user, ad):
        caption = self.format_ad(ad, user)

        if ad.type is AdTypes.BUY:
            sent_message = bot.send_message(chat_id=self.channel_id, text=caption, parse_mode=ParseMode.HTML)
        elif ad.type is AdTypes.SELL:
            sent_message = bot.send_photo(chat_id=self.channel_id, photo=ad.photo, caption=caption,
                            parse_mode=ParseMode.HTML)

        # Save message id in case I want to modify the message
        ad.message_id = sent_message.message_id

        # Insert the ad
        self.ads.append(ad)
        self.update_save_file(self.ads_save_file, self.ads)

    def post_to_channel(self, context):
        job = context.job
        bot = context.bot

        ad = job.context[0]
        chat_id = job.context[1]
        user = job.context[2]

        if ad.id not in [a.id for a in self.queue_ads]:
            self.logger.info("Ad %s discarded previously on the private group...", ad.id)
            return

        self.logger.info("Posting Ad %s on the channel", ad.id)

        caption = self.format_ad(ad, user)

        if ad.type is AdTypes.BUY:
            sent_message = bot.send_message(chat_id=self.channel_id, text=caption, parse_mode=ParseMode.HTML)
        elif ad.type is AdTypes.SELL:
            sent_message = bot.send_photo(chat_id=self.channel_id, photo=ad.photo, caption=caption,
                            parse_mode=ParseMode.HTML)

        # Save message id in case I want to modify the message
        ad.message_id = sent_message.message_id

        # Insert the ad
        self.ads.append(ad)
        self.update_save_file(self.ads_save_file, self.ads)

        # Remove the ad from the queue
        self.remove_from_queue(ad.id)

    def block_ad(self, update, context):
        message = update.message
        user = message.from_user
        chat_id = message.chat_id
        bot = context.bot
        if user.id in self.admin_list:
            try:
                result = self.remove_from_queue(context.args[0])
                if result:
                    bot.send_message(chat_id, botDialogs.DIALOGS['block_confirm'])
                else:
                    bot.send_message(chat_id, botDialogs.DIALOGS['id_not_found'])
            except IndexError:
                bot.send_message(chat_id, botDialogs.DIALOGS['error_block_ad'])
        else:
            bot.send_message(chat_id, botDialogs.DIALOGS['permission_denied'])


    def remove_from_queue(self, id):
        new_queue = []
        result = False

        for a in self.queue_ads:
            if a.id != id:
                new_queue.append(a)
            else:
                result = True
        self.queue_ads = new_queue

        return result

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
                set_keyboard(user, update, bot)
            return

        # Region selection
        if self.user_stage[user.id] is Stages.REGION_SELECT:
            self.pending_ads[user.id].region = message.text # Insert region name
            self.logger.info("User %s selected region %s for its Ad", user.name, message.text)
            self.user_stage[user.id] = Stages.BRAND_SELECTION # Change stage
            self.set_keyboard(user, update, bot)
            return

        # Brand selection
        if self.user_stage[user.id] is Stages.BRAND_SELECTION:
            if validate_brand(message.text):
                if message.text == 'Altro':
                    self.user_stage[user.id] = Stages.CUSTOM_BRAND_INSERTION
                    bot.send_message(chat_id, botDialogs.KEYBOARD_TEXTS['custom_brand_insertion'])
                else:
                    self.pending_ads[user.id].brand = message.text # Insert brand name
                    self.logger.info("User %s selected brand %s for its Ad", user.name, message.text)
                    self.user_stage[user.id] = Stages.SHOE_NAME_SELECTION
                    bot.send_message(chat_id, botDialogs.KEYBOARD_TEXTS['shoe_name_selection'])
            else:
                bot.send_message(chat_id, botDialogs.DIALOGS['brand_not_valid'])
                self.set_keyboard(user, update, bot)
            return

        # Custom Brand insertion
        if self.user_stage[user.id] is Stages.CUSTOM_BRAND_INSERTION:
            self.pending_ads[user.id].brand = message.text
            self.logger.info("User %s selected brand %s for its Ad", user.name, message.text)
            self.user_stage[user.id] = Stages.SHOE_NAME_SELECTION
            bot.send_message(chat_id, botDialogs.KEYBOARD_TEXTS['shoe_name_selection'])
            return

        # Shoe name insertion
        if self.user_stage[user.id] is Stages.SHOE_NAME_SELECTION:
            self.pending_ads[user.id].shoe_name = message.text
            self.logger.info("User %s inserted shoe name: %s", user.name, message.text)
            self.user_stage[user.id] = Stages.NUMBER_SELECTION # Change stage
            self.set_keyboard(user, update, bot)
            return

        # Shoe number selection
        if self.user_stage[user.id] is Stages.NUMBER_SELECTION:
            if validate_size(message.text):
                self.pending_ads[user.id].number = float(message.text)
                self.logger.info("User %s inserted shoe number: %f", user.name, float(message.text))
                self.user_stage[user.id] = Stages.CONDITION_SELECTION
                self.set_keyboard(user, update, bot)
            else:
                bot.send_message(chat_id, botDialogs.DIALOGS['shoe_size_error'])
                self.set_keyboard(user, update, bot)
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

        # Notes confirm
        if self.user_stage[user.id] is Stages.NOTE_INSERT_REQ:
            if message.text == 'SI':
                self.user_stage[user.id] = Stages.NOTE_INSERT
                bot.send_message(chat_id, botDialogs.KEYBOARD_TEXTS['note_insert'])
            elif message.text == 'NO':
                self.user_stage[user.id] = Stages.AD_INSERT
                self.send_ad_preview(update, context)
                self.set_keyboard(user, update, bot)
            else:
                bot.send_message(chat_id, botDialogs.DIALOGS['not_valid_choice'])
                self.set_keyboard(user, update, bot)
            return

        # Notes insertion
        if self.user_stage[user.id] is Stages.NOTE_INSERT:
            self.pending_ads[user.id].notes = message.text
            self.send_ad_preview(update, context)
            self.user_stage[user.id] = Stages.AD_INSERT
            self.set_keyboard(user, update, bot)
            return

        # Price selection
        if self.user_stage[user.id] is Stages.PRICE_SELECTION:
            if not message.text.isdigit():
                bot.send_message(chat_id, botDialogs.DIALOGS['digit_error'])
            else:
                self.pending_ads[user.id].price = int(message.text)
                self.logger.info("User %s inserted price: %d", user.name, int(message.text))
                if self.pending_ads[user.id].type is AdTypes.SELL:
                    self.user_stage[user.id] = Stages.SET_AVAILABILITY
                    self.set_keyboard(user, update, bot)
                elif self.pending_ads[user.id].type is AdTypes.BUY :
                    self.user_stage[user.id] = Stages.NOTE_INSERT_REQ
                    self.set_keyboard(user, update, bot)
            return

        # Set Availabilty
        if self.user_stage[user.id] is Stages.SET_AVAILABILITY:
            if message.text == 'SI':
                self.pending_ads[user.id].availability = "available"
                self.user_stage[user.id] = Stages.SET_SHIPPING
                self.set_keyboard(user, update, bot)
            elif message.text == 'NO':
                self.user_stage[user.id] = Stages.STORE_INSERTION
                bot.send_message(chat_id, botDialogs.KEYBOARD_TEXTS['store_insertion'])
            else:
                bot.send_message(chat_id, botDialogs.DIALOGS['not_valid_choice'])
                self.set_keyboard(user, update, bot)
            return

        # Store insertion
        if self.user_stage[user.id] is Stages.STORE_INSERTION:
            self.pending_ads[user.id].availability = message.text
            self.user_stage[user.id] = Stages.SET_SHIPPING
            self.set_keyboard(user, update, bot)
            return

        # Set shipping
        if self.user_stage[user.id] is Stages.SET_SHIPPING:
            if message.text == 'SI':
                self.pending_ads[user.id].shipping = True
                self.user_stage[user.id] = Stages.ACCEPT_PAYPAL
                self.set_keyboard(user, update, bot)
            elif message.text == 'NO':
                self.pending_ads[user.id].shipping = False
                self.user_stage[user.id] = Stages.ACCEPT_PAYPAL
                self.set_keyboard(user, update, bot)
            else:
                bot.send_message(chat_id, botDialogs.DIALOGS['not_valid_choice'])
                self.set_keyboard(user, update, bot)
            return

        # Accept Paypal
        if self.user_stage[user.id] is Stages.ACCEPT_PAYPAL:
            if message.text == 'SI':
                self.pending_ads[user.id].accept_paypal = True
                self.user_stage[user.id] = Stages.PHOTO_INSERTION
                bot.send_message(chat_id, botDialogs.KEYBOARD_TEXTS['photo_insertion'])
            elif message.text == 'NO':
                self.pending_ads[user.id].accept_paypal = False
                self.user_stage[user.id] = Stages.PHOTO_INSERTION
                bot.send_message(chat_id, botDialogs.KEYBOARD_TEXTS['photo_insertion'])
            else:
                bot.send_message(chat_id, botDialogs.DIALOGS['not_valid_choice'])
                self.set_keyboard(user, update, bot)
            return

        # Begin Feedback
        if self.user_stage[user.id] is Stages.INSERT_FEEDBACK:
            if message.text == user.name:
                bot.send_message(chat_id, botDialogs.DIALOGS['autovote_error'])
                self.user_stage[user.id] = Stages.MENU
                self.set_keyboard(user, update, bot)
                return
            self.feedbacking[user.id] = message.text
            self.user_stage[user.id] = Stages.EVALUATE_FEEDBACK
            self.set_keyboard(user, update, bot)
            return

        # Evaluate Feedback
        if self.user_stage[user.id] is Stages.EVALUATE_FEEDBACK:
            if message.text == 'Positiva':
                self.vote(bot, message, self.feedbacking[user.id], 1)
                self.user_stage[user.id] = Stages.MENU
                self.set_keyboard(user, update, bot)
            elif message.text == 'Negativa':
                self.vote(bot, message, self.feedbacking[user.id], -1)
                self.user_stage[user.id] = Stages.MENU
                self.set_keyboard(user, update, bot)
            else:
                bot.send_message(chat_id, botDialogs.DIALOGS['not_valid_choice'])
                self.set_keyboard(user, update, bot)
            self.logger.info("User %s is giving a feedback on user %s", user.name, self.feedbacking[user.id])
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
            bot.send_message(chat_id=chat_id, text=caption, parse_mode=ParseMode.HTML)
        elif ad.type is AdTypes.SELL:
            bot.send_photo(chat_id=chat_id, photo=ad.photo, caption=caption,
                            parse_mode=ParseMode.HTML)

    def set_group(self, update, context):
        message = update.message
        user = message.from_user
        chat_id = message.chat_id
        bot = context.bot

        if user.id in self.admin_list:
            self.group_id = chat_id
            bot.send_message(chat_id, botDialogs.DIALOGS['confirm_group_set'])
        else:
            bot.send_message(chat_id, botDialogs.DIALOGS['permission_denied'])

    def new_password(self, update, context):
        message = update.message
        user = message.from_user
        chat_id = message.chat_id
        bot = context.bot

        if user.id in self.admin_list:
            try:
                m = hashlib.sha256()
                m.update(context.args[0].encode('utf-8'))
                if len(self.password) == 0:
                    self.password = m.digest()
                    update.message.reply_text(botDialogs.DIALOGS['password_updated'])
                else:
                    if self.password == m.digest():
                        n = hashlib.sha256()
                        n.update(context.args[1].encode('utf-8'))
                        self.password = n.digest()
                        update.message.reply_text(botDialogs.DIALOGS['password_updated'])
                    else:
                        bot.send_message(chat_id, botDialogs.DIALOGS['invalid_password'])
            except IndexError:
                bot.send_message(chat_id, botDialogs.DIALOGS['error_set_password'])
        else:
            bot.send_message(chat_id, botDialogs.DIALOGS['permission_denied'])
            
    def set_admin(self, update, context):
        message = update.message
        user = message.from_user
        chat_id = message.chat_id
        bot = context.bot

        if user.id in self.admin_list:
            bot.send_message(chat_id, botDialogs.DIALOGS['already_admin'])
            return

        if len(self.password) != 0:
            try:
                m = hashlib.sha256()
                m.update(context.args[0].encode('utf-8'))
                if self.password == m.digest():
                    self.admin_list.append(user.id)
                    bot.send_message(chat_id, botDialogs.DIALOGS['admin_set_confirm'])
                else:
                    bot.send_message(chat_id, botDialogs.DIALOGS['invalid_password'])
            except IndexError:
                update.message.reply_text(botDialogs.DIALOGS['invalid_set_admin_usage'])
        else:
            self.admin_list.append(user.id)
            bot.send_message(chat_id, botDialogs.DIALOGS['admin_set_confirm'])

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
            self.user_stage[user.id] = Stages.NOTE_INSERT_REQ
            self.set_keyboard(user, update, bot)

        return

    def format_pending_ad(self, user, review=False):
        ad = self.pending_ads[user.id]
        return self.format_ad(ad, user, review)

    def format_number(self, number):
        try:
            float(number)
        except ValueError:
            self.logger.info("Value Error")
            return "Err"

        if float(number) == float(int(number)):
            return str(int(number))
        else:
            return str(number)

    def format_ad(self, ad, user, review=False):
        if ad.type is AdTypes.SELL:
            caption = 'Vendo <b>' + escape(ad.brand) + ' ' + escape(ad.shoe_name) + '</b>'
            caption = caption + '\nLuogo: ' + escape(ad.region)
            caption = caption + '\nCondizione: ' + escape(ad.condition) + ' | Prezzo: ' + self.format_number(ad.price) + '€'
            caption = caption + '\nTaglia: ' + self.format_number(ad.number)
            caption = caption + '\nDisponibilità: '
            if ad.availability == 'available':
                caption = caption + '<i>Disponibile</i>'
            else:
                caption = caption + '<i>In arrivo, acquistata presso ' + escape(ad.availability) + '</i>'
            caption = caption + '\nSpedizione: '
            if ad.shipping:
                caption = caption + 'si'
            else:
                caption = caption + 'no'
            caption = caption + ' | Accetta Paypal: '
            if ad.accept_paypal:
                caption = caption + 'si'
            else:
                caption = caption + 'no'
            if ad.notes != "":
                caption = caption + "\nNote: " + '<i>' + escape(ad.notes) + '</i>'
            caption = caption + '\nContattare: ' + escape(user.name)
            if self.count_feedbacks(user.id, 1) != 0:
                caption = caption + '<i>\nUtente con ' + str(self.count_feedbacks(user.id, 1)) + ' feedback positivi</i>'
            if self.count_feedbacks(user.id, -1) != 0:
                caption = caption + '<i>\nUtente con ' + str(self.count_feedbacks(user.id, -1)) + ' feedback negativi</i>'
        else:
            caption = 'Cerco <b>' + escape(ad.brand) + ' ' + escape(ad.shoe_name) + '</b>'
            caption = caption + '\nLuogo: ' + escape(ad.region)
            caption = caption + '\nCondizione: ' + escape(ad.condition) + ' | ' + 'Budget: ' + self.format_number(ad.price) + '€'
            caption = caption +'\nTaglia: ' + self.format_number(ad.number)
            if ad.notes != "":
                caption = caption + "\nNote: " + '<i>' + escape(ad.notes) + '</i>'
            caption = caption + '\nContattare: ' + escape(user.name)

        if review:
            caption = caption + '\nID: ' + ad.id

        return caption

    def update_save_file(self, save_file, my_list):
        json_string = jsonpickle.encode(my_list)
        with open(save_file, 'w') as f:
            f.write(json_string)
    
    def update_next_id(self):
        with open(self.id_save_file, 'w') as f:
            f.write(str(self.next_id))

    def load_save_file(self):
        # Ads
        try:
            if os.stat(self.ads_save_file).st_size != 0:
                with open(self.ads_save_file, 'r') as f:
                    json_string = f.read()
                    self.ads = jsonpickle.decode(json_string)
            self.logger.info("Successfully loaded ads save file")
        except FileNotFoundError:
            self.logger.info("No ads save file found")
            self.ads = []
        except pickle.PickleError:
            self.ads = []
            self.update_save_file(self.ads_save_file, self.ads)

        # Users
        try:
            if os.stat(self.user_save_file).st_size != 0:
                with open(self.user_save_file, 'r') as f:
                    json_string = f.read()
                    self.user_list = jsonpickle.decode(json_string)
            self.logger.info("Successfully loaded users save file")
        except FileNotFoundError:
            self.logger.info("No user save file found")
            self.user_list = []
        except pickle.PickleError:
            self.user_list = []
            self.update_save_file(self.user_save_file, self.user_list)
        
        # Feedback
        try:
            if os.stat(self.feedback_save_file).st_size != 0:
                with open(self.feedback_save_file, 'r') as f:
                    json_string = f.read()
                    self.feedback_list = jsonpickle.decode(json_string)
            self.logger.info("Successfully loaded feedback save file")
        except FileNotFoundError:
            self.logger.info("No feedback save file found")
            self.feedback_list = []
        except pickle.PickleError:
            self.feedback_list = []
            self.update_save_file(self.feedback_save_file, self.feedback_list)
        
        # Last id
        try:
            with open(self.id_save_file, 'r') as f:
                self.next_id = int(f.read())
        except ValueError:
            print("FUCK!")
        except FileNotFoundError:
            self.logger.info("No id file found")
            self.next_id = 1
        
    def run(self):
        # Start the bot
        self.updater.start_polling()
        # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT
        self.updater.idle()
