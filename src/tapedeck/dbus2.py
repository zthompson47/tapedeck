from itertools import count

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

import logging
logging.basicConfig(filename="td.log", level=logging.DEBUG)

well_known_bus_name = "io.readthedocs.jeepney.aio_subscribe_example"
serial_id = count(1)


class Proxy(ProxyBase):
    def __init__(self, name, nursery, msggen, bus="SESSION"):
        self.name = name
        self.nursery = nursery
        super().__init__(msggen)
        self.bus = bus
        self.parser = Parser()
        #self.router = Router(None)
        self.awaiting_reply = {}

    def __repr__(self):
        return f"Proxy({self._msggen}, {self._protocol})"

    async def __aenter__(self):
        """Connect and authenticate."""
        self.sock = await trio.open_unix_socket(get_bus(self.bus))

        await self.sock.send_all(b"\0" + make_auth_external())
        auth_parser = SASLParser()
        response = await self.sock.receive_some(4096)
        auth_parser.feed(response)
        if not auth_parser.authenticated:
            if auth_parser.error:
                raise AuthenticationError(auth_parser.error)
            else:
                raise AuthenticationError("Unknown error")
        self.parser.feed(auth_parser.buffer)
        await self.sock.send_all(BEGIN)

        hello = DBusAddress(
            "/org/freedesktop/DBus",
            bus_name="org.freedesktop.DBus",
            interface="org.freedesktop.DBus",
        )
        meth = new_method_call(hello, "Hello")
        meth.header.serial = next(serial_id)
        ser = meth.serialise()
        await self.sock.send_all(ser)
        hello_reply = await self.sock.receive_some(65536)

        self.nursery.start_soon(self.listen)

    async def __aexit__(self, *_):
        await self.sock.aclose()

    async def listen(self):
        while True:
            try:
                response = await self.sock.receive_some(65536)
            except trio.ClosedResourceError:
                break
            for msg in self.parser.feed(response):
                logging.debug(f"<<{self.name}>>\"LISTEN\" msg: {msg}")
                serial = msg.header.fields.get(
                    HeaderFields.reply_serial, -1
                )
                logging.debug(f"<<{self.name}>>\"LISTEN\" serial: {serial}")
                if serial in self.awaiting_reply:
                    logging.debug(f"<<{self.name}>>\"LISTEN\" serial {serial} is awaiting...")
                    ch = self.awaiting_reply[serial]
                    del(self.awaiting_reply[serial])
                    await ch.send(msg.body)
                    logging.debug(f"<<{self.name}>>\"LISTEN\" serial {serial} awaiting SENT")
                else:

                    # Signals:
                    hdr = msg.header
                    if hdr.message_type is MessageType.signal:
                        key = (hdr.fields.get(HeaderFields.path, None),
                               hdr.fields.get(HeaderFields.interface, None),
                               hdr.fields.get(HeaderFields.member, None)
                              )
                        if key == (
                            message_bus.object_path,
                            message_bus.interface,
                            "NameOwnerChanged"
                        ):
                            print("[watcher] match hit:", msg.body)


    def _method_call(self, make_msg):
        async def inner(*args, **kwargs):
            msg = make_msg(*args, **kwargs)
            assert msg.header.message_type is MessageType.method_call
            #return self._protocol.send_message(msg)
            msg.header.serial = next(serial_id)
            set_done, wait_done = trio.open_memory_channel(0)
            self.awaiting_reply[msg.header.serial] = set_done
            #logging.debug(f"-{self.name}-> sending _method_call:")
            serialized = msg.serialise()
            logging.debug(f"<<{self.name}>>_METHOD_CALL msg: {msg}")
            #logging.debug(serialized)
            await self.sock.send_all(serialized)
            async with wait_done:
                #logging.debug(f"-{self.name}-> waiting _method_call result")
                return await wait_done.receive()
                logging.debug(f"-{self.name}-> G-0-T _method_call result")
        return inner


async def main():
    async with trio.open_nursery() as nursery:
        service = Proxy("seRVice", nursery, message_bus)
        watcher = Proxy("waTCher", nursery, message_bus)

        match_rule = MatchRule(
            type="signal",
            sender=message_bus.bus_name,
            interface=message_bus.interface,
            member="NameOwnerChanged",
            path=message_bus.object_path,
        )
        match_rule.add_arg_condition(0, well_known_bus_name)

        def print_match(match_info):
            """A demo callback triggered on successful matches."""
            print("[watcher] match hit:", match_info)

        async with service, watcher:

            print("[watcher] adding match rule")
            await watcher.AddMatch(match_rule)
            await trio.sleep(1)

            print("[service] calling 'RequestName'")
            resp = await service.RequestName(well_known_bus_name, 4)
            print(
                "[service] reply:",
                (None, "primary owner", "in queue",
                "exists", "already owned")[resp[0]]
            )
            await trio.sleep(1)


if __name__ == "__main__":
    trio.run(main)
