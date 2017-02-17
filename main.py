import time
import asyncio
import logging.config
import traceback
from collections import defaultdict

import database
import my_token
import tbot
import time_service
import location_service
import utils
from utils import *
from utils import BotMsg

# todo narrow BaseException
# todo move logic from this file to dialog.py
# todo add some classes: think about common logic parts for all sessions(it can be callable class)
# todo i18n ?
# todo use ids for buttons, dictionaries instead of lists
# todo there are lot of uncertainties in lower-capital-cases
# todo fix all 'while True:' loops, there are almost explicit invariant which should be relied
# todo after all: check and tidy up with logging
# todo fix outdated descriptions
help_message = ''' Бот находится в разработке, не рассчитывайте на сохранение данных.
Бот позволяет создавать напоминалки, привязанные к месту и времени.'''

'''
Ожидаются команды на добавление или удаление события, запрос на события по месту.
Грамматика
place="[^,]*"
event=".*"
number="\d*"
empty=""
Запросы
1. (напомни|добавь) %event% (,%place%|)
\t добавляет событие для локации. Если не указана, будет произведен запрос от бота
2. (место|события) %place%
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
ts = time_service.TimeService()
# yesno = ['/yes', '/no']
yesno = None
YES_NO_CANCEL = ['1. да', '2. нет', '3. отменить']


# todo create class Session(i.e. run async functions in it) and move this to it
class Memory:
    def __init__(self, user):
        self.user = user
        self.cur_place = None
        self.last_events = None
        self.event_name = None
        self.place_name = None
        self.place_id = None


def parse_place_name(place_name):
    if place_name is not None and len(place_name) > 0 and place_name[0] == '<' and place_name[-1] == '>':
        place_name = place_name[1:-1]
    return place_name


def add_enumeration(iterable):
    return ['{}. {}'.format(idx + 1, caption) for idx, caption in enumerate(iterable)]


def recognize_user_text(text, captions):
    """ todo check invariant: this method should be called after calling #get_buttons """
    idx = utils.parse_int(text)
    if idx is not None and 1 <= idx <= len(captions):
        return captions[idx - 1]
    for caption in captions:
        # todo fix
        if caption.endswith(text) or text.endswith(caption):
            return caption
    return None


class Event:
    def __init__(self, event_name):
        self.event_name = event_name
        self.place_name = None
        self.time = None
        self.saved_captions = None

    def message0(self):
        event_name_str = '<{}>'.format(self.event_name)
        place_str = None if self.place_name is None else 'место: <{}>'.format(self.place_name)
        time_str = None if self.time is None else 'время: <{}>'.format(self.time)
        return ', '.join(i for i in (event_name_str, place_str, time_str) if i is not None)

    def message(self):
        return 'Событие: ' + self.message0()

    def __str__(self):
        return self.message()

    def done_message(self):
        return 'Событие добавлено: ' + self.message0()

    def get_buttons(self):
        self.saved_captions = [DONE]
        if self.place_name is None:
            self.saved_captions.append(DEFINE_PLACE)
        if self.time is None:
            self.saved_captions.append(DEFINE_TIME)
        self.saved_captions.append(CANCEL)
        return add_enumeration(self.saved_captions)

    def set_place_name(self, place_name):
        # todo add assertion that place_name exists in db
        self.place_name = place_name

    def set_time(self, time):
        self.time = time

    def recognize_user_text(self, text):
        """ todo check invariant: this method should be called after calling #get_buttons """
        return recognize_user_text(text, self.saved_captions)


def add_event_session(user, suffix):
    # todo fix
    suffix = None
    logger.debug('action: adding event, <%s>', suffix)
    # todo recognize sequences: what-where-when, what-when, what-where
    event_name = suffix
    while event_name is None:
        user_msg = yield BotMsg(text='Какое событие?')
        event_name = user_msg.text.strip()
        logger.debug('for user %s received event name: %s', user, event_name)
    event = Event(event_name)
    undefined = False
    while True:
        text = event.message()
        if undefined:
            text = 'Неизвестная команда! ' + text
        user_msg = yield BotMsg(text=text, buttons=event.get_buttons())
        text = user_msg.text
        answer = event.recognize_user_text(text)
        if answer == DONE:
            break
        elif answer == CANCEL:
            return (yield BotMsg.done_message(text='Отменено добавление события.'))
        elif answer == DEFINE_PLACE:
            place_name = None
            while place_name is None:
                # todo add variants with places
                user_msg = yield BotMsg(text='Какое место?', buttons=[SKIP, CANCEL_ADDING_EV])
                place_name = user_msg.text
                if place_name == SKIP:
                    break
                if place_name == CANCEL_ADDING_EV:
                    return (yield BotMsg.done_message(text='Отменено добавление события.'))
                place = db.get_place(user, place_name)
                if place is None:
                    answer = yield BotMsg(text='Место <%s> не найдено. Добавить?' % place_name, buttons=YES_NO_CANCEL)
                    if answer.accepted():
                        db.add_place(user, place_name)
                        break
                    elif answer.declined():
                        place_name = None
                        continue
                    elif answer.cancel():
                        return (yield BotMsg(text='Отменено добавление события!'))
            event.set_place_name(place_name)
        elif answer == DEFINE_TIME:
            event_time = yield from ts.define_time()
            event.set_time(event_time)
        else:
            undefined = True

    db.add_event(user=user, place_name=event.place_name, name=event.event_name, event_time=event.time)
    # if event.time is not None:
    #     ts.add_remind_task(user, event)
    # todo decide what is more effective: checking priority-queue or just put all events to remind in db
    return (yield BotMsg.done_message(text=event.done_message()))


def remove_events_session(user, text):
    logger.debug('action: removing event, <%s>', text)
    memory = memories[user]
    events = memory.last_events
    if events is None or len(events) < 1:
        return (yield BotMsg(text='Ошибка! Не могу ничего удалить!'))
    if text == 'все':
        answer = yield BotMsg(text='Удалить все события?', buttons=yesno)
        if answer.accepted():
            # todo optimize this cycle with removing by memory.last_place ?
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
        answer = yield BotMsg(text='Удалить событие <%s> для места <%s>?' % (ev['name'], ev['place']), buttons=yesno)
        if answer.accepted():
            db.remove_event(user, ev)
            text = 'Событие удалено!'
        else:
            text = 'Событие не было удалено!'
        memory.last_events = None
        return (yield BotMsg.done_message(text=text))


def text_for_events(events):
    if len(events) == 0:
        return 'Нет событий.'
    if len(events) == 1:
        return 'Событие: ' + events[0]['name']
    events_lines = add_enumeration(e['name'] for e in events)
    return 'События: \n%s' % '\n'.join(events_lines)


def remind_events_session(user, place_name):
    logger.debug('action: reminding events for place, <%s>', place_name)
    if place_name is None:
        # todo output enumerated list of places
        places = db.get_all_places(user=user)
        place_names = [l['name'] for l in places]
        places = ['0. все события'] + add_enumeration(place_names)
        answer = yield BotMsg(text='Какое место?', buttons=places)
        if answer.text.startswith('0') or 'все события' in answer.text:
            place_name = None
        else:
            place_name = recognize_user_text(answer.text, place_names)
    if place_name is not None:
        place = db.get_place(user, place_name)
        if place is None:
            return (yield BotMsg(text='Место не найдено!'))
            # todo add adding place
    else:
        place = None

    memory = memories.get(user)
    if memory is None:
        memory = memories[user] = Memory(user)
    memory.cur_place = place
    if place is not None:
        events = db.get_events_by_place(user, place['name'])
    else:
        assert place_name is None
        events = db.get_all_events(user)
    memory.last_events = events
    text = text_for_events(events)
    return (yield BotMsg.done_message(text=text))


# todo add add_place_session branch ??
def update_place_session(user, suffix):
    place_name_to_edit = None
    while True:
        places = db.get_all_places(user)
        names = [l['name'] for l in places] + ['отмена']
        answer = yield BotMsg(text='Какое место вы хотите редактировать?', buttons=add_enumeration(names))
        place_name = recognize_user_text(answer.text, names)
        if place_name == 'отмена':
            return (yield BotMsg.done_message(text='отменено редактирование события!'))
        if place_name is None:
            # todo refactor: we need something like "resolve_place_sub_dialog"(and in add_event_session)
            answer = yield BotMsg(text='Место <%s> не найдено. Добавить?' % place_name, buttons=YES_NO_CANCEL)
            if answer.accepted():
                db.add_place(user, place_name)
            elif answer.declined():
                continue
            elif answer.cancel():
                # todo fix duplicating logic
                return (yield BotMsg.done_message(text='отменено редактирование события!'))
                # todo add another branch??
        else:
            place_name_to_edit = place_name
            break

    # todo add 'удалить'
    # todo recognize is location exist(it should be easy after fixing @1)
    RENAME_PLACE, UPDATE_LOC, FINISH_EDITING = 'переименовать', 'добавить/изменить локацию', 'закончить редактирование'
    actions = [RENAME_PLACE, UPDATE_LOC, FINISH_EDITING]
    prefix = ''
    while True:
        answer = yield BotMsg(text=prefix + 'Что вы хотите сделать с местом <{}>?'.format(place_name_to_edit),
                              buttons=add_enumeration(actions))
        action = recognize_user_text(answer.text, actions)
        # todo fix logic
        if action == RENAME_PLACE:
            request = 'Введите новое имя'
            renaming_in_progress = True
            while renaming_in_progress:
                answer = yield BotMsg(text=request)
                new_place_name = parse_place_name(answer.text)
                if new_place_name is None:
                    request = 'Ничего не введено. Попробуйте ещё раз.'

                confirmation = yield BotMsg(
                    text='Старое имя: <{}>. Новое имя: <{}>'.format(place_name_to_edit, new_place_name),
                    buttons=YES_NO_CANCEL)
                # todo logic extraction: common method for the confirmation, exception isn't good in any case
                while True:
                    if confirmation.accepted():
                        db.rename_place(user, place_name_to_edit, new_place_name)
                        place_name_to_edit = new_place_name
                        # todo wtf?? prefix should visible out of this scope
                        prefix = 'Переименовано. '
                        renaming_in_progress = False
                        break
                    elif answer.declined():
                        request = 'Введите новое имя'
                        break
                    elif answer.cancel():
                        return (yield BotMsg.done_message('отменено редактирование события!'))
                    else:
                        request = 'Ответ не распознан. Попробуйте ещё раз.'
        elif action == UPDATE_LOC:
            # todo extract branch with getting location to the location_service ?
            str_location_for_db = None
            prefix = ''
            while str_location_for_db is None:
                answer = yield BotMsg(
                    text=prefix + 'Введите координаты места в формате "59.939095, 30.315868" или просто пришлите локацию.')
                if answer.location is not None:
                    str_location_for_db = format_location(answer.location)
                elif answer.text is not None:
                    if answer.text == 'отмена':
                        break
                    str_location_for_db = parse_location(answer.text)
                    if str_location_for_db is not None:
                        break
                    else:
                        prefix = 'Некорректные координаты. '
            if str_location_for_db is None:
                # todo wtf?? prefix should visible out of this scope
                prefix = 'Отменено добавление локации'
                continue
            else:
                db.update_location_for_place(user, place_name_to_edit, str_location_for_db)
                prefix = 'Локация обновлена. '

            pass
        elif action == FINISH_EDITING:
            return (yield BotMsg.done_message(text='Редактирование завершено.'))
        else:
            # todo wtf?? prefix should visible out of this scope
            prefix = 'Действие не распознано, попробуйте ещё раз. '

    pass


def help_session(user, suffix):
    global help_message
    logger.debug('action: help')
    return (yield BotMsg.done_message(text=help_message))


UNEXPECTED_COMMAND = 'Неизвестная команда! Введите "помощь" чтобы посмотреть список команд.'


def unrecognized_session(user, suffix):
    logger.debug('action: unrecognized')
    return (yield BotMsg.done_message(text=UNEXPECTED_COMMAND))

def format_place(place_entry):
    if 'location' in place_entry:
        loc_suffix = ' ({})'.format(place_entry['location'])
    else:
        loc_suffix = ''
    return place_entry['name'] + loc_suffix

def get_places_session(user, suffix):
    logging.debug('action: get places for user %s', user)
    places = db.get_all_places(user)
    names = lmap(format_place, places)
    if len(names) == 0:
        text = 'Нет мест!'
    elif len(names) == 1:
        text = 'Известно одно место: %s' % names[0]
    else:
        text = 'Места:\n' + '\n'.join(add_enumeration(names))
    return (yield BotMsg.done_message(text=text))


class DialogStarterRecognizer:
    def __init__(self, idx, button_caption, allowed_prefixes, generator_function):
        self.idx = idx
        self.button_caption = button_caption
        self.allowed_prefixes = allowed_prefixes
        self.generator_function = generator_function
        self.button_message = '{}. {}'.format(self.idx, self.button_caption) if self.has_button_message() else None

    def _allowed(self, prefix):
        if prefix in self.allowed_prefixes:
            return True
        i = utils.parse_int(prefix)
        if i == self.idx:
            return True
        if prefix == str(self.idx) + '.':
            return True
        return False

    def get_button_message(self):
        return self.button_message

    def has_button_message(self):
        return self.idx is not None and self.button_caption is not None

    def get_generator(self, prefix):
        if self._allowed(prefix):
            return self.generator_function
        else:
            return None


class UnrecognizedStarter(DialogStarterRecognizer):
    def _allowed(self, prefix):
        return True

# todo unique logic for the answer recognition
def checkin_session(user, suffix):
    places = db.get_all_places(user)
    names = [l['name'] for l in places]
    suffix_2 = suffix[:-2]
    checkin_place = None
    for name in names:
        if name.startswith(suffix_2):
            checkin_place = name
            break
    if checkin_place is None:
        return (yield BotMsg.done_message(text='Место не найдено. Попробуйте ещё раз.'))
    db.update_current_place(user, checkin_place)
    return (yield BotMsg.done_message(text='Текущее место - <{}>'.format(checkin_place)))


START_RECOGNIZERS = [
    DialogStarterRecognizer(1, 'Добавить событие', ['добавить', 'напомни', 'добавь'], add_event_session),
    DialogStarterRecognizer(2, 'Напомнить события', ['место', 'события'], remind_events_session),
    DialogStarterRecognizer(3, 'Удалить события', ['удали'], remove_events_session),
    DialogStarterRecognizer(4, 'Список мест', ['места'], get_places_session),
    DialogStarterRecognizer(5, 'Изменить место', ['редактировать место'], update_place_session),
    DialogStarterRecognizer(6, 'Помощь', ['помощь'], help_session),
    DialogStarterRecognizer(7, 'Текущее место', ['я в'], checkin_session),
    UnrecognizedStarter(8, None, None, unrecognized_session),
]
MAIN_DEFAULT_BUTTONS = [r.get_button_message() for r in START_RECOGNIZERS if r.has_button_message()]
update_default_buttons(MAIN_DEFAULT_BUTTONS)


def start_session(user):
    user_msg = yield
    while True:
        logger.debug('received for user %s: %s', user, user_msg)
        # todo fix logic? user_msg can't be empty
        # todo totally fix! This is very unusable!
        prepared_user_msg = user_msg.text.lower()
        if prepared_user_msg.startswith('я в '):
            prefix, suffix = 'я в', prepared_user_msg[4:]
        else:
            prefix, suffix = utils.split_first(prepared_user_msg, ' ')
        for starter_recognizer in START_RECOGNIZERS:
            generator_fun = starter_recognizer.get_generator(prefix)
            if generator_fun is not None:
                user_msg = yield from generator_fun(user, suffix)
                break
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
        answer = BotMsg.done_message(text='Произошла ошибка, попробуйте ещё')
        del sessions[user]

    logger.debug('bot  %s: %s', user, answer)
    return answer


# todo replace with cache with timeout?
memories = defaultdict(Memory)
sessions = {}
# todo hide token!!!
token = my_token.TOKEN


# todo encapsulate logic in some class
# todo add #configure in all helper modules?
# todo is it enough private - store data entries for all users in one table?

# todo implement, just grab from db all remind events with empty loc and check that now.time < reminder.time or do some manipulations if there are location defined
def check_tasks(self):
    while not self.queue.empty():
        first_task = self.queue.get()
        if first_task.should_remind():
            yield first_task
        else:
            self.queue.put(first_task)
            break


# todo add clean_up task which should clean tasks maybe once at hour
def get_message(task):
    event_name = task['name']
    event_place = task.get('place', None)
    event_time = task.get('time', None)
    place_suffix = '' if event_place is None else '; Место: ' + str(event_place)
    time_suffix = '' if event_time is None else '; Время: ' + time_service.format_time(event_time)
    return 'Напоминание: ' + str(event_name) + place_suffix + time_suffix


# todo move it to time_service????
def current_milli_time():
    return int(round(time.time()))


async def reminder():
    logging.debug('Reminder started...')
    await asyncio.sleep(4)
    try:
        while True:
            now = current_milli_time()
            tasks, done_callback = db.check_tasks(now)
            for task in tasks:
                # todo check that it's time to remind
                user = task['user']
                logging.debug('reminding, user: %s, event: %s', user, task['name'])
                await tbot.send_remind_message(user, get_message(task))
                done_callback(task)

            # todo check dimensions
            # todo fix magic constants
            tasks_with_loc, done_callback = db.check_tasks(now + 3600*2)
            for task in tasks_with_loc:
                task_place = task['place']
                task_time = task['time']
                if task_place is not None and task_time is not None:
                    user = task['user']
                    cur_place = db.get_current_place(user)
                    if cur_place is not None:
                        loc_from = db.get_place(user, cur_place.get('place')).get('location')
                        loc_to = db.get_place(user, task_place).get('location')
                        if loc_from != loc_to:
                            if loc_from is not None and loc_to is not None:
                                time_to_move = location_service.get_expected_time(loc_from, loc_to)
                                if time_to_move + now > task_time:
                                    await tbot.send_remind_message(user,
                                                                   'Пора выходить! ' +
                                                                   get_message(task) +
                                                                   '. Время в пути: ' +
                                                                   time_service.format_time_delta(time_to_move))
                                    done_callback(task)
            await asyncio.sleep(15)
            # todo 10-15 is enough
    except BaseException:
        print('something wrong happens here!!!!')
        traceback.print_exc()
        raise InterruptedError


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(reminder())
    print('added reminder')

    tbot.start_bot(loop, token, chat)

    loop.run_forever()
    print('Invoked infinity loop...')
