"""Transport class."""
import logging

import trio

LOG = logging.getLogger(__name__)


class Transport(trio.abc.AsyncResource):
    """A device for running spools."""

    def __init__(self, *args):
        """Create a transport chain from a list of spools."""
        self._done_evt = None
        self._nursery = None
        self._output = None
        if len(args) == 1 and isinstance(args[0], list):
            self._chain = []
            for spool in args[0]:
                self._chain.append(spool)
        else:
            self._chain = list(args)
        LOG.debug(self.__repr__())

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

    def __or__(self, the_other_one):
        """Store all the chained spools and reels in this transport."""
        self._append(the_other_one)
        return self

    async def aclose(self):
        """Clean up resources."""
        # Not needed for tests:
        # for spool in self._chain:
        #     await spool.aclose()

    def _append(self, spool):
        """Add a spool to this transport chain."""
        self._chain.append(spool)

    async def _run(self, message=None):
        """Connect the spools with pipes and let the bytes flow."""
        LOG.debug('_run %s', self._chain)
        async with trio.open_nursery() as nursery:

            # Chain the spools with pipes.
            for idx, spool in enumerate(self._chain):
                LOG.debug('_run %d %s', idx, spool)
                if idx == 0:
                    LOG.debug('_run near aa %d %s', idx, spool)
                    spool.start(nursery, message)
                    LOG.debug('_run aft aa %d %s }', idx, spool)
                else:
                    spool.start(nursery)
                if idx < len(self._chain) - 1:
                    _src = spool
                    _dst = self._chain[idx + 1]
                    send_ch, receive_ch = trio.open_memory_channel(0)
                    async with send_ch, receive_ch:
                        nursery.start_soon(
                            _src.send_to_channel, send_ch.clone()
                        )
                        nursery.start_soon(
                            _dst.receive_from_channel, receive_ch.clone()
                        )

            # Read stdout from the last spool in the list.
            LOG.debug('about to read stdout of chain')
            ch_send, ch_receive = trio.open_memory_channel(0)
            nursery.start_soon(self._chain[-1].send_to_channel, ch_send)
            async for chunk in ch_receive:
                LOG.debug('GOT chun.....')
                LOG.debug(']}]}-->> %s', chunk)
                if not self._output:
                    self._output = b''
                self._output += chunk

            LOG.debug('about to send closed')
            if self._done_evt:
                LOG.debug('about to be done!!!!!!')
                self._done_evt.set()
            LOG.debug('about to be done part 2!!!!!!')

        LOG.debug('returning output!!!!!! %s', self._output)
        return self._output

    def start_daemon(self, nursery):
        """Run this transport in the background and return."""
        nursery.start_soon(self._run)

        # Set up an event to report done.
        self._done_evt = trio.Event()
        return self._done_evt

    async def stop(self):
        """Stop this transport."""
        LOG.debug('{ stop %s }', self.__repr__())
        for streamer in self._chain:
            await streamer.stop()

    async def play(self) -> None:
        """Run this transport and ignore stdout."""
        await self._run()

    async def read(self, message=None, text=True):
        """Run transport and return stdout as str."""
        if message and text:
            message = message.encode('utf-8')

        rawbytes = await self._run(message=message)

        if text and rawbytes:
            decoded = rawbytes.decode('utf-8')

            # Remove trailing \n.
            if decoded[-1:] == '\n':
                decoded = decoded[:-1]
            return decoded
        return rawbytes

    async def readlines(self):
        """Run this transport and return stdout as a `list`."""
        result = await self._run()
        if not result:
            result = b''
        output = result.decode('utf-8')
        return output.split('\n')[:-1]
