import logging

from pymongo import MongoClient


class MongoWrapper:
    def __init__(self):
        self.logger = logging.getLogger('db')
        client = MongoClient('mongodb://localhost:27017/')
        # todo remove test_
        db = client.test_database
        # collection = db.test_collection
        self.events = db.events
        self.locations = db.locations

    def add_event(self, user, loc_name, name, time=None):
        """ now add_event expect only existing places """
        assert self.get_location(user, loc_name) is not None
        ev = {'user': user, 'name': name, 'location': loc_name}
        if time is not None:
            ev['time'] = time
        # todo remove
        self.events.insert_one(ev)
        self.logger.debug('#add_event, user: %s, event: %s', user, ev)

    def remove_event(self, user, event):
        res = self.events.delete_one(event)
        self.logger.debug('#remove_event user: %s, eid: %s', user, event)
        # todo something with res, we don't need to return it
        return res

    def get_events_by_location(self, user, loc_name):
        # todo add fuzzy search: iter across all locations, find similar
        events = list(self.events.find({'user': user, 'location': loc_name}))
        self.logger.debug('#get_events_by_location user: %s, location: %s, events cnt: %d', user, loc_name, len(events))
        return events

    def add_location(self, user, loc_name):
        # todo add check that there are still no location with this name?
        self.locations.insert_one({'user': user, 'name': loc_name})
        self.logger.debug('#add_location user: %s, loc: %s', user, loc_name)

    def get_location(self, user, loc_name):
        # todo add check that there are only one location with this name?
        # todo add fuzzy search?
        loc = self.locations.find_one({'user': user, 'name': loc_name})
        self.logger.debug('#get_location user: %s, loc: %s', user, loc_name)
        return loc

    def get_all_locations(self, user):
        locations = self.locations.find({'user': user})
        self.logger.debug('#get_all_locations user: %s, locations: %s', user, locations)
        return locations

    # todo add possibility query by last added
