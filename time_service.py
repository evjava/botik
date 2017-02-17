import datetime

from utils import *
import time

TIME_BUTTONS_0 = ['через 20 сек', 'через полчаса', 'через час', 'через 2 часа']
'''
через 15 минут
через полчаса
через 45 минут
через час
через полтора часа
через 2 часа
через 3 часа
'''
TIME_BUTTONS = TIME_BUTTONS_0 + [SKIP, CANCEL_ADDING_EV]

PREP_RELATIVE = 'через'


# todo put reminders to the db to prevent losing event after restart
class RemindTask:
    def __init__(self, user, event):
        self.user = user
        self.event = event
        self.time = event.time
        assert self.time is not None

    def should_remind(self):
        return self.time < now()

    def message(self):
        return 'Напоминание: ' + str(self.event)

    def __cmp__(self, other):
        return self.time <= other.time


def now():
    return datetime.datetime.now()


def parse_time_delta(delta_tokens):
    if len(delta_tokens) == 1 and delta_tokens[0] == 'полчаса':
        # i suppose that it's too strange use 'полчаса' with other tokens
        total_delta = datetime.timedelta(minutes=30)
        return total_delta

    total_delta = datetime.timedelta()
    for idx, tok in enumerate(delta_tokens):
        delta = None
        if tok.startswith('час'):
            delta = datetime.timedelta(hours=1)
        elif tok.startswith('дн') or tok.startswith('ден'):
            delta = datetime.timedelta(days=1)
        elif tok.startswith('мин'):
            delta = datetime.timedelta(minutes=1)
        elif tok.startswith('сек'):
            delta = datetime.timedelta(seconds=1)
        count_tok = delta_tokens[idx - 1]
        if count_tok == 'полтора':
            count_for_delta = 1.5
        else:
            count_for_delta = 1 if idx == 0 else parse_int(count_tok, 1)
        if delta is not None:
            delta *= count_for_delta
            total_delta += delta
    return total_delta


def to_set(*ranges):
    res = set()
    for rng in ranges:
        for r in ranges:
            res.add(r)
    return res


II_ENDINGS = to_set(range(1, 5), range(21, 25), range(31, 35), range(41, 45), range(51, 55))


def format_time_delta(total_seconds):
    hours = total_seconds // 3600
    # todo fix, it could be minutes=61. todo round
    minutes = round((total_seconds % 3600) / 60)

    # todo mb nltk can do it
    if hours == 0:
        str_hours = None
    elif hours == 1:
        str_hours = '1 час'
    elif hours < 5:
        str_hours = str(hours) + ' часа'
    else:
        # todo fix endings for the words, mb there are some library for this?
        str_hours = str(hours) + ' часов'

    if minutes == 0:
        str_minutes = None
    elif minutes in II_ENDINGS:
        str_minutes = str(minutes) + ' минуты'
    else:
        str_minutes = str(minutes) + ' минут'

    return ', '.join(tok for tok in (str_hours, str_minutes) if tok is not None)


def across_recognizer(text, now_time):
    if text.startswith(PREP_RELATIVE):
        prepared_text = text[len(PREP_RELATIVE):]
    else:
        prepared_text = text

    tokens = prepared_text.strip().split()
    wanted_time = now_time + parse_time_delta(tokens)
    return wanted_time


def parse_time(text, now_time):
    assert ':' in text
    tokens = text.split()
    # todo support phrases like "завтра в 18:30"
    for tok in tokens:
        if ':' in tok:
            hours_minutes = tok.split(':')
            if len(hours_minutes) > 2:
                return None
            hour = parse_int(hours_minutes[0], 0)
            minute = 0 if len(hours_minutes) < 2 else parse_int(hours_minutes[1], 0)
            time = datetime.time(hour=hour, minute=minute)
            today = now_time.date()
            wanted_time = datetime.datetime.combine(today, time)
            if wanted_time <= now_time:
                wanted_time += datetime.timedelta(days=1)
            return wanted_time


def format_time(event_time):
    return time.strftime("%H:%M:%S %d.%m.%y", time.gmtime(event_time))



class TimeService:
    def __init__(self):
        # self.queue = Queue.PriorityQueue()
        pass

    # todo this isn't a class
    def define_time(self):
        answer = yield BotMsg(text='Какое время?', buttons=TIME_BUTTONS)
        text = answer.text
        if text is None:
            return None
        now_time = now()
        if text.startswith(PREP_RELATIVE):
            time = across_recognizer(text, now_time)
        elif ':' in text:
            time = parse_time(text, now_time)
        else:
            time = across_recognizer(text, now_time)
        # todo remove microseconds
        return time

        # def add_remind_task(self, user, event):
        #     self.queue.put(RemindTask(user=user, event=event))
