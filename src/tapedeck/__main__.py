import os
import argparse
import logging
from contextlib import AsyncExitStack
import threading
import asyncio

import anyio
import curio
import trio
from trio_monitor.monitor import Monitor
import sniffio

from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit import PromptSession

from .dispatch import Dispatch, CommandNotFound
from .config import ARIA2, ARIA2_CURIO, MPD, PULSE
from .completion import TapedeckCompleter
from .aria2 import AnyioAria2Proxy
from .mpd import AnyioMPDProxy
from .redis import AnyioRedisProxy
from .etree import AnyioEtreeProxy
from .pulse import PulseProxy
from .util import TrioQueue

logging.basicConfig(filename="td.log", level=logging.DEBUG)


async def prompt_thread(td_cmd, request_queue, response_queue):
    ptk = PromptSession(
        vi_mode=True,
        complete_style=CompleteStyle.READLINE_LIKE,
        completer=TapedeckCompleter(td_cmd),
    )
    while True:
        try:
            with patch_stdout():
                request = await ptk.prompt_async(td_cmd.PS1())
                await request_queue.put(request)
                print(await response_queue.get())
        except CommandNotFound:
            print("Press <TAB> for help")
        except KeyboardInterrupt:
            continue
        except EOFError:
            await request_queue.put(None)
            break


async def run_prompt(td_cmd, request_queue, response_queue):
    while True:
        request = await request_queue.get()
        logging.debug(f"got request: {request}")
        if request is None:
            logging.debug(f"?????????got request: {request} - break!!")
            break
        else:
            try:
                response = await td_cmd.route(request)
            except CommandNotFound:
                await response_queue.put("Press <TAB> for help")
            else:
                await response_queue.put(response)


async def main(request_queue, response_queue):
    async with anyio.create_task_group() as tg:
        async with AsyncExitStack() as stack:
            backend = sniffio.current_async_library()
            if backend == "trio":
                # Create special queue that works in trio
                request_queue = TrioQueue(request_queue)
                response_queue = TrioQueue(response_queue)

                # Enable debugging
                mon = Monitor()
                trio.hazmat.add_instrument(mon)
                nursery = await stack.enter_async_context(trio.open_nursery())
                nursery.start_soon(trio.serve_tcp, mon.listen_on_stream, 8998)

            aria2_proxy = await stack.enter_async_context(
                AnyioAria2Proxy(tg, ARIA2)
            )
            mpd_proxy = await stack.enter_async_context(AnyioMPDProxy(tg, *MPD))
            redis_proxy = await stack.enter_async_context(AnyioRedisProxy(tg))
            etree_proxy = AnyioEtreeProxy(redis_proxy)
            pulse_proxy = await stack.enter_async_context(PulseProxy(PULSE))
            td_cmd = Dispatch(
                aria2=aria2_proxy,
                mpd=mpd_proxy,
                redis=redis_proxy,
                etree=etree_proxy,
                pulse=pulse_proxy
            )
            await run_prompt(td_cmd, request_queue, response_queue)
            await redis_proxy.close()  # Close so curio doesn't hang on exit
            await tg.cancel_scope.cancel()


# Command line arguments
arrg = argparse.ArgumentParser()
arrg.add_argument(
    "-a", "--async-loop",
    help="asyncio, curio, trio",
    default="trio"
)
arrgs = arrg.parse_args()

# Run python-prompt-toolkit in a thread
td_cmd = Dispatch(None, None, None, None)  # Hack for autocomplete
request_queue = curio.UniversalQueue(withfd=True)
response_queue = curio.UniversalQueue(withfd=True)
ptk_coro = prompt_thread(td_cmd, request_queue, response_queue)
ptk_thread = threading.Thread(target=asyncio.run, args=[ptk_coro])
ptk_thread.start()

os.environ["CURIOMONITOR"] = "True"
anyio.run(main, request_queue, response_queue, backend=arrgs.async_loop)
