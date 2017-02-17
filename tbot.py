import logging.config

import telepot
import telepot.aio
from telepot.namedtuple import ReplyKeyboardMarkup, ReplyKeyboardHide, KeyboardButton

import utils

logger = None


# todo move to utils? BotMsg is already moved
class UserMsg:
    def __init__(self, text=None, button=None, location=None):
        assert text is None or location is None, 'unexpected parameters for UserMsg!'
        self.text = text
        self.button = button
        self.location = location

    def is_empty(self):
        return self == EMPTY_MESSAGE or (self.text is None and self.button is None)

    def accepted(self):
        # todo fix logic:
        return 'да' in self.text or 'yes' in self.text or utils.parse_int(self.text) == 1

    def declined(self):
        # todo fix logic:
        return 'нет' in self.text or 'no' in self.text or utils.parse_int(self.text) == 2

    def cancel(self):
        # todo fix logic:
        return 'отмена' in self.text or 'cancel' in self.text or utils.parse_int(self.text) == 3

    def __repr__(self):
        # todo rollback, too expensive
        return 'UserMsg: <{}> <{}>'.format(self.text.replace('\n', ' ')[:60], self.button)


EMPTY_MESSAGE = UserMsg(text=None, button=None)


def build_markup(bot_msg):
    buttons = bot_msg.buttons
    if buttons is not None:
        markup = ReplyKeyboardMarkup(keyboard=[[i] for i in buttons])
    else:
        # if bot_msg.done_session:
        #     todo update
        # markup = START_BUTTONS
        # else:
        #     markup = ReplyKeyboardHide()
        markup = ReplyKeyboardHide()
    return markup


SEND_LOCATION_BUTTONS = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Location', request_location=True)]])

allowed_users = {131265966, 133881511, 36629165, 45595809, 79460132}

async def on_chat_message(msg):
    logger.debug('raw msg: %s', msg)
    content_type, chat_type, chat_id = telepot.glance(msg)
    if False and chat_id not in allowed_users:
        await bot.sendMessage(chat_id, 'Botik in progress of development...')
        return
    # todo fix logic, maybe it's good know about some context to agree location only when it's expected
    # if content_type != 'text':
    #     if content_type == 'location':
    #         print(msg['location'])
    #     return
    print(msg)
    user, text, location = msg['from']['id'], msg.get('text'), msg.get('location')
    logger.debug('From user %s: %s', user, text)
    # todo save and crypt all users data ??
    if message_processor is not None:
        lowered_text = None if text is None else text.lower()
        bot_msg = message_processor(user, UserMsg(text=lowered_text, location=location))
        logger.debug('To user %s: %s', user, bot_msg)
        # todo add descriptions to all assertions
        assert bot_msg is not None
        markup = build_markup(bot_msg)
        text = bot_msg.text
        assert text is not None
        await bot.sendMessage(chat_id, text, reply_markup=markup)


bot = None
message_processor = None


# todo is user and chat_id is the same?
async def send_remind_message(user, text):
    await bot.sendMessage(user, text)


def start_bot(loop, token, msg_processor):
    global logger
    logger = logging.getLogger('tpot_wrapper')
    global message_processor, bot
    bot = telepot.aio.Bot(token)
    message_processor = msg_processor
    loop.create_task(bot.message_loop({'chat': on_chat_message}))
    print('Listening ...')
