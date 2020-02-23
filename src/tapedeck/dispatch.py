from itertools import count

from trio_repl import TrioRepl
from trignalc import main as signal

from prompt_toolkit.patch_stdout import patch_stdout

from .redis import RedisProxy

from .aria2.proxy import CMD as aria2_cmd, Aria2Proxy
from .aria2.format import FMT as aria2_fmt

from .mpd.proxy import CMD as mpd_cmd, MPDProxy

from .etree.proxy import CMD as etree_cmd, EtreeProxy
from .etree.format import FMT as etree_fmt

from .config import PS1
from .parser import parse

class CommandNotFound(Exception):
    pass

class Dispatch:
    def __init__(self, nursery, aria2_websocket, mpd_tcp_stream):
        """Start up proxy services"""
        self.namespace = ""
        self.nursery = nursery
        self.aria2 = Aria2Proxy(nursery, aria2_websocket)
        self.mpd = MPDProxy(nursery, mpd_tcp_stream)
        self.redis = RedisProxy(nursery)
        self.etree = EtreeProxy(nursery, self.redis)

    def PS1(self):
        if self.namespace == "mpd.":
            return PS1.format(namespace="mpd")
        elif self.namespace  == "aria2.":
            return PS1.format(namespace="aria2")
        elif self.namespace  == "etree.":
            return PS1.format(namespace="etree")
        else:
            return PS1.format(namespace="~")

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
            self.namespace = ""
        elif command == "aria2.~":
            self.namespace = "aria2."
        elif command == "mpd.~":
            self.namespace = "mpd."
        elif command == "etree.~":
            self.namespace = "etree."
        elif command == "trio":
            await TrioRepl().run(locals())
        elif command == "trignalc":
            await signal()

        # MPD
        elif self.namespace == "mpd."or command.startswith("mpd."):
            if command.startswith("mpd."):
                cmd_name = program[0][0][4:]
            else:
                cmd_name = program[0][0]
            args = program[0][1:]
            meth = mpd_cmd[cmd_name]
            await meth(self.mpd, *args)

        # Aria2
        elif self.namespace == "aria2."or command.startswith("aria2."):
            if command.startswith("aria2."):
                cmd_name = program[0][0][6:]
            else:
                cmd_name = program[0][0]
            args = program[0][1:]
            meth = aria2_cmd[cmd_name]
            response = await meth(self.aria2, *args)
            format = aria2_fmt.get(cmd_name, aria2_fmt["_default"])
            with patch_stdout(nursery=self.nursery):
                print("-------->>>>>>>!!!!!!!!!!!!!!", flush=True)
                print(format(response), flush=True)

        # RSS (Etree)
        elif self.namespace == "etree."or command.startswith("etree."):
            if command.startswith("etree."):
                cmd_name = program[0][0][6:]
            else:
                cmd_name = program[0][0]
            args = program[0][1:]
            meth = etree_cmd[cmd_name]
            response = await meth(self.etree, *args)
            format = etree_fmt.get(cmd_name, etree_fmt["_default"])
            with patch_stdout(nursery=self.nursery):
                print(format(response))

        else:
            raise CommandNotFound()
