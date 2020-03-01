from functools import partial
import logging
import asyncio

import anyio
from anyio.exceptions import ClosedResourceError
import curio
import trio

CMD = {}


def cmd(name):
    """Fill CMD with list of commands."""

    def decorator(func):
        CMD[name] = func
        return func

    return decorator


async def arun(func, *args, **kwargs):
    """Run a sync function as async."""
    return func(*args, **kwargs)


class MPDProxyBase:
    async def keepalive_task(self):
        while True:
            await self.write(b"ping\n")
            await self.sleep(3.333)

    async def listener_task(self):
        while True:
            response = await self.read()
            if response != b"OK\n":
                print("mpd", response.decode("utf-8").rstrip())

    async def runcmd(self, command, *params):
        # Encode to UTF-8 bytes
        if params:
            params = [param.encode("utf-8") for param in params]
            params_str = b" " + b" ".join(params)
            command = command.encode("utf-8") + params_str
        else:
            command = command.encode("utf-8")
        await self.write(command + b"\n")

    @cmd("add")
    async def add(self, uri):
        await self.runcmd("add", uri)

    @cmd("clear")
    async def clear(self):
        await self.runcmd("clear")

    @cmd("consume")
    async def consume(self, state):
        await self.runcmd("consume", state)

    @cmd("disableoutput")
    async def disable_output(self, output):
        await self.runcmd("disableoutput", output)

    @cmd("enableoutput")
    async def enable_output(self, output):
        await self.runcmd("enableoutput", output)

    @cmd("toggleoutput")
    async def toggle_output(self, output):
        await self.runcmd("toggleoutput", output)

    @cmd("listall")
    async def list_all(self):
        await self.runcmd("listall")

    @cmd("outputs")
    async def outputs(self):
        await self.runcmd("outputs")

    @cmd("play")  # [SONGPOS]
    async def play(self):
        await self.runcmd("play")

    @cmd("playlist")
    async def playlist(self):
        await self.runcmd("playlist")

    @cmd("shuffle")
    async def shuffle(self):
        await self.runcmd("shuffle")

    @cmd("status")
    async def status(self):
        await self.runcmd("status")

    @cmd("update")
    async def update(self):
        await self.runcmd("update")

    @cmd("clearerror")
    async def clear_error(self):
        await self.runcmd("clearerror")

    @cmd("currentsong")
    async def current_song(self):
        await self.runcmd("currentsong")

    @cmd("idle")  # [SUBSYSTEMS]
    async def idle(self):
        await self.runcmd("idle")

    @cmd("stats")
    async def stats(self):
        await self.runcmd("stats")

    @cmd("crossfade")  # {SECONDS}
    async def crossfade(self):
        await self.runcmd("crossfade")

    @cmd("mixrampdb")  # {deciBels}
    async def mix_ramp_db(self):
        await self.runcmd("mixrampdb")

    @cmd("mixrampdelay")  # {SECONDS}
    async def mix_ramp_delay(self):
        await self.runcmd("mixrampdelay")

    @cmd("random")  # {STATE}
    async def random(self):
        await self.runcmd("random")

    @cmd("repeat")  # {STATE}
    async def repeat(self):
        await self.runcmd("repeat")

    @cmd("setvol")  # {VOL}
    async def set_vol(self):
        await self.runcmd("setvol")

    @cmd("single")  # {STATE}
    async def single(self):
        await self.runcmd("single")

    @cmd("replay_gain_mode")  # {MODE}
    async def replay_gain_mode(self):
        await self.runcmd("replay_gain_mode")

    @cmd("replay_gain_status")
    async def replay_gain_status(self):
        await self.runcmd("replay_gain_status")

    @cmd("previous")
    async def previous(self):
        await self.runcmd("previous")

    @cmd("next")
    async def next(self):
        await self.runcmd("next")

    @cmd("pause")
    async def pause(self):
        await self.runcmd("pause")

    @cmd("stop")
    async def stop(self):
        await self.runcmd("stop")

    @cmd("playid")  # [SONGID]
    async def play_id(self):
        await self.runcmd("playid")

    @cmd("seek")  # {SONGPOS} {TIME}
    async def seek(self):
        await self.runcmd("seek")

    @cmd("seekid")  # {SONGPOS} {TIME}
    async def seek_id(self):
        await self.runcmd("seekid")

    @cmd("seekcur")  # {TIME}
    async def seek_cur(self):
        await self.runcmd("seekcur")

    @cmd("addid")  # {URI} [POSITION]
    async def add_id(self):
        await self.runcmd("addid")

    @cmd("delete")  # [{POS} | {START:END}]
    async def delete(self):
        await self.runcmd("delete")

    @cmd("deleteid")  # {SONGID}
    async def delete_id(self):
        await self.runcmd("deleteid")


class TrioMPDProxy(MPDProxyBase):
    def __init__(self, nursery, stream):
        self.read = partial(stream.receive_some, 65536)
        self.write = stream.send_all
        self.sleep = trio.sleep
        nursery.start_soon(self.run_tasks)

    async def run_tasks(self):
        async with trio.open_nursery() as nursery:
            nursery.start_soon(self.keepalive_task)
            nursery.start_soon(self.listener_task)


class AnyioMPDProxy(MPDProxyBase):
    def __init__(self, task_group, *uri):
        self.tg = task_group
        self.uri = uri

    async def __aenter__(self):
        self.sock = await anyio.connect_tcp(*self.uri)
        await self.tg.spawn(self.keepalive_task)
        await self.tg.spawn(self.listener_task)
        return self

    async def __aexit__(self, *args):
        await self.sock.close()

    async def keepalive_task(self):
        while True:
            try:
                await self.sock.send_all(b"ping\n")
            except OSError:
                logging.debug("mpd keepalive bad conn")
                break
            else:
                await anyio.sleep(3.333)

    async def listener_task(self):
        while True:
            try:
                response = await self.sock.receive_some(65536)
            except ClosedResourceError:
                logging.debug("mpd listener closed conn")
                break
            else:
                if response != b"OK\n":
                    print("mpd", response.decode("utf-8").rstrip())

    async def runcmd(self, command, *params):
        # Encode to UTF-8 bytes
        if params:
            params = [param.encode("utf-8") for param in params]
            params_str = b" " + b" ".join(params)
            command = command.encode("utf-8") + params_str
        else:
            command = command.encode("utf-8")
        await self.sock.send_all(command + b"\n")


class CurioMPDProxy(MPDProxyBase):
    def __init__(self, sock):
        self.read = partial(sock.recv, 65536)
        self.write = sock.sendall
        self.sleep = curio.sleep

    async def start(self):
        async def _start():
            async with curio.TaskGroup() as tg:
                await tg.spawn(self.keepalive_task)
                await tg.spawn(self.listener_task)
        await curio.spawn(_start)


class AsyncioMPDProxy(MPDProxyBase):
    def __init__(self, reader, writer):
        self.read = partial(reader.read, 65536)
        self.write = partial(arun, writer.write)
        self.sleep = asyncio.sleep
        asyncio.create_task(self.run_tasks())

    async def run_tasks(self):
        await asyncio.gather(self.keepalive_task(), self.listener_task())
