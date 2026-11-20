from collections.abc import Mapping
from functools import lru_cache
import json


def mergedict(initial, changed, ):
    for key in set(initial.keys()).union(changed.keys()):
        if key in initial and key in changed:
            if isinstance(initial[key], dict) and isinstance(changed[key], dict):
                yield key, dict(mergedict(initial[key], changed[key]))
            else:
                yield key, changed[key]
        elif key in initial:
            yield key, initial[key]
        else:
            yield key, changed[key]


def dotdict(dictionary=None, no_list=False):
    if dictionary is None:
        dictionary = {}
    return DotDict(dictionary, separator='.', escape_character='\\', no_list=no_list)


class DotDict:
    def __init__(self, dictionary, separator='.', escape_character='\\', no_list=False):
        if not isinstance(dictionary, (Mapping, dict)):
            raise AttributeError('Dictionary must be type of dict')
        else:
            self._data = dictionary
        self.separator = separator
        self.escape_character = escape_character
        self.no_list = no_list

    def __repr__(self):
        return 'DotDict(dictionary={}, separator={!r}, escape_character={!r})'.format(self._data, self.separator, self.escape_character)

    def __str__(self):
        return str(self._data)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        try:
            return sorted(self._data.items()) == sorted(other.items())
        except AttributeError:
            return False

    def __len__(self):
        return len(self._data)

    def __getattr__(self, item):
        return getattr(self._data, item)

    def __contains__(self, item):
        def search_in(items, data):
            item = items.pop(0)
            if item.isdigit():
                indx = int(item)
                if indx < len(data):
                    if items:
                        return search_in(items, data[indx])
                    else:
                        return data[indx]
                else:
                    return False
            if items and item in data:
                return search_in(items, data[item])
            return item in data

        return search_in(self._split(item), self._data)

    @staticmethod
    def _find_data_type(item, data):
        data_types = [type(it) for it in data.keys()]
        for typee in set(data_types):
            try:
                if typee(item) in data:
                    item = typee(item)
                    return item
            except ValueError:
                pass
        return item

    @lru_cache(maxsize=32)
    def __getitem__(self, item):
        def get_from(items, data):
            itemm = items.pop(0)
            if isinstance(data, list) and itemm.isdigit() and not self.no_list:
                itemm = int(itemm)
            elif itemm not in data and isinstance(data, dict):
                itemm = self._find_data_type(itemm, data)
            elif isinstance(data, list) and ':' in itemm and not self.no_list:
                list_slice = slice(*map(lambda it: None if it in [''] else int(it), itemm.split(':')))
                if items:
                    return [get_from(items.copy(), x) for x in data[list_slice]]
                else:
                    return data[list_slice]
            try:
                data = data[itemm]
            except TypeError:
                raise KeyError('List index must be an integer, got {}'.format(itemm))
            if items and data is not None:
                return get_from(items, data)
            else:
                return data

        return get_from(self._split(item), self._data)

    def __setitem__(self, key, value):
        def set_to(items, data):
            item = items.pop(0)
            if items:
                if items[0].isdigit():
                    next_item = []
                else:
                    next_item = {}
                if item.isdigit():
                    item = int(item)
                    try:
                        if not data[item]:
                            data[item] = next_item
                    except IndexError:
                        self.set_list_index(data, item, next_item)
                    set_to(items, data[item])
                else:
                    if not data.get(item):
                        data[item] = next_item
                    set_to(items, data[item])
            else:
                if item.isdigit():
                    self.set_list_index(data, item, value)
                else:
                    data[item] = value

        set_to(self._split(key), self._data)

    @staticmethod
    def set_list_index(data, index, value):
        for _ in range(len(data), int(index) + 1):
            data.append(None)
        else:
            data[int(index)] = value

    def __delitem__(self, key):
        def delete_key(items, data):
            item = items.pop(0)
            if item.isdigit():
                item = int(item)
            if items:
                delete_key(items, data[item])
            else:
                del data[item]

        delete_key(self._split(key), self._data)

    def copy(self):
        return dotdict(self._data.copy())

    @staticmethod
    def fromkeys(seq, value=None):
        return dotdict(dict.fromkeys(seq, value))

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except (KeyError, IndexError):
            return default

    def pop(self, key, default=None):
        def pop_from(items, data):
            item = items.pop(0)
            if item not in data:
                return default
            if items:
                data = data[item]
                return pop_from(items, data)
            else:
                return data.pop(item, default)

        return pop_from(self._split(key), self._data)

    def setdefault(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            self.__setitem__(key, default)
            return default

    def to_dict(self):
        return json.loads(self.to_json())

    def to_json(self):
        return json.dumps(self._data, cls=DotDictEncoder)

    def _split(self, key):
        if not isinstance(key, str):
            return [key]
        escape_stamp = (self.escape_character + self.separator, '<#escape#>')
        skip_stamp = ('\\' + self.escape_character + self.separator, '<#skip#>' + self.separator)
        stamp_escape = ('<#escape#>', self.separator)
        stamp_skip = ('<#skip#>', self.escape_character)
        key = key.replace(*skip_stamp).replace(*escape_stamp)
        keys = key.split(self.separator)
        for index, keyy in enumerate(keys):
            keys[index] = keyy.replace(*stamp_escape).replace(*stamp_skip)
        return keys


class DotDictEncoder(json.JSONEncoder):
    def default(self, object):
        if hasattr(object, '_data'):
            return object._data
        else:
            return json.JSONEncoder.default(self, object)
