import json
import logging

from django import template

logger = logging.getLogger(__name__)

register = template.Library()


@register.filter(name='jsondumps')
@register.simple_tag(name='jsondumps')
def dumps(value, indent=2):
    try:
        return json.dumps(value.__dicts__(), indent=indent if indent > 0 else None)
    except Exception as e:
        return json.dumps(value, indent=indent if indent > 0 else None)
