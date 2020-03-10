import argparse
import asyncio
from contextlib import AsyncExitStack
from functools import partial

import trio
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit import PromptSession

from .dispatch import Dispatch, CommandNotFound
from .config import ARIA2, MPD, PULSE
from .completion import TapedeckCompleter
from .aria2 import Aria2Proxy
from .mpd import TrioMPDProxy
from .redis import TrioRedisProxy
from .etree import TrioEtreeProxy
from .pulse import TrioPulseProxy
from .udev import UdevProxy
from .util import TrioToAsyncioChannel

# import logging
# logging.basicConfig(filename="td.log", level=logging.DEBUG)
# D = logging.debug


async def prompt_thread(td_cmd, channel):
    ptk = PromptSession(
        vi_mode=True,
        complete_style=CompleteStyle.READLINE_LIKE,
        completer=TapedeckCompleter(td_cmd),
    )
    while True:
        try:
            with patch_stdout():
                request = await ptk.prompt_async(td_cmd.PS1())
                await channel.send(request)
                response = await channel.receive()
                if response:
                    print(response)
        except CommandNotFound:
            print("Press <TAB> for help")
        except KeyboardInterrupt:
            continue
        except EOFError:
            await channel.send(None)
            break


async def run_in_prompt(td_cmd, channel):
    while True:
        request = await channel.receive()
        if request is None:
            break
        else:
            try:
                response = await td_cmd.route(request)
            except CommandNotFound:
                await channel.send("Press <TAB> for help")
            else:
                await channel.send(response)


async def main(args):
    async with AsyncExitStack() as stack:
        _start = stack.enter_async_context
        nursery = await _start(trio.open_nursery())
        if args.monitor:
            from trio_monitor.monitor import Monitor

            mon = Monitor()
            trio.hazmat.add_instrument(mon)
            nursery.start_soon(
                trio.serve_tcp, mon.listen_on_stream, 8998
            )

        # Gather the proxies
        aria2_proxy = await _start(Aria2Proxy(nursery, ARIA2))
        mpd_proxy = await _start(TrioMPDProxy(nursery, *MPD))
        redis_proxy = TrioRedisProxy(nursery)
        etree_proxy = TrioEtreeProxy(redis_proxy)
        pulse_proxy = await _start(TrioPulseProxy(PULSE))
        udev_proxy = await _start(UdevProxy(nursery))
        td_cmd = Dispatch(
            aria2=aria2_proxy,
            mpd=mpd_proxy,
            redis=redis_proxy,
            etree=etree_proxy,
            pulse=pulse_proxy,
        )

        # Start the prompt
        channel = TrioToAsyncioChannel()
        nursery.start_soon(
            partial(
                trio.to_thread.run_sync,
                asyncio.run,
                prompt_thread(td_cmd, channel),
                cancellable=True,
            )
        )
        await run_in_prompt(td_cmd, channel)
        nursery.cancel_scope.cancel()


def enter():
    arg = argparse.ArgumentParser()
    arg.add_argument(
        "-m", "--monitor",
        help="ncat localhost 8998",
        action="store_true"
    )
    args = arg.parse_args()
    trio.run(main, args)


if __name__ == "__main__":
    enter()
