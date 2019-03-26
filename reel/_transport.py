"""Transport class."""
import logging

import trio

LOG = logging.getLogger(__name__)


class Transport(trio.abc.AsyncResource):
    """A device for running spools."""

    def __init__(self, *args):
        """Create a transport chain from a list of spools."""
        self._cancel_scope = None
        self._is_done = trio.Event()
        self._nursery = None
        self._output = None
        if len(args) == 1 and isinstance(args[0], list):
            self._chain = []
            for spool in args[0]:
                self._chain.append(spool)
        else:
            self._chain = list(args)
        LOG.debug(self.__repr__())

    def __gt__(self, nursery):
        """Set the nursery to use in the context manager."""
        self._nursery = nursery
        return self

    def __or__(self, next_one):
        """Store all the chained spools and reels in this transport."""
        self._chain.append(next_one)
        return self

    def __rshift__(self, next_one):
        """Store all the chained spools and reels in this transport."""
        self._chain.append(next_one)
        return self

    async def aclose(self):
        """Clean up resources."""
        for streamer in self._chain:
            await streamer.aclose()

    def __str__(self):
        """Print prettily."""
        return self.__repr__()

    def __repr__(self):
        """Represent prettily."""
        result = 'Transport([ '
        for thing in self._chain:
            result += thing.__repr__()
            result += ','
        result += ' ])'
        return result

    @property
    def is_done(self):
        """Has this thing finished playing."""
        return self._is_done.is_set()

    async def wait(self):
        """Wait until this is done."""
        await self._is_done.wait()

    async def _run(self, nursery, message=None):
        """Connect the spools with pipes and let the bytes flow."""
        for idx, spool in enumerate(self._chain):
            if idx == 0:  # Gets stdin
                spool.start(nursery, message)
            else:
                spool.start(nursery)

                # Create a pipe
                _src = self._chain[idx - 1]
                _dst = spool
                send_ch, receive_ch = trio.open_memory_channel(0)
                async with send_ch, receive_ch:
                    nursery.start_soon(
                        _src.send_to_channel, send_ch.clone()
                    )
                    nursery.start_soon(
                        _dst.receive_from_channel, receive_ch.clone()
                    )

        # Read stdout from the last spool in the list
        LOG.debug('about to read stdout of chain')
        ch_send, ch_receive = trio.open_memory_channel(0)
        nursery.start_soon(self._chain[-1].send_to_channel, ch_send)
        async for chunk in ch_receive:
            if not self._output:
                self._output = b''
            self._output += chunk

        self._is_done.set()
        if self._cancel_scope:
            self._cancel_scope.cancel()

    def spawn_in(self, nursery):
        """Start this transport and return a cancel_scope."""
        nursery.start_soon(self._run, nursery)
        self._cancel_scope = trio.CancelScope()
        return self._cancel_scope

    def start_daemon(self, nursery):
        """Run this transport in the background and return."""
        nursery.start_soon(self._run, nursery)

#    async def stop(self):
#        """Stop this transport."""
#        LOG.debug('{ stop %s }', self.__repr__())
#        for streamer in self._chain:
#            await streamer.stop()

    async def play(self) -> None:
        """Run this transport and ignore stdout."""
        async with trio.open_nursery() as nursery:
            await self._run(nursery)

    async def read(self, message=None, text=True):
        """Run transport and return stdout as str."""
        if message and text:
            message = message.encode('utf-8')

        async with trio.open_nursery() as nursery:
            await self._run(nursery, message=message)

        if text and self._output:
            decoded = self._output.decode('utf-8')

            # Remove trailing \n
            if decoded[-1:] == '\n':
                decoded = decoded[:-1]
            return decoded
        return self._output

    async def readlines(self):
        """Run this transport and return stdout as a `list`."""
        async with trio.open_nursery() as nursery:
            await self._run(nursery)
        if self._output:
            result = self._output
        else:
            result = b''
        output = result.decode('utf-8')
        return output.split('\n')[:-1]
