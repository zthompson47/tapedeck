import json
import functools

import feedparser
from redis import Redis

import trio
from trio_websocket import open_websocket_url as _ws
from trio import open_tcp_stream as _tcp
from trio_monitor.monitor import Monitor
from trio_repl import Wrap as TrioWrapper

from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit import PromptSession, HTML

RSS_ETREE = "http://bt.etree.org/rss/bt_etree_org.rdf"
ARIA2 = "ws://localhost:6800/jsonrpc"
MPD = ("localhost", 6600)
PS1 = HTML(
    "<blue>⦗</blue>"
    "<yellow>✇</yellow>"
    "<orange>_</orange>"
    "<yellow>✇</yellow>"
    "<blue>⦘</blue>"
    "<orange>~></orange> "
)
PS1_MPD = HTML(
    "<blue>⦗</blue>"
    "<yellow>✇</yellow>"
    "<orange>_</orange>"
    "<yellow>✇</yellow>"
    "<blue>⦘</blue>"
    "<orange>~mpd></orange> "
)
PS1_ARIA2 = HTML(
    "<blue>⦗</blue>"
    "<yellow>✇</yellow>"
    "<orange>_</orange>"
    "<yellow>✇</yellow>"
    "<blue>⦘</blue>"
    "<orange>~aria2></orange> "
)

class CommandNotFound(Exception):
    pass

class Dispatch:
    def __init__(self, nursery, aria2_websocket, mpd_tcp_stream):
        """Start up proxy services"""
        self.prefix = ""
        self.nursery = nursery
        self.aria2 = Aria2Proxy(nursery, aria2_websocket)
        self.mpd = MPDProxy(nursery, mpd_tcp_stream)
        self.redis = RedisProxy(nursery)
        self.etree = EtreeProxy(nursery, self.redis)
        self.CMD = {
            "aria2_addUri": None,
            "aria2_tellActive": None,
            "aria2_tellStatus": None,
            "etree_rss": None,
            "mpd_add": None,
            "mpd_clear": None,
            "mpd_consume": None,
            "mpd_disableoutput": None,
            "mpd_enableoutput": None,
            "mpd_listall": None,
            "mpd_outputs": None,
            "mpd_play": None,
            "mpd_playlist": None,
            "mpd_shuffle": None,
            "mpd_status": None,
            "mpd_toggleoutput": None,
            "mpd_update": None,
            "exit": None,
            "all": None,
            "aria2": None,
            "mpd": None,
            "trio": None,
        }

    def completer(self):
        #if self.prefix == "":
        #    return {_: None for _ in self.CMD.keys()}
        #else:
        result = {}
        for key in self.CMD.keys():
            if key.startswith(self.prefix):
                result[key[len(self.prefix):]] = None
        return result

    def ps1(self):
        if self.prefix == "mpd_":
            return PS1_MPD
        elif self.prefix  == "aria2_":
            return PS1_ARIA2
        else:
            return PS1

    async def route(self, request):
        """Parse request and execute command"""
        args = request.split()
        command = None
        if args:
            command = args[0]
        if command == "exit":
            self.nursery.cancel_scope.cancel()
        elif command == "all":
            self.prefix = ""
        elif command == "aria2":
            self.prefix = "aria2_"
        elif command == "mpd":
            self.prefix = "mpd_"
        elif command == "trio":
            await TrioWrapper().main()

        elif self.prefix + command == "mpd_add":
            await self.mpd.add(args[1])
        elif self.prefix + command == "mpd_clear":
            await self.mpd.clear()
        elif self.prefix + command == "mpd_consume":
            await self.mpd.consume(args[1])
        elif self.prefix + command == "mpd_disableoutput":
            await self.mpd.disableoutput(args[1])
        elif self.prefix + command == "mpd_enableoutput":
            await self.mpd.enableoutput(args[1])
        elif self.prefix + command == "mpd_listall":
            await self.mpd.listall()
        elif self.prefix + command == "mpd_outputs":
            await self.mpd.outputs()
        elif self.prefix + command == "mpd_play":
            await self.mpd.play()
        elif self.prefix + command == "mpd_playlist":
            await self.mpd.playlist()
        elif self.prefix + command == "mpd_shuffle":
            await self.mpd.shuffle()
        elif self.prefix + command == "mpd_status":
            await self.mpd.status()
        elif self.prefix + command == "mpd_toggleoutput":
            await self.mpd.toggleoutput(args[1])
        elif self.prefix + command == "mpd_update":
            await self.mpd.update()

        elif self.prefix + command == "aria2_addUri":
            await self.aria2.add_uri(args[1])
        elif self.prefix + command == "aria2_tellActive":
            await self.aria2.tell_active()
        elif self.prefix + command == "aria2_tellStatus":
            await self.aria2.tell_status(args[1])

        elif command == "etree_rss":
            await self.etree.rss()

        else:
            raise CommandNotFound()

class Aria2Proxy:
    def __init__(self, nursery, socket):
        self.nursery = nursery
        self.socket = socket
        self.nursery.start_soon(self.task_listener)

    async def task_listener(self):
        while True:
            response = await self.socket.get_message()
            print("aria2", response)

    async def add_uri(self, uri):
        await self.socket.send_message(json.dumps({
            "jsonrpc": "2.0",
            "id": "47",
            "method": "aria2.addUri",
            "params": [[uri]],
        }))

    async def tell_status(self, torrent_id):
        await self.socket.send_message(json.dumps({
            "jsonrpc": "2.0",
            "id": "42",
            "method": "aria2.tellStatus",
            "params": [torrent_id],
        }))

    async def tell_active(self):
        await self.socket.send_message(json.dumps({
            "jsonrpc": "2.0",
            "id": "48",
            "method": "aria2.tellActive",
        }))

class MPDProxy:
    def __init__(self, nursery, stream):
        self.nursery = nursery
        self.stream = stream
        nursery.start_soon(self.task_keepalive)
        nursery.start_soon(self.task_listener)

    async def task_keepalive(self):
        while True:
            await self.stream.send_all(b"ping\n")
            await trio.sleep(3.333)

    async def task_listener(self):
        while True:
            response = await self.stream.receive_some(65536)
            if response != b"OK\n":
                print("mpd", response.decode("utf-8").rstrip())

    async def add(self, filename):
        command = b"add " + filename.encode("utf-8") + b"\n"
        await self.stream.send_all(command)

    async def clear(self):
        await self.stream.send_all(b"clear\n")

    async def consume(self, state):
        command = b"consume " + state.encode("utf-8") + b"\n"
        await self.stream.send_all(command)

    async def disableoutput(self, output):
        command = b"disableoutput " + output.encode("utf-8") + b"\n"
        await self.stream.send_all(command)

    async def enableoutput(self, output):
        command = b"enableoutput " + output.encode("utf-8") + b"\n"
        await self.stream.send_all(command)

    async def toggleoutput(self, output):
        command = b"toggleoutput " + output.encode("utf-8") + b"\n"
        await self.stream.send_all(command)

    async def listall(self):
        await self.stream.send_all(b"listall\n")

    async def outputs(self):
        await self.stream.send_all(b"outputs\n")

    async def play(self):
        await self.stream.send_all(b"play\n")

    async def playlist(self):
        await self.stream.send_all(b"playlist\n")

    async def shuffle(self):
        await self.stream.send_all(b"shuffle\n")

    async def status(self):
        await self.stream.send_all(b"status\n")

    async def update(self):
        await self.stream.send_all(b"update\n")

class EtreeProxy:
    def __init__(self, nursery, redis):
        self.nursery = nursery
        self.ch_to_redis = redis.ch_to_redis
        # TODO test for fetch_rss_task started!!

    async def fetch_rss_task(self):
        ch_to_me, ch_from_redis = trio.open_memory_channel(0)
        while True:
            await trio.sleep(60 * 60)
            rss = await trio.to_thread.run_sync(
                feedparser.parse,
                RSS_ETREE,
                cancellable=True
            )
            await self.ch_to_redis.send((ch_to_me, "set", "etree.rss", rss))

    async def rss(self):
        ch_to_me, ch_from_redis = trio.open_memory_channel(0)
        await self.ch_to_redis.send((ch_to_me, "get", "etree.rss"))
        result = await ch_from_redis.receive()
        print(result)

class RedisProxy:
    def __init__(self, nursery):
        self.nursery = nursery
        self.ch_to_redis, self.ch_from_trio = trio.open_memory_channel(0)
        self.ch_to_trio, self.ch_from_redis = trio.open_memory_channel(0)
        self.nursery.start_soon(self.task_listener)
        self.nursery.start_soon(functools.partial(
            trio.to_thread.run_sync, self.task_proxy, cancellable=True
        ))

    async def task_listener(self):
        while True:
            response = await self.ch_from_redis.receive()
            print(response)

    def task_proxy(self):
        redis = Redis(host="localhost", port=6379, db=0)
        while True:
            req = trio.from_thread.run(self.ch_from_trio.receive)
            if req[1] == "set":
                rsp = redis.set(req[2], json.dumps(req[3]))
            elif req[1] == "get":
                rsp = json.loads(redis.get(req[2]))
            trio.from_thread.run(req[0].send, rsp)

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
                vi_mode=True,
                completer=tab,
                complete_style=CompleteStyle.READLINE_LIKE
            )
            with patch_stdout(nursery=nursery):
                while 47 != 42:
                    try:
                        request = await ptk.prompt_async(
                            td_dispatch.ps1()
                            #completer=td_dispatch.completer()
                        )
                        try:
                            await td_dispatch.route(request)
                        except CommandNotFound:
                            print("Press <TAB> for help")
                    except KeyboardInterrupt:
                        continue
                    except EOFError:
                        nursery.cancel_scope.cancel()
                        break


if __name__ == "__main__":
    trio.run(main)
