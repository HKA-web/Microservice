from core.consumers.clock import ClockConsumer
from core.consumers.progress import ProgressConsumer


def Group(label) -> str:
    return f'RESOURCE-{label}'


Created = 'CREATED'
Updated = 'UPDATED'
Deleted = 'DELETED'

__all__ = [
    ClockConsumer,
    ProgressConsumer,
    Group,
    Created,
    Updated,
    Deleted,
]
