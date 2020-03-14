import logging
import math
from itertools import count
from dataclasses import dataclass

import trio
from jeepney import DBusAddress
from jeepney.auth import (
    SASLParser, make_auth_external, AuthenticationError, BEGIN
)
from jeepney.bus import get_bus
from jeepney.low_level import Parser, MessageType, HeaderFields
from jeepney.wrappers import new_method_call, ProxyBase
from jeepney.bus_messages import message_bus, MatchRule
from jeepney.routing import Router

# logging.basicConfig(filename="dbus.log", level=logging.DEBUG)
well_known_bus_name = "io.readthedocs.jeepney.aio_subscribe_example"


@dataclass
class _sigmatch:
    path: str
    interface: str
    member: str
    def __eq__(self, other):
        if self.path != other.path:
            if None not in (self.path, other.path):
                return False
        if self.interface != other.interface:
            if None not in (self.interface, other.interface):
                return False
        if self.member != other.member:
            if None not in (self.member, other.member):
                return False
        return True


class Proxy(ProxyBase):
    def __init__(self, msggen, nursery, bus="SESSION", buffsize=math.inf):
        super().__init__(msggen)
        self._serial_id = count(start=1)
        self._nursery = nursery
        self._bus = bus
        self._parser = Parser()
        self._awaiting_reply = {}
        self._signals, self.signals = trio.open_memory_channel(buffsize)
        self._subscribed_signals = []

    def __repr__(self):
        return f"Proxy({self._msggen}, {self._protocol})"

    async def __aenter__(self):
        await self._connect_and_authenticate()
        await self._send_hello()
        self._nursery.start_soon(self._router_task)

    async def __aexit__(self, *_):
        await self.sock.aclose()

    async def _connect_and_authenticate(self):
        """Connect and authenticate."""
        self.sock = await trio.open_unix_socket(get_bus(self._bus))
        await self.sock.send_all(b"\0" + make_auth_external())
        auth_parser = SASLParser()
        response = await self.sock.receive_some()
        auth_parser.feed(response)
        if not auth_parser.authenticated:
            if auth_parser.error:
                raise AuthenticationError(auth_parser.error)
            else:
                raise AuthenticationError("Unknown error")
        self._parser.feed(auth_parser.buffer)
        await self.sock.send_all(BEGIN)

    async def _send_hello(self):
        hello = new_method_call(message_bus, "Hello")
        hello.header.serial = next(self._serial_id)
        await self.sock.send_all(hello.serialise())
        hello_reply = await self.sock.receive_some()
        for msg in self._parser.feed(hello_reply):
            serial = msg.header.fields.get(
                HeaderFields.reply_serial, -1
            )
            if serial == hello.header.serial:
                self.unique_name = msg.body[0]
        
    async def _router_task(self):
        while True:
            response = await self.sock.receive_some()
            for msg in self._parser.feed(response):
                serial = msg.header.fields.get(
                    HeaderFields.reply_serial, -1
                )
                if serial in self._awaiting_reply:
                    awaiting_channel = self._awaiting_reply[serial]
                    del(self._awaiting_reply[serial])
                    await awaiting_channel.send(msg.body)
                else:
                    hdr = msg.header
                    if hdr.message_type is MessageType.signal:
                        key = _sigmatch(
                            hdr.fields.get(HeaderFields.path, None),
                            hdr.fields.get(HeaderFields.interface, None),
                            hdr.fields.get(HeaderFields.member, None)
                        )
                        if key in self._subscribed_signals:
                            # Don't block when waiting for method returns
                            if self._awaiting_reply:
                                try:
                                    self._signals.send_nowait(msg)
                                except trio.WouldBlock:
                                    # Drop signal: buffer full
                                    pass
                            else:
                                await self._signals.send(msg)
                        else:
                            # Drop signal: not subscribed
                            pass

    async def _send_message(self, msg):
        msg.header.serial = next(self._serial_id)
        set_done, wait_done = trio.open_memory_channel(0)
        self._awaiting_reply[msg.header.serial] = set_done
        serialized = msg.serialise()
        await self.sock.send_all(serialized)
        async with wait_done:
            return await wait_done.receive()

    def _method_call(self, make_msg):
        async def inner(*args, **kwargs):
            msg = make_msg(*args, **kwargs)
            assert msg.header.message_type is MessageType.method_call
            return await self._send_message(msg)
        return inner

    def subscribe_signal(self, path, interface, member):
        self._subscribed_signals.append(_sigmatch(path, interface, member))


async def main():
    async with trio.open_nursery() as nursery:
        service = Proxy(message_bus, nursery, buffsize=0)
        watcher = Proxy(message_bus, nursery, buffsize=0)
        async with service, watcher:
            match_rule = MatchRule(
                type="signal",
                sender=message_bus.bus_name,
                interface=message_bus.interface,
                member="NameOwnerChanged",
                path=message_bus.object_path,
            )
            match_rule.add_arg_condition(0, well_known_bus_name)

            watcher.subscribe_signal(
                path=message_bus.object_path,
                interface=message_bus.interface,
                #member="NameOwnerChanged"
                member=None
            )

            async def print_watcher_signals():
                async for msg in watcher.signals:
                    member = msg.header.fields[HeaderFields.member]
                    print("[watcher] match hit:", member, msg.body)

            nursery.start_soon(print_watcher_signals)

            print("[watcher] adding match rule")
            await watcher.AddMatch(match_rule)
            await trio.sleep(1)

            print("[service] calling 'RequestName'")
            resp = await service.RequestName(well_known_bus_name, 4)
            resp_map = (
                None, "primary owner", "in queue",
                "exists", "already owner",
            )
            print("[service] reply:", resp_map[resp[0]])
            await trio.sleep(1)

            nursery.cancel_scope.cancel()


if __name__ == "__main__":
    trio.run(main)
