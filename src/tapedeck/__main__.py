from contextlib import AsyncExitStack

import trio
import trio_websocket
from trio_monitor.monitor import Monitor

from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit import PromptSession, HTML

from .dispatch import Dispatch, CommandNotFound
from .config import ARIA2, MPD
from .completion import TapedeckCompleter

async def main():
    async with AsyncExitStack() as stack:
        # Enter context managers
        nursery = await stack.enter_async_context(trio.open_nursery())
        aria2 = await stack.enter_async_context(
            trio_websocket.open_websocket_url(ARIA2)
        )
        mpd = await stack.enter_async_context(
            await trio.open_tcp_stream(*MPD)
        )
        # Route commands
        td_cmd = Dispatch(nursery, aria2, mpd)

        # Enable debugging
        mon = Monitor()
        trio.hazmat.add_instrument(mon)
        nursery.start_soon(trio.serve_tcp, mon.listen_on_stream, 8998)

        ptk = PromptSession(
            vi_mode=True,
            complete_style=CompleteStyle.READLINE_LIKE,
            completer=TapedeckCompleter(td_cmd)
        )
        with patch_stdout(nursery=nursery):
            while 47 != 42:
                try:
                    # Prompt
                    request = await ptk.prompt_async(td_cmd.PS1())
                    await td_cmd.route(request)
                except CommandNotFound:
                    print("Press <TAB> for help")
                except KeyboardInterrupt:
                    continue
                except EOFError:
                    nursery.cancel_scope.cancel()
                    break

trio.run(main)
