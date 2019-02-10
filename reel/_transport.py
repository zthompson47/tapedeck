"""Transport class."""
import logging

import trio

LOG = logging.getLogger(__name__)


class Transport(trio.abc.AsyncResource):
    """A device for running spools."""

    def __init__(self, *args):
        """Create a transport chain from a list of spools."""
        self._nursery = None
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

    @property
    def stdin(self):
        """Return stdin of the first spool in the chain."""
        return self._chain[0].proc.stdin

    @property
    def stdout(self):
        """Return stdout of the last spool in the chain."""
        return self._chain[-1].proc.stdout

    def _append(self, spool):
        """Add a spool to this transport chain."""
        self._chain.append(spool)

    async def _handle_stdin(self, message):
        """Send a message to stdin."""
        async with self.stdin as stdin:
            try:
                await stdin.send_all(message)
            except trio.BrokenResourceError as err:
                LOG.exception(err)

    async def _run(self, message=None, stdout=False):
        """Connect the spools with pipes and let the bytes flow."""
        output = None
        async with trio.open_nursery() as nursery:

            # Chain the spools with pipes.
            for idx, spool in enumerate(self._chain):
                spool.start_process(nursery)
                if idx < len(self._chain) - 1:
                    _src = spool
                    _dst = self._chain[idx + 1]
                    send_ch, receive_ch = trio.open_memory_channel(0)
                    async with send_ch, receive_ch:
                        nursery.start_soon(_src.send, send_ch.clone())
                        nursery.start_soon(_dst.receive, receive_ch.clone())

            # Queue the message to stdin.
            if message:
                nursery.start_soon(self._handle_stdin, message)

            # Read stdout from the last spool in the list.
            if stdout:
                output = b''
            ch_send, ch_receive = trio.open_memory_channel(0)
            nursery.start_soon(self._chain[-1].send, ch_send)
            async for chunk in ch_receive:
                if stdout:
                    output += chunk

        # Close the subprocesses.
        for spool in self._chain:
            await spool.aclose()

        if stdout:
            return output

    def start_daemon(self, nursery):
        """Run this transport in the background and return."""
        nursery.start_soon(self._run)

    async def stop(self):
        """Stop this transport."""
        LOG.debug('{}{}{}{}{}{}{}{}{}{}{}{} Transport.stop!!!!!!!!!!!!!')
        for spool in self._chain:
            LOG.debug('>>> %s %s', type(spool), spool)
            # if isinstance(spool, reel._spool.Spool):
            await spool.proc.stdin.aclose()
            await spool.proc.stdout.aclose()
            await spool.proc.stderr.aclose()
            spool.proc.kill()

    async def play(self) -> None:
        """Run this transport and ignore stdout."""
        await self._run()

    async def read(self, message=None, text=True):
        """Run transport and return stdout as str."""
        if message and text:
            message = message.encode('utf-8')

        rawbytes = await self._run(message=message, stdout=True)

        if text:
            decoded = rawbytes.decode('utf-8')

            # Remove trailing \n.
            if decoded[-1:] == '\n':
                decoded = decoded[:-1]
            return decoded
        return rawbytes

    async def readlines(self):
        """Run this transport and return stdout as a `list`."""
        output = (await self._run(stdout=True)).decode('utf-8')
        return output.split('\n')[:-1]
