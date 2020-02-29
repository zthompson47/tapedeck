import logging
import anyio

from .config import PULSE

CMD = {}


def cmd(name):
    """Fill CMD with list of commands."""

    def decorator(func):
        CMD[name] = func
        return func

    return decorator


class PulseProxy:
    def __init__(self, uri):
        self.uri = uri
        self.snd = anyio.create_queue(0)
        self.rcv = anyio.create_queue(0)

    async def __aenter__(self):
        self.sock = await anyio.connect_unix(self.uri)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        logging.debug(f"{exc_type}\n{exc}\n{tb}")
        await self.sock.close()

    async def run_cmd(self, command, *params):
        if params:
            params = [param.encode("utf-8") for param in params]
            params_str = b" " + b" ".join(params)
            command = command.encode("utf-8") + params_str
        else:
            command = command.encode("utf-8")
        await self.sock.send_all(command + b"\n")
        return await self.sock.receive_some(65536)

    @cmd("list-sinks")
    async def list_sinks(self):
        return await self.run_cmd("list-sinks")
