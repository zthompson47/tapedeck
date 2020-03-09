import os
import struct

from jeepney import DBusAddress
from jeepney.auth import SASLParser, make_auth_external, BEGIN
from jeepney.low_level import Parser
from jeepney.bus_messages import message_bus
from jeepney.integrate.blocking import _Future, Proxy
from jeepney.routing import Router
from jeepney.wrappers import new_method_call, MessageGenerator
from jeepney.bus_messages import message_bus

import trio

CHUNK = 65536
SESSION_BUS = os.environ["DBUS_SESSION_BUS_ADDRESS"].split("=")[1]
print("session bus:", SESSION_BUS)

async def main():
    auth_parser = SASLParser()
    parser = Parser()

    sock = await trio.open_unix_socket(SESSION_BUS)

    auth = b"\0" + make_auth_external()
    print("auth:", auth)
    await sock.send_all(auth)
    response = await sock.receive_some(CHUNK)
    print("response:", response)
    auth_parser.feed(response)
    if auth_parser.authenticated:
        print("authenticated!!")
        print("BEGIN:", BEGIN)
        await sock.send_all(BEGIN)
        #await sock.send_all(b"CANCEL\r\n")
        print("left in auth_parser:", auth_parser.buffer)


        hello = DBusAddress(
            "/org/freedesktop/DBus",
            bus_name="org.freedesktop.DBus",
            interface="org.freedesktop.DBus",
        )

        #meth = new_method_call(lookup, "Get", "ss",
        #    ("org.PulseAudio.ServerLookup1", "Address")
        #)
        meth = new_method_call(hello, "Hello")
        meth.header.serial = 50
        print("meth:", meth)
        ser = meth.serialise()
        print("ser:", ser)
        await sock.send_all(ser)
        print(await sock.receive_some(CHUNK))

        # Find name for lookup service
        getname = new_method_call(hello, "GetNameOwner",
            "s", ("org.PulseAudio1",)
        )
        getname.header.serial = 99
        print("getname:", getname)
        await sock.send_all(getname.serialise())
        resp = await sock.receive_some(CHUNK)
        msgs = parser.feed(resp)
        if msgs:
            for msg in msgs:
                print("==msg==>>>>", msg)
                print("==msgbody==>>>>", msg.body[0])
                bus_name = msg.body[0]

        lookup = DBusAddress(
            "/org/pulseaudio/server_lookup1",
            bus_name=bus_name,
            interface="org.freedesktop.DBus.Properties",
        )
        meth_lookup = new_method_call(lookup, "Get", "ss", (
            "org.PulseAudio.ServerLookup1", "Address"
        ))
        meth_lookup.header.serial = 51
        print("meth_lookup:", meth_lookup)
        await sock.send_all(meth_lookup.serialise())
        resp = await sock.receive_some(CHUNK)
        msgs = parser.feed(resp)
        if msgs:
            for msg in msgs:
                print("==msg==>>>>", msg)
                print("==msgbody==>>>>", msg.body[0][1])
                pulse_socket = msg.body[0][1]
        print("PULSE SOCKET:", pulse_socket)

        # Pulseaudio dbus connection
        pulse_path = pulse_socket.split("=")[1]
        sock = await trio.open_unix_socket(pulse_path)

        auth = b"\0" + make_auth_external()
        print("auth:", auth)
        await sock.send_all(auth)
        response = await sock.receive_some(CHUNK)
        print("response:", response)
        await sock.send_all(BEGIN)

        paddr = DBusAddress(
            "/org/pulseaudio/core1",
            bus_name="org.PulseAudio.Core1",
            interface="org.freedesktop.DBus.Properties"
        )
        listsinks = new_method_call(
            paddr, "Get", "ss", (
                "org.PulseAudio.Core1", "Sinks",
            )
        )
        listsinks.header.serial = 4242
        print("listsinks:", listsinks)
        await sock.send_all(listsinks.serialise())
        resp = await sock.receive_some(CHUNK)
        print("resp:", resp)
        msgs = parser.feed(resp)
        if msgs:
            for msg in msgs:
                print("==msg==>>>>", msg)
                print("==msgbody==>>>>", msg.body[0][1])
                sinks = msg.body[0][1]
        print("SINKS:", sinks)

        listen_addr = DBusAddress(
            "/org/pulseaudio/core1",
            bus_name="org.PulseAudio.Core1",
            interface="org.PulseAudio.Core1"
        )
        listen = new_method_call(
            listen_addr,
            "ListenForSignal",
            "sao",
            ("", ["/org/pulseaudio/core1"],)
        )
        listen.header.serial = 234
        await sock.send_all(listen.serialise())
        resp = await sock.receive_some(65536)
        msgs = parser.feed(resp)
        if msgs:
            for msg in msgs:
                print("==msg-->>>", msg)
        while True:
            resp = await sock.receive_some(65535)
            msgs = parser.feed(resp)
            if msgs:
                for msg in msgs:
                    print("==msg-->>>", msg)


if __name__ == "__main__":
    trio.run(main)
