import json
import uuid


class RaceHandler:
    """
    Standard race handler.

    You should use this class as a basis for creating your own handler that
    can consume incoming messages, react to race data changes, and send stuff
    back to the race room.
    """
    # This is used by `should_stop` to determine when the handler should quit.
    stop_at = ['cancelled', 'finished']

    def __init__(self, logger, conn, state, command_prefix='!'):
        """
        Base handler constructor.

        Sets up the following attributes:
        * conn - WebSocket connection, used internally.
        * data - Race data dict, as retrieved from race detail API endpoint.
        * logger - The logger instance bot was instantiated with.
        * state - A dict of stateful data for this race
        * ws - The open WebSocket, used internally.

        About data vs state - data is the race information retrieved from the
        server and can be read by your handler, but should not be written to.
        The state on the other hand can be used by your handler to preserve
        information about the race. It is preserved even if the handler is
        recreated (e.g. due to disconnect). Use it for any information you
        want.
        """
        self.conn = conn
        self.data = {}
        self.logger = logger
        self.state = state
        self.command_prefix = command_prefix
        self.ws = None

    def should_stop(self):
        """
        Determine if the handler should be terminated. This is checked after
        every receieved message.

        By default, checks if the race state matches one of the values in
        `stop_at`.
        """
        return self.data.get('status', {}).get('value') in self.stop_at

    async def begin(self):
        """
        Bot actions to perform when first connecting to a race room.

        Override this method to add an intro for when your bot first appears.
        """
        pass

    async def consume(self, data):
        """
        Standard message consumer. This is called for every message we receive
        from the site.

        This implementation will attempt to find an appropriate method to call
        to handle the incoming data, based on its type. For example if we have
        a "race.data" type message, it will call `self.race_data(data)`.
        """
        msg_type = data.get('type')

        self.logger.info('[%(race)s] Recieved %(msg_type)s' % {
            'race': self.data.get('name'),
            'msg_type': msg_type,
        })

        method = msg_type.replace('.', '_')
        if msg_type and hasattr(self, method):
            await getattr(self, method)(data)
        else:
            self.logger.info(f'No handler for {msg_type}, ignoring.')

    async def end(self):
        """
        Bot actions to perform just before disconnecting from a race room.

        Override this method to add an outro for when your bot leaves.
        """
        pass

    async def error(self, data):
        """
        Consume an incoming "error" type message.

        By default, just raises the message as an exception.
        """
        raise Exception(data.get('errors'))

    async def chat_message(self, data):
        """
        Consume an incoming "chat.message" type message.

        This method assumes a standard bot operation. It checks the first word
        in the message, and if it looks like an exclaimation command like
        "!seed", then it will call the relevant method, i.e.
        `self.ex_seed(args, message)` (where `args` is the remainder of the
        message split up by words, and message is the original message blob).
        """
        message = data.get('message', {})

        if message.get('is_bot') or message.get('is_system'):
            self.logger.info('Ignoring bot/system message.')
            return

        words = message.get('message', '').lower().split(' ')
        if words and words[0].startswith(self.command_prefix.lower()):
            method = 'ex_' + words[0][len(self.command_prefix):]
            args = words[1:]
            if hasattr(self, method):
                self.logger.info('[%(race)s] Calling handler for %(word)s' % {
                    'race': self.data.get('name'),
                    'word': words[0],
                })
                await getattr(self, method)(args, message)

    async def race_data(self, data):
        """
        Consume an incoming "race.data" message.

        By default just updates the `data` attribute on the object. If you
        want to react to race changes, you can override this method to add
        further functionality.
        """
        self.data = data.get('race')

    async def send_message(self, message):
        """
        Send a chat message to the race room.

        `message` should be the message string you want to send.
        """
        await self.ws.send(json.dumps({
            'action': 'message',
            'data': {
                'message': message,
                'guid': str(uuid.uuid4()),
            }
        }))
        self.logger.info('[%(race)s] Message: "%(message)s"' % {
            'race': self.data.get('name'),
            'message': message,
        })

    async def set_raceinfo(self, info, overwrite=False, prefix=True):
        """
        Set the `info` field on the race room's data.

        `info` should be the information you wish to set. By default, this
        method will prefix your information with the existing info, if needed.
        You can change this to suffix with `prefix=False`, or disable this
        behaviour entirely with `overwrite=True`.
        """
        if self.data.get('info') and not overwrite:
            if prefix:
                info = info + ' | ' + self.data.get('info')
            else:
                info = self.data.get('info') + ' | ' + info

        await self.ws.send(json.dumps({
            'action': 'setinfo',
            'data': {'info': info}
        }))
        self.logger.info('[%(race)s] Set info: "%(info)s"' % {
            'race': self.data.get('name'),
            'info': info,
        })

    async def handle(self):
        """
        Low-level handler for the race room. This will loop over the websocket,
        processing any messages that come in.
        """
        self.logger.info('[%(race)s] Handler started' % {
            'race': self.data.get('name'),
        })
        async with self.conn as ws:
            self.ws = ws
            await self.begin()
            async for message in self.ws:
                data = json.loads(message)
                await self.consume(data)
                if self.should_stop():
                    await self.end()
                    break
