import logging
import time

from pymongo import MongoClient


# to_do add fuzzy search?
# to_do I heard thought about using cassanrda (fuzzy text search)
class MongoWrapper:
    def __init__(self):
        self.logger = logging.getLogger('db')
        client = MongoClient('mongodb://localhost:27017/')
        # to_do remove test_ after reviewing
        db = client.test_database
        # collection = db.test_collection
        self.events = db.events
        self.places = db.places
        # self.reminders = db.reminders
        self.current_places = db.current_places

    def add_event(self, user, place_name, name, event_time=None):
        """ now add_event expect only existing places """
        # todo improve assertions
        # assert self.get_place(user, place_name) is not None
        ev = {'user': user, 'name': name, 'place': place_name}
        if event_time is not None:
            # todo is it ok way to get time?
            ev['time'] = int(event_time.timestamp())
            ev['done'] = False
        self.events.insert_one(ev)
        # if event_time is not None:
        #     if current_milli_time() < time_millis:
        #         self.reminders.insert_one({'user': user, 'event_id': ev.get('_id'), 'time_millis': time_millis})
        self.logger.debug('#add_event, user: %s, event: %s', user, ev)

    def remove_event(self, user, event):
        res = self.events.delete_one(event)
        self.logger.debug('#remove_event user: %s, eid: %s', user, event)
        # todo smth with res, we can show "event ... was removed"
        return res

    def get_events_by_place(self, user, place_name):
        events = list(self.events.find({'user': user, 'place': place_name}))
        self.logger.debug('#get_events_by_place user: %s, place: %s, events cnt: %d', user, place_name, len(events))
        return events

    def get_all_events(self, user):
        events = list(self.events.find({'user': user}))
        self.logger.debug('#get_events_by_place user: %s, events cnt: %d', user, len(events))
        return events

    def add_place(self, user, place_name):
        # todo add check that there are still no place with this name?
        self.places.insert_one({'user': user, 'name': place_name})
        self.logger.debug('#add_place user: %s, place: %s', user, place_name)

    def get_place(self, user, place_name):
        # todo add check that there are only one place with this name?
        place = self.places.find_one({'user': user, 'name': place_name})
        self.logger.debug('#get_place user: %s, place: %s', user, place_name)
        return place

    def get_all_places(self, user):
        places = self.places.find({'user': user})
        self.logger.debug('#get_all_places user: %s, places: %s', user, places)
        return places

    # todo fix memory!!!!!!
    def update_current_place(self, user, place_name):
        assert self.get_place(user, place_name) is not None
        self.current_places.update({'user': user}, {'$set': {'place': place_name}}, upsert=True)
        # todo add possibility query by last added ?

    # todo wrap entries from db?
    def get_current_places(self):
        return self.current_places.find({})

    def get_current_place(self, user):
        return self.current_places.find_one({'user': user})

    def rename_place(self, user, old_place_name, new_place_name):
        assert self.get_place(user, old_place_name) is not None
        # todo@1 fix, this is totally not a transaction(which is very bad style) and low-performance, but it should work now
        # we have id_ for the places and we need some wrappers around it for the main.py
        # todo remove 'print'
        self.events.update({'user': user, 'place': old_place_name}, {'$set': {'place': new_place_name}})
        self.places.update({'user': user, 'name': old_place_name}, {'$set': {'name': new_place_name}})

    def update_location_for_place(self, user, place_name, str_location_for_db):
        assert self.get_place(user, place_name) is not None
        self.logger.debug('#update_location_for_place user: %s, place: %s, location: %s', user, place_name,
                          str_location_for_db)
        self.places.update_one({'user': user, 'name': place_name}, {'$set': {'location': str_location_for_db}})

    # todo use little table self.reminders
    def check_tasks(self, now):
        def done_callback(ev):
            ev['done'] = True
            self.events.save(ev)

        # todo check it manually
        query = {'time': {'$lt': now}, 'done': False}
        if self.logger.isEnabledFor(logging.DEBUG):
            count = self.events.find(query).count()
            if count > 0:
                print('#check_tasks count:', count)
        # todo fix, this is strange logic
        return self.events.find(query), done_callback
