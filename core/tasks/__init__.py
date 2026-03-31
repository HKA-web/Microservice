from core.tasks.dynamic import periodic_task, execute_task
from core.tasks.commandline import process as process_commandline
from core.tasks.icon import process_collect as process_collect_icon
from core.tasks.imports import process as process_import
from core.tasks.clock import process as process_clock
from core.tasks.autofield import process as process_setvalue

__all__ = [
    periodic_task,
    execute_task,
    process_commandline,
    process_collect_icon,
    process_import,
    process_clock,
    process_setvalue,
]
