from functools import wraps

from .bot import Bot
from .handler import RaceHandler

__all__ = [
    'Bot',
    'RaceHandler',
    'can_moderate',
    'can_monitor',
    'moderator_cmd',
    'monitor_cmd',
]


def can_moderate(message):
    """
    Determine if the user who sent the message is a moderator.

    Returns False if moderator status is indeterminate, e.g. message was sent
    by a bot instead of a user.
    """
    return message.get('user', {}).get('can_moderate', False)


def can_monitor(message):
    """
    Determine if the user who sent the message is a race monitor.

    Returns False if monitor status is indeterminate, e.g. message was sent
    by a bot instead of a user.
    """
    return message.get('is_monitor', False)


def moderator_cmd(func):
    """
    Restrict a command so it can only be used by category moderators.

    Use as a decorator in your race handler, for example:

    @moderator_cmd
    async def ex_lock(self, args, message):
        await self.send_message('...')
    """
    return _restrict_cmd(
        func,
        can_moderate,
        'Sorry %(reply_to)s, only moderators can do that.',
    )


def monitor_cmd(func):
    """
    Restrict a command so it can only be used by race monitors.

    Use as a decorator in your race handler, for example:

    @moderator_cmd
    async def ex_lock(self, args, message):
        await self.send_message('...')
    """
    return _restrict_cmd(
        func,
        can_monitor,
        'Sorry %(reply_to)s, only race monitors can do that.',
    )


def _restrict_cmd(fn, perm_fn, error_msg):
    @wraps(fn)
    async def wrap(self, args, message):
        if perm_fn(message):
            await fn(self, args, message)
        else:
            reply_to = message.get('user', {}).get('name', 'friend')
            await self.send_message(error_msg % {'reply_to': reply_to})
    return wrap
