import datetime
import re
from collections import defaultdict
from datetime import time
from datetime import timedelta
from itertools import count

import database
import main
import tbot
import time_service


class MockMongoWrapper(database.MongoWrapper):
    def __init__(self):
        self.events_cnt, self.places_cnt = count(), count()
        self.events, self.places = defaultdict(list), defaultdict(list)

    def add_event(self, user, place_name, name, event_time=None):
        ev_entry = {'name': name, 'place': place_name, '_id': next(self.events_cnt)}
        if event_time is not None:
            ev_entry['time'] = event_time
        self.events[user].append(ev_entry)
        return ev_entry

    def remove_event(self, user, event):
        self.events[user].remove(event)

    def get_events_by_place(self, user, place_name):
        return [e for e in self.events[user] if e['place'] == place_name]

    def add_place(self, user, place_name):
        new_place = {'_id': next(self.places_cnt), 'name': place_name}
        self.places[user].append(new_place)
        return new_place

    def get_place(self, user, place_name):
        return next(filter(lambda l: l['name'] == place_name, self.places[user]), None)

    def get_all_places(self, user):
        return self.places[user]


user_id = 1


def test_simple():
    main.db = MockMongoWrapper()

    def message(to_bot, expected_from_bot):
        user_msg = tbot.UserMsg(text=to_bot)
        bot_answer = main.chat(user_id, user_msg)
        bot_text = bot_answer.text.replace('\n', ' ')
        print('\nmessage: ', to_bot)
        print('actual   :', bot_text)
        print('expected :', expected_from_bot)
        assert len(re.findall(expected_from_bot.lower(), bot_text.lower())) > 0

    message('помощь', 'ожидаются команды')
    message('добавь поесть пельмешки, дом', 'Место <дом> не найдено. Добавить?')
    message('да', 'Событие <поесть пельмешки> добавлено для места <дом>!')
    message('добавь побатонить, дом', 'Событие <побатонить> добавлено для места <дом>!')
    message('место дом', 'события:.*поесть пельмешки.* побатонить')
    message('удали 1', 'удалить событие.*поесть пельмешки?')
    message('да', 'событие удалено')
    message('место дом', 'событие:.*побатонить')
    message('удали все', 'удалить все события?')
    message('yes', 'события удалены!')
    print('done!')


def check_time_delta(expected_time_delta, str_representation):
    tokens = str_representation.split()
    actual_delta = time_service.parse_time_delta(tokens)
    assert expected_time_delta == actual_delta, '{} != {} for {}'.format(expected_time_delta, actual_delta,
                                                                         str_representation)


def test_parse_time_delta():
    check_time_delta(timedelta(minutes=3), '3 минуты')
    check_time_delta(timedelta(minutes=5), '5 минут')
    check_time_delta(timedelta(minutes=22), '22 минуты')
    check_time_delta(timedelta(minutes=30), 'полчаса')
    check_time_delta(timedelta(hours=1), 'час')
    check_time_delta(timedelta(hours=1), '1 час')
    check_time_delta(timedelta(hours=1, minutes=30), 'полтора часа')
    check_time_delta(timedelta(hours=2), '2 часа')
    check_time_delta(timedelta(hours=10), '10 часов')
    check_time_delta(timedelta(days=1), 'день')
    check_time_delta(timedelta(days=1), '1 день')
    check_time_delta(timedelta(days=1, hours=3), '1 день 3 часа')
    check_time_delta(timedelta(days=1, hours=3), '1 день, 3 часа')
    check_time_delta(timedelta(days=1, hours=3), '1 день и 3 часа')
    print('done with', test_parse_time_delta.__name__)


def combine(some_date, some_time):
    return datetime.datetime.combine(some_date, some_time)


def check_time(now, str_representation, expected_time):
    actual_time = time_service.parse_time(str_representation, now)
    assert actual_time == expected_time, '{} != {} for {}'.format(expected_time, actual_time, str_representation)


def test_parse_time():
    today_start = datetime.date(year=2016, month=10, day=9)
    tomorrow_start = today_start + timedelta(days=1)
    now = datetime.datetime.combine(today_start, time(hour=12))

    check_time(now, '17:30', combine(today_start, time(hour=17, minute=30)))
    check_time(now, '12:01', combine(today_start, time(hour=12, minute=1)))
    check_time(now, '12:00', combine(tomorrow_start, time(hour=12, minute=0)))
    check_time(now, '11:00', combine(tomorrow_start, time(hour=11, minute=0)))
    print('done with', test_parse_time.__name__)

def test_format_time_delta():
    #todo
    pass


# test_simple()
test_parse_time_delta()
test_parse_time()
