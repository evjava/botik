import re
from collections import defaultdict
from itertools import count
import main
import tbot
import database


class MockMongoWrapper(database.MongoWrapper):
    def __init__(self):
        self.events_cnt, self.locations_cnt = count(), count()
        self.events, self.locations = defaultdict(list), defaultdict(list)

    def add_event(self, user, loc_name, name, time=None):
        ev_entry = {'name': name, 'location': loc_name, '_id': next(self.events_cnt)}
        if time is not None:
            ev_entry['time'] = time
        self.events[user].append(ev_entry)
        return ev_entry

    def remove_event(self, user, event):
        self.events[user].remove(event)

    def get_events_by_location(self, user, loc_name):
        return [e for e in self.events[user] if e['location'] == loc_name]

    def add_location(self, user, loc_name):
        new_location = {'_id': next(self.locations_cnt), 'name': loc_name}
        self.locations[user].append(new_location)
        return new_location

    def get_location(self, user, loc_name):
        return next(filter(lambda l: l['name'] == loc_name, self.locations[user]), None)

    def get_all_locations(self, user):
        return self.locations[user]



user_id = 1


def simple():
    main.db = MockMongoWrapper()

    def message(to_bot, expected_from_bot):
        user_msg = tbot.UserMsg(text=to_bot)
        bot_answer = main.chat(user_id, user_msg)
        bot_text = bot_answer.text.replace('\n', ' ')
        print('\nmessage: ', to_bot)
        print('actual: ', bot_text)
        print('expected: ', expected_from_bot)
        assert len(re.findall(expected_from_bot.lower(), bot_text.lower())) > 0

    message('1', 'неизвестная команда')
    message('помощь', 'ожидаются команды')
    message('добавь поесть пельмешки, дом', 'Место не найдено. Добавить?')
    message('да', 'событие добавлено')
    message('добавь побатонить, дом', 'событие добавлено')
    message('место дом', 'события:.*поесть пельмешки.* побатонить')
    message('удали 1', 'удалить событие.*поесть пельмешки?')
    message('да', 'событие удалено')
    message('место дом', 'событие:.*побатонить')
    message('удали все', 'удалить все события?')
    message('yes', 'события удалены!')
    print('done!')

simple()
