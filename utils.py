DONE = 'готово'
DEFINE_TIME = 'определить время'
DEFINE_PLACE = 'добавить место'
CANCEL = 'отменить'
SKIP = 'пропустить'
CANCEL_ADDING_EV = 'отменить добавление события'

DEFAULT_BUTTONS = None


# todo unwind dependency main.py <-> utils.py, just use class for this stuff
def update_default_buttons(new_buttons):
    global DEFAULT_BUTTONS
    DEFAULT_BUTTONS = new_buttons


class BotMsg:
    def __init__(self, text=None, done_session=False, buttons=None):
        self.text = text
        self.done_session = done_session
        self.buttons = buttons

    def __repr__(self):
        # todo rollback, too expensive
        return 'BotMsg<text={}, btns={}, done={}>'.format(self.text.replace('\n', ' ')[:60], self.buttons,
                                                          self.done_session)

    @staticmethod
    def done_message(text=None):
        # todo fix architecture, here DEFAULT_BUTTONS should be defined
        return BotMsg(text, done_session=True, buttons=DEFAULT_BUTTONS)


def split_first(text, subtext):
    if text is None:
        return None, None
    idx = text.find(subtext)
    if idx < 0:
        return text.strip(), None
    return text[:idx].strip(), text[idx + len(subtext):].strip()


def split_last(text, subtext):
    if text is None:
        return None, None
    idx = text.rfind(subtext)
    if idx < 0:
        return text.strip(), None
    return text[:idx].strip(), text[idx + len(subtext):].strip()


def parse_int(s, val=None):
    try:
        return int(s.strip(), 10)
    except ValueError:
        return val


def parse_float(s, val=None):
    try:
        return float(s.strip())
    except ValueError:
        return val


def lmap(func, iterable):
    return list(map(func, iterable))


GEO_COORDINATES_FORMAT = '{:.6f},{:.6f}'


def format_location(location_dict):
    # example: {'latitude': 59.939095, 'longitude': 30.315868}
    return GEO_COORDINATES_FORMAT.format(location_dict['latitude'], location_dict['longitude'])


def parse_location(token):
    if token is None:
        return None
    tokens = token.split(',')
    if len(tokens) != 2:
        return None
    coords = lmap(parse_float, tokens)
    if None in coords:
        return None
    latitude, longitude = coords
    # todo extract magic numbers
    if -90 < latitude <= 90 and -180 < longitude <= 180:
        return GEO_COORDINATES_FORMAT.format(latitude, longitude)
    return '{}'
