import asyncio
import json
from functools import partial

import aiohttp
import requests
import websockets

from .handler import RaceHandler


class Bot:
    """
    The racetime.gg bot class.

    This bot uses event loops to connect to multiple race rooms at once. Each
    room is assigned a handler object, which you can determine with the
    `get_handler_class`/`get_handler_kwargs` methods.

    When implementing your own bot, you will need to specify what handler you
    wish to use, as the default `RaceHandler` will not actually do anything
    other than connect to the room and log the messages.
    """
    racetime_host = 'racetime.gg'
    racetime_secure = True
    scan_races_every = 30
    reauthorize_every = 36000

    continue_on = [
        # Exception types that will not cause the bot to shut down.
        websockets.ConnectionClosed,
    ]

    def __init__(self, category_slug, client_id, client_secret, logger,
                 ssl_context=None):
        """
        Bot constructor.
        """
        self.logger = logger
        self.category_slug = category_slug
        self.ssl_context = ssl_context

        self.loop = asyncio.get_event_loop()
        self.last_scan = None
        self.handlers = {}
        self.races = {}
        self.state = {}

        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token, self.reauthorize_every = self.authorize()

    def get_handler_class(self):
        """
        Returns the handler class for races. Each race the bot finds will have
        its own handler object of this class.
        """
        return RaceHandler

    def get_handler_kwargs(self, ws_conn, state):
        """
        Returns a dict of keyword arguments to be passed into the handler class
        when instantiated.

        Override this method if you need to pass additional kwargs to your race
        handler.
        """
        return {
            'conn': ws_conn,
            'logger': self.logger,
            'state': state,
            'command_prefix': '!',
        }

    def should_handle(self, race_data):
        """
        Determine if a race we've found should be handled by this bot or not.

        Returns True if the race should have a handler created for it, False
        otherwise.
        """
        status = race_data.get('status', {}).get('value')
        return status not in self.get_handler_class().stop_at

    def authorize(self):
        """
        Get an OAuth2 token from the authentication server.
        """
        resp = requests.post(self.http_uri('/o/token'), {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials',
        })
        data = json.loads(resp.content)
        if not data.get('access_token'):
            raise Exception('Unable to retrieve access token.')
        return data.get('access_token'), data.get('expires_in', 36000)

    def create_handler(self, race_data):
        """
        Create a new WebSocket connection and set up a handler object to manage
        it.
        """
        ws_conn = websockets.connect(
            self.ws_uri(race_data.get('websocket_bot_url')),
            extra_headers={
                'Authorization': 'Bearer ' + self.access_token,
            },
            ssl=self.ssl_context,
        )

        race_name = race_data.get('name')
        if race_name not in self.state:
            self.state[race_name] = {}

        cls = self.get_handler_class()
        kwargs = self.get_handler_kwargs(ws_conn, self.state[race_name])

        handler = cls(**kwargs)

        self.logger.info(
            'Created handler for %(race)s'
            % {'race': race_data.get('name')}
        )

        return handler

    async def reauthorize(self):
        """
        Reauthorize with the token endpoint, to generate a new access token
        before the current one expires.

        This method runs in a constant loop, creating a new access token when
        needed.
        """
        while True:
            self.logger.info('Get new access token')
            self.access_token, self.reauthorize_every = self.authorize()
            delay = self.reauthorize_every
            if delay > 600:
                # Get a token a bit earlier so that we don't get caught out by
                # expiry.
                delay -= 600
            await asyncio.sleep(delay)

    async def refresh_races(self):
        """
        Retrieve current race information from the category detail API
        endpoint, retrieving the current race list. Creates a handler and task
        for any race that should be handled but currently isn't.

        This method runs in a constant loop, checking for new races every few
        seconds.
        """
        def done(task_name, *args):
            del self.handlers[task_name]

        while True:
            self.logger.info('Refresh races')
            async with aiohttp.request(
                    method='get',
                    url=self.http_uri(f'/{self.category_slug}/data')
            ) as resp:
                data = json.loads(await resp.read())
            self.races = {}
            for race in data.get('current_races', []):
                self.races[race.get('name')] = race

            for name, summary_data in self.races.items():
                if name not in self.handlers:
                    async with aiohttp.request(
                            method='get',
                            url=self.http_uri(summary_data.get('data_url'))
                    ) as resp:
                        race_data = json.loads(await resp.read())
                    if self.should_handle(race_data):
                        handler = self.create_handler(race_data)
                        self.handlers[name] = self.loop.create_task(handler.handle())
                        self.handlers[name].add_done_callback(partial(done, name))
                    else:
                        if name in self.state:
                            del self.state[name]
                        self.logger.info(
                            'Ignoring %(race)s by configuration.'
                            % {'race': race_data.get('name')}
                        )

            await asyncio.sleep(self.scan_races_every)

    def handle_exception(self, loop, context):
        """
        Handle exceptions that occur during the event loop.
        """
        self.logger.error(context)
        exception = context.get('exception')
        if exception:
            self.logger.exception(context)

        if not exception or exception.__class__ not in self.continue_on:
            loop.stop()

    def run(self):
        """
        Run the bot. Creates an event loop then iterates over it forever.
        """
        self.loop.create_task(self.reauthorize())
        self.loop.create_task(self.refresh_races())
        self.loop.set_exception_handler(self.handle_exception)
        self.loop.run_forever()

    def http_uri(self, url):
        """
        Generate a HTTP/HTTPS URI from the given URL path fragment.
        """
        return self.uri(
            proto='https' if self.racetime_secure else 'http',
            url=url,
        )

    def ws_uri(self, url):
        """
        Generate a WS/WSS URI from the given URL path fragment.
        """
        return self.uri(
            proto='wss' if self.racetime_secure else 'ws',
            url=url,
        )

    def uri(self, proto, url):
        """
        Generate a URI from the given protocol and URL path fragment.
        """
        return '%(proto)s://%(host)s%(url)s' % {
            'proto': proto,
            'host': self.racetime_host,
            'url': url,
        }
