from pydash import py_ as lodash


def flatten_dict(data, parent='', separator='.', ):
    items = dict()
    for key, value in data.items():
        merged = f'{parent}{separator}{key}' if parent else key
        if isinstance(value, dict, ):
            items.update(flatten_dict(value, merged, separator, ))
        else:
            items.update({merged: value, }, )
    return items


setattr(lodash, 'flatten_dict', flatten_dict, )
__all__ = [
    lodash,
]
