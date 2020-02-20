import trio
from trio_websocket import open_websocket_url as _ws
from trio import open_tcp_stream as _tcp
from trio_monitor.monitor import Monitor

from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit import PromptSession, HTML

from .dispatch import Dispatch, CommandNotFound
from .config import ARIA2, MPD


async def main():
    async with trio.open_nursery() as nursery:
        async with _ws(ARIA2) as aria2, await _tcp(*MPD) as mpd:
            # Trio monitor
            mon = Monitor()
            trio.hazmat.add_instrument(mon)
            nursery.start_soon(trio.serve_tcp, mon.listen_on_stream, 8998)

            # Tapedeck command dispatcher
            td_dispatch = Dispatch(nursery, aria2, mpd)

            # Action prompt
            tab = NestedCompleter.from_nested_dict(td_dispatch.completer())
            ptk = PromptSession(
                vi_mode=True, completer=tab, complete_style=CompleteStyle.READLINE_LIKE
            )
            with patch_stdout(nursery=nursery):
                while 47 != 42:
                    try:
                        request = await ptk.prompt_async(
                            td_dispatch.ps1()
                            # completer=td_dispatch.completer()
                        )
                        await td_dispatch.route(request)
                    except CommandNotFound:
                        print("Press <TAB> for help")
                    except KeyboardInterrupt:
                        continue
                    except EOFError:
                        nursery.cancel_scope.cancel()
                        break


trio.run(main)
