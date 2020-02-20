from itertools import count

from trio_repl import TrioRepl
from trignalc import main as signal

from .aria2.proxy import CMD as aria2_cmd, Aria2Proxy
from .aria2.format import FMT as aria2_fmt
from .mpd.proxy import CMD as mpd_cmd, MPDProxy
from .redis import RedisProxy
from .etree import EtreeProxy
from .config import PS1
from .parser import parse

def pprint_etree(rss):
    result = ""
    for entry in rss["entries"]:
        result += entry["title"] + "\n"
        result += entry["links"][0]["href"] + "\n"
        result += "--\n"
    print(result)

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

    def PS1(self):
        if self.prefix == "mpd.":
            return PS1.format(prefix="mpd")
        elif self.prefix  == "aria2.":
            return PS1.format(prefix="aria2")
        else:
            return PS1.format(prefix="~")

    async def route(self, request):
        """Parse request and execute command."""
        if not request:
            raise CommandNotFound()
        program = parse(request)

        args = request.split()
        command = None
        if args:
            command = args[0]

        # Builtins
        if command == "quit":
            self.nursery.cancel_scope.cancel()
        elif command == "~":
            self.prefix = ""
        elif command == "aria2.~":
            self.prefix = "aria2."
        elif command == "mpd.~":
            self.prefix = "mpd."
        elif command == "trio":
            await TrioRepl().run(locals())
        elif command == "trignalc":
            await signal()
        elif command == "asdf.asdf":
            print("Wot?!?")

        # MPD
        elif self.prefix == "mpd."or command.startswith("mpd."):
            cmd_name = program[0][0][4:]
            args = program[0][1:]
            meth = mpd_cmd[cmd_name]
            await meth(self.mpd, *args)

        # Aria2
        elif self.prefix == "aria2."or command.startswith("aria2."):
            cmd_name = program[0][0][6:]
            args = program[0][1:]
            meth = aria2_cmd[cmd_name]
            response = await meth(self.aria2, *args)
            format = aria2_fmt.get(cmd_name, aria2_fmt["_default"])
            print(format(response))

        # RSS (Etree)
        elif command == "etree_rss":
            rss = await self.etree.rss()
            result = ""
            for entry in rss["entries"]:
                result += entry["title"] + "\n"
                result += entry["links"][0]["href"] + "\n"
                result += "--\n"
            print(result)

        else:
            raise CommandNotFound()
