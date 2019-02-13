"""Transport class."""
import abc

import logging

import trio

LOG = logging.getLogger(__name__)


class Streamer(metaclass=abc.ABCMeta):
    """Something that can stream i/o in a transport."""

    @abc.abstractmethod
    def start_process(self, nursery, stdin=None):
        """Start whatever this thing needs to run.

        Called before send or receive.

        """

    @abc.abstractmethod
    async def send(self, channel):
        """Send data to the channel and close both sides."""

    @abc.abstractmethod
    def receive(self, channel):
        """Receive data from the channel and leave connections open."""


class Transport(trio.abc.AsyncResource):
    """A device for running spools."""

    def __init__(self, *args):
        """Create a transport chain from a list of spools."""
        self._nursery = None
        self._output = None
        if len(args) == 1 and isinstance(args[0], list):
            self._chain = []
            for spool in args[0]:
                self._chain.append(spool)
        else:
            self._chain = list(args)

    def __repr__(self):
        """Represent prettily."""
        return str(self._chain)

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
        async with trio.open_nursery() as nursery:

            # Chain the spools with pipes.
            for idx, spool in enumerate(self._chain):
                if idx == 0:
                    spool.start_process(nursery, message)
                else:
                    spool.start_process(nursery)
                if idx < len(self._chain) - 1:
                    _src = spool
                    _dst = self._chain[idx + 1]
                    send_ch, receive_ch = trio.open_memory_channel(0)
                    async with send_ch, receive_ch:
                        nursery.start_soon(_src.send, send_ch.clone())
                        nursery.start_soon(_dst.receive, receive_ch.clone())

            # Read stdout from the last spool in the list.
            ch_send, ch_receive = trio.open_memory_channel(0)
            nursery.start_soon(self._chain[-1].send, ch_send)
            async for chunk in ch_receive:
                if not self._output:
                    self._output = b''
                self._output += chunk

        return self._output

    def start_daemon(self, nursery):
        """Run this transport in the background and return."""
        nursery.start_soon(self._run)

    async def stop(self):
        """Stop this transport."""
        for spool in self._chain:
            spool.proc.kill()
            await spool.proc.wait()
            # await spool.proc.aclose()  # HANGS

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
        output = (await self._run()).decode('utf-8')
        return output.split('\n')[:-1]
