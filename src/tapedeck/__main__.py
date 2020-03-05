import argparse
import asyncio
from contextlib import AsyncExitStack
from functools import partial

import trio
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit import PromptSession

from .dispatch import Dispatch, CommandNotFound
from .config import ARIA2, ARIA2_CURIO, MPD, PULSE
from .completion import TapedeckCompleter
from .aria2 import Aria2Proxy
from .mpd import TrioMPDProxy
from .redis import TrioRedisProxy
from .etree import TrioEtreeProxy
from .pulse import TrioPulseProxy
from .util import TrioQueue

# import logging
# logging.basicConfig(filename="td.log", level=logging.DEBUG)

async def prompt_thread(td_cmd, to_main, from_main, trio_token):
    async def _put(data):
        fut = asyncio.get_event_loop().run_in_executor(
            None,
            partial(
                trio.from_thread.run,
                to_main.send, data,
                trio_token=trio_token
            )
        )
        await asyncio.wait([fut])
        return fut.result()

    async def _get():
        fut = asyncio.get_event_loop().run_in_executor(
            None,
            partial(
                trio.from_thread.run,
                from_main.receive,
                trio_token=trio_token
            )
        )
        await asyncio.wait([fut])
        return fut.result()

    ptk = PromptSession(
        vi_mode=True,
        complete_style=CompleteStyle.READLINE_LIKE,
        completer=TapedeckCompleter(td_cmd),
    )
    while True:
        try:
            with patch_stdout():
                # Prompt loop
                request = await ptk.prompt_async(td_cmd.PS1())
                await _put(request)
                response = await _get()
                if response:
                    print(response)
        except CommandNotFound:
            print("Press <TAB> for help")
        except KeyboardInterrupt:
            continue
        except EOFError:
            await _put(None)
            break


async def run_in_prompt(td_cmd, to_thread, from_thread):
    async def _put(data):
        await to_thread.send(data)

    async def _get():
        return await from_thread.receive()

    while True:
        request = await _get()
        if request is None:
            break
        else:
            try:
                response = await td_cmd.route(request)
            except CommandNotFound:
                await _put("Press <TAB> for help")
            else:
                await _put(response)


async def main(args):
    async with AsyncExitStack() as stack:
        nursery = await stack.enter_async_context(trio.open_nursery())
        if args.monitor:
            from trio_monitor.monitor import Monitor
            mon = Monitor()
            trio.hazmat.add_instrument(mon)
            nursery.start_soon(trio.serve_tcp, mon.listen_on_stream, 8998)

        aria2_proxy = await stack.enter_async_context(
            Aria2Proxy(nursery, ARIA2)
        )
        mpd_proxy = await stack.enter_async_context(TrioMPDProxy(nursery, *MPD))
        redis_proxy = TrioRedisProxy(nursery)
        etree_proxy = TrioEtreeProxy(redis_proxy)
        pulse_proxy = await stack.enter_async_context(TrioPulseProxy(PULSE))
        td_cmd = Dispatch(
            aria2=aria2_proxy,
            mpd=mpd_proxy,
            redis=redis_proxy,
            etree=etree_proxy,
            pulse=pulse_proxy
        )

        to_thread, from_main = trio.open_memory_channel(0)
        to_main, from_thread = trio.open_memory_channel(0)

        trio_token = trio.hazmat.current_trio_token()
        nursery.start_soon(partial(
            trio.to_thread.run_sync,
            asyncio.run,
            prompt_thread(td_cmd, to_main, from_main, trio_token),
            cancellable=True
        ))

        await run_in_prompt(td_cmd, to_thread, from_thread)
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
