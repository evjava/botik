import logging.config

import database
import sys
import tbot
import utils
from random import random

# todo i18n ?
help_message = '''Ожидаются команды на добавление или удаление события, запрос на события по месту.
Грамматика
location="[^,]*"
event=".*"
number="\d*"
empty=""
Запросы
1. (напомни|добавь) %event% (,%location%|)
\t добавляет событие для локации. Если не указана, будет произведен запрос от бота
2. (место|события) %location%
\t показывает все добавленные события для места
3. удали (все|number|empty)
\t после команды 2 удаляет заданн-ое(ые) событи-е(я). Для следующего удаления нужно снова вызвать 2
\t все - удаляет все события
\t number - удаляет событие по номеру из выведенного списка
\t в случае если было только одно событие, удаляет его
4. места
\t выводит список известных мест
'''
logging.config.fileConfig('logging.conf')
logger = logging.getLogger('main')

db = database.MongoWrapper()
# yesno = ['/yes', '/no']
yesno = None


class BotMsg:
    def __init__(self, text=None, buttons=None):
        self.text = text
        self.buttons = buttons

    def __repr__(self):
        # todo rollback, too expensive
        return 'BotMsg: <{}> <{}>'.format(self.text.replace('\n', ' ')[:60], self.buttons)


# todo create class Session(i.e. run async functions in it) and move this to it
class Memory:
    def __init__(self, user):
        self.user = user
        self.cur_location = None
        self.last_events = None
        self.event_name = None
        self.loc_name = None
        self.loc_id = None

def parse_loc_name(loc_name):
    if loc_name and len(loc_name) > 0 and loc_name[0] == '<' and loc_name[-1] == '>':
        loc_name = loc_name[1:-1]
    return loc_name

def add_event_session(user, text):
    logger.debug('action: adding event, <%s>', text)
    name, loc_name = utils.split_last(text, ',')
    # todo refactor: duplicated logic
    if loc_name is None or loc_name == '':
        user_msg = yield BotMsg(text='Какое место?')
        loc_name = user_msg.text.strip()
        logger.debug('for user %s received location: %s', user, loc_name)
    while True:
        loc = db.get_location(user, loc_name)
        if loc is None:
            # todo add yesno function
            answer = yield BotMsg(text='Место <%s> не найдено. Добавить?' % loc_name, buttons=yesno)
            if answer.accepted():
                db.add_location(user, loc_name)
                break
            elif answer.cancel():
                return (yield BotMsg(text='Отменено добавление события!'))
            else:
                loc_name = yield BotMsg(text='Введите новое место')
                loc_name = loc_name.strip()
        else:
            break
    db.add_event(user=user, loc_name=loc_name, name=name, time=None)
    return (yield BotMsg(text='Событие <%s> добавлено для места <%s>!' % (name, loc_name)))


def remove_events_session(user, text):
    logger.debug('action: removing event, <%s>', text)
    memory = memories[user]
    events = memory.last_events
    if events is None or len(events) < 1:
        return (yield BotMsg(text='Ошибка! Не могу ничего удалить!'))
    if text == 'все':
        answer = yield BotMsg(text='Удалить все события?', buttons=yesno)
        if answer.accepted():
            # todo optimize this cycle with removing by memory.last_location ?
            for ev in events:
                db.remove_event(user, ev)
        memory.last_events = None
        return (yield BotMsg(text='События удалены!'))
    else:
        if text is None and len(events) == 1:
            nmb = 1
        else:
            nmb = utils.parse_int(text)
        if nmb is None or nmb < 1 or nmb > len(events):
            # todo i18n?
            return (yield BotMsg(text='Ошибка! Не могу ничего удалить! Ожидается число от 1 до {}'.format(len(events))))
        ev = events[nmb - 1]
        answer = yield BotMsg(text='Удалить событие <%s> для места <%s>?' % (ev['name'], ev['location']), buttons=yesno)
        if answer.accepted():
            db.remove_event(user, ev)
            text = 'Событие удалено!'
        else:
            text = 'Событие не было удалено!'
        memory.last_events = None
        return (yield BotMsg(text=text))


def text_for_events(events):
    if len(events) == 0:
        return 'Нет событий.'
    if len(events) == 1:
        return 'Событие: ' + events[0]['name']
    events_lines = ['%d. %s' % (idx + 1, e['name']) for idx, e in enumerate(events)]
    return 'События: \n%s' % '\n'.join(events_lines)


def remind_events_session(user, location_name):
    logger.debug('action: reminding events for location, <%s>', location_name)
    loc = db.get_location(user, location_name)
    if loc is None:
        return (yield BotMsg(text='Место не найдено!'))
        # todo add adding place?

    memory = memories.get(user)
    if memory is None:
        memory = memories[user] = Memory(user)
    memory.cur_location = loc
    events = db.get_events_by_location(user, loc['name'])
    memory.last_events = events
    text = text_for_events(events)
    return (yield BotMsg(text=text))


def help_session():
    global help_message
    logger.debug('action: help')
    return (yield BotMsg(text=help_message))


def unrecognized_session():
    logger.debug('action: unrecognized')
    return (yield BotMsg(text='Неизвестная команда! Введите "помощь" чтобы посмотреть список команд.'))


def get_locations_session(user):
    logging.debug('action: get locations for user %s', user)
    locations = db.get_all_locations(user)
    names = [l['name'] for l in locations]
    if len(names) == 0:
        text = 'Нет мест!'
    elif len(names) == 1:
        text = 'Известно одно место: %s' % names[0]
    else:
        text = 'Места: %s' % ', '.join(names)
    return (yield BotMsg(text=text))


def start_session(user):
    user_msg = yield
    while True:
        # rand = random()
        # logger.debug('random = %f', rand)
        # if user in [128746708, 36629165] and rand < 0.3:
        #     user_msg = yield BotMsg(text='Есть два стула - с хуями и с хуями. На какой сядешь?')
        #     user_msg = yield BotMsg(text='Сразу на два? Так и знал.')
        logger.debug('received for user %s: %s', user, user_msg)
        # todo fix logic? user_msg can't be empty
        if user_msg == tbot.EMPTY_MESSAGE:
            generator = unrecognized_session()
        else:
            prefix, suffix = utils.split_first(user_msg.text.lower(), ' ')
            if prefix in ['напомни', 'добавь']:
                generator = add_event_session(user, suffix)
            elif prefix == 'удали':
                generator = remove_events_session(user, suffix)
            elif prefix in ['место', 'события']:
                generator = remind_events_session(user, suffix)
            elif prefix == 'места':
                generator = get_locations_session(user)
            elif prefix == 'помощь':
                generator = help_session()
            else:
                generator = unrecognized_session()
        user_msg = yield from generator
        logger.debug('end of while')


def chat(user, msg):
    logger.debug('user %s: %s', user, msg)
    session = sessions.get(user)
    if session is None:
        logger.info('new session for user %s', user)
        session = sessions[user] = start_session(user)
        next(session)

    try:
        # todo wtf??? send returns something!
        answer = session.send(msg)
    except StopIteration:
        answer = BotMsg(text='Произошла ошибка, попробуйте ещё')
        del sessions[user]

    logger.debug('bot  %s: %s', user, answer)
    return answer


# todo replace with cache with timeout?
memories = {}
sessions = {}
# todo encapsulate logic in some class
# todo add #configure in all helper modules?
# todo is it enough private - store data entries for all users in one table?
token = sys.argv[1]
if __name__ == '__main__':
    tbot.start_bot(token, chat)
