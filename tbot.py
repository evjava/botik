import asyncio
import logging.config

import telepot
import telepot.aio
from telepot.namedtuple import ReplyKeyboardMarkup, ReplyKeyboardHide

logger = None


class UserMsg:
    def __init__(self, text=None, button=None):
        self.text = text
        self.button = button

    def is_empty(self):
        return self == EMPTY_MESSAGE or (self.text is None and self.button is None)

    def accepted(self):
        # todo fix logic:
        return self.text == 'да' or self.button == '/yes' or 'yes' in self.text

    def __repr__(self):
        # todo rollback, too expensive
        return 'UserMsg: <{}> <{}>'.format(self.text.replace('\n', ' ')[:60], self.button)


EMPTY_MESSAGE = UserMsg(text=None, button=None)


def build_markup(buttons):
    if buttons:
        markup = ReplyKeyboardMarkup(keyboard=buttons)
    else:
        markup = ReplyKeyboardHide()
    return markup


async def on_chat_message(msg):
    logger.debug('raw msg: %s', msg)
    content_type, chat_type, chat_id = telepot.glance(msg)
    if content_type != 'text':
        return
    user, text = msg['from']['id'], msg['text']
    logger.debug('From user %s: %s', user, text)
    if message_processor is not None:
        bot_msg = message_processor(user, UserMsg(text=text.lower()))
        logger.debug('To user %s: %s', user, bot_msg)
        # todo add descriptions to all assertions
        assert bot_msg is not None
        markup = build_markup(bot_msg.buttons)
        text = bot_msg.text
        assert text is not None
        await bot.sendMessage(chat_id, text, reply_markup=markup)


bot = None
message_processor = None


def start_bot(token, msg_processor):
    global logger
    logger = logging.getLogger('tpot_wrapper')
    global message_processor, bot
    bot = telepot.aio.Bot(token)
    message_processor = msg_processor
    # answerer = telepot.aio.helper.Answerer(bot)
    loop = asyncio.get_event_loop()
    loop.create_task(bot.message_loop({'chat': on_chat_message}))
    print('Listening ...')
    loop.run_forever()
