import argparse
import logging
logging.basicConfig(filename='/home/zach/td.log', level=logging.DEBUG)
from contextlib import AsyncExitStack
import threading
import asyncio

import websockets
import curio
import trio
import trio_websocket
from trio_monitor.monitor import Monitor

from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit import PromptSession

from .dispatch import Dispatch, CommandNotFound
from .config import ARIA2, ARIA2_CURIO, MPD
from .completion import TapedeckCompleter
from .aria2.proxy import AsyncioAria2Proxy, CurioAria2Proxy, TrioAria2Proxy
from .mpd.proxy import AsyncioMPDProxy, CurioMPDProxy, TrioMPDProxy
from .redis import AsyncioRedisProxy, CurioRedisProxy, TrioRedisProxy
from .etree.proxy import AsyncioEtreeProxy, CurioEtreeProxy, TrioEtreeProxy
from .util import TrioQueue


async def prompt_thread(td_cmd, request_queue, response_queue):
    ptk = PromptSession(
        vi_mode=True,
        complete_style=CompleteStyle.READLINE_LIKE,
        completer=TapedeckCompleter(td_cmd)
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
        if request is None:
            break
        else:
            try:
                response = await td_cmd.route(request)
            except CommandNotFound:
                await response_queue.put("Press <TAB> for help")
            else:
                await response_queue.put(response)


async def asyncio_main(request_queue, response_queue):
    async with AsyncExitStack() as stack:
        # Aria2
        aria2 = await stack.enter_async_context(
            websockets.connect(ARIA2)
        )
        aria2_proxy = AsyncioAria2Proxy(aria2)

        # MPD
        mpd_reader, mpd_writer = await asyncio.open_connection(*MPD)
        mpd_proxy = AsyncioMPDProxy(mpd_reader, mpd_writer)

        redis_proxy = AsyncioRedisProxy()
        etree_proxy = AsyncioEtreeProxy(redis_proxy)

        # Prompt
        td_cmd = Dispatch(
            aria2_proxy, mpd_proxy, redis_proxy, etree_proxy
        )

        await run_prompt(td_cmd, request_queue, response_queue)


async def curio_main(request_queue, response_queue):
    async with AsyncExitStack() as stack:
        # MPD
        mpd = await stack.enter_async_context(
            await curio.open_connection(*MPD)
        )
        mpd_proxy = CurioMPDProxy(mpd)
        await mpd_proxy.start()

        # Aria2
        aria2 = await stack.enter_async_context(
            await curio.open_connection(*ARIA2_CURIO)
        )
        aria2_proxy = CurioAria2Proxy(aria2)
        await aria2_proxy.start()

        # Redis
        redis_proxy = CurioRedisProxy()
        await redis_proxy.start()

        etree_proxy = CurioEtreeProxy(redis_proxy)

        # Prompt
        td_cmd = Dispatch(
            aria2_proxy, mpd_proxy, redis_proxy, etree_proxy
        )
        await run_prompt(td_cmd, request_queue, response_queue)


async def trio_main(request_queue, response_queue):
    async with AsyncExitStack() as stack:
        # Initialize IO resources
        aria2_websocket = await stack.enter_async_context(
            trio_websocket.open_websocket_url(ARIA2)
        )
        mpd = await stack.enter_async_context(
            await trio.open_tcp_stream(*MPD)
        )
        nursery = await stack.enter_async_context(trio.open_nursery())

        # Route commands
        aria2_proxy = TrioAria2Proxy(nursery, aria2_websocket)
        mpd_proxy = TrioMPDProxy(nursery, mpd)
        redis_proxy = TrioRedisProxy(nursery)
        etree_proxy = TrioEtreeProxy(redis_proxy)
        td_cmd = Dispatch(
            aria2_proxy, mpd_proxy, redis_proxy, etree_proxy
        )

        # Enable debugging
        mon = Monitor()
        trio.hazmat.add_instrument(mon)
        nursery.start_soon(trio.serve_tcp, mon.listen_on_stream, 8998)

        # Communicate with the prompt
        await run_prompt(td_cmd, request_queue, response_queue)

        # Shutdown
        nursery.cancel_scope.cancel()


assert __name__ == "__main__"

# Command line arguments
arrg = argparse.ArgumentParser()
arrg.add_argument(
    "-a", "--async-loop", help="asyncio, curio, trio", default="trio"
)
arrgs = arrg.parse_args()

# Run python-prompt-toolkit in a thread
td_cmd = Dispatch(None, None, None, None)  # Hack for autocomplete
request_queue = curio.UniversalQueue(withfd=True)
response_queue = curio.UniversalQueue(withfd=True)
ptk_thread = threading.Thread(
    target=asyncio.run,
    args=[prompt_thread(td_cmd, request_queue, response_queue)]
)
ptk_thread.start()

# Run main IO loop
if arrgs.async_loop == "asyncio":
    asyncio.run(asyncio_main(request_queue, response_queue))
elif arrgs.async_loop == "curio":
    curio.run(
        curio_main, request_queue, response_queue, with_monitor=True
    )
elif arrgs.async_loop == "trio":
    request_q = TrioQueue(request_queue)
    response_q = TrioQueue(response_queue)
    trio.run(trio_main, request_q, response_q)
