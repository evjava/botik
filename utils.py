def split_first(text, subtext):
    idx = text.find(subtext)
    if idx < 0:
        return text.strip(), None
    return text[:idx].strip(), text[idx + len(subtext):].strip()


def split_last(text, subtext):
    idx = text.rfind(subtext)
    if idx < 0:
        return text.strip(), None
    return text[:idx].strip(), text[idx + len(subtext):].strip()


def parse_int(s, val=None):
    try:
        return int(s.strip(), 10)
    except ValueError:
        return val
