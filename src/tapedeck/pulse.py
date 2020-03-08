import logging

import trio

from .config import PULSE

CMD = {}


def cmd(name):
    """Fill CMD with list of commands."""

    def decorator(func):
        CMD[name] = func
        return func

    return decorator


class CliRequest:
    def __init__(self, command, *params):
        self.command = command
        self.params = params

    def send(self):
        """Generate netword data for this request."""
        if self.params:
            params = [
                param.encode("utf-8") for param in self.params
            ]
            params_str = b" " + b" ".join(params)
            command = self.command.encode("utf-8") + params_str
        else:
            command = self.command.encode("utf-8")
        return command + b"\n"


class CliResponse:
    def __init__(self, data):
        self.data = data

    def decode(self):
        return self.data


class TrioPulseProxy:
    def __init__(self, uri):
        self.uri = uri

    async def __aenter__(self):
        self.sock = await trio.open_unix_socket(self.uri)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        logging.debug(f"==>> {exc_type}\n{exc}\n{tb}")
        await self.sock.aclose()

    async def run_cmd(self, command, *params, expect_response=True):
        request = CliRequest(command, *params)
        await self.sock.send_all(request.send())
        if expect_response:
            response = CliResponse(await self.sock.receive_some(65536))
            return response.decode()
        else:
            return b""

    @cmd("list-sinks")
    async def list_sinks(self):
        return await self.run_cmd("list-sinks")

    @cmd("set-default-sink")
    async def set_default_sink(self, sink_id):
        return await self.run_cmd(
            "set-default-sink", sink_id, expect_response=False
        )
