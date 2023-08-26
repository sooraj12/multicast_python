import socket
import json
import struct
import asyncio


async def send_and_receive(hostip, grpaddr, port, msg):
    sender = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP, fileno=None)
    
    mcgrp = (grpaddr, port)

    sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(hostip))

    print(f'sending {msg}')
    encoded = json.dumps(msg).encode('utf-8')
    sent = sender.sendto(encoded, mcgrp)

    loop = asyncio.get_event_loop()
    receiver_task = loop.run_in_executor(None, sender.recvfrom, 16)
    await asyncio.wait([receiver_task])

    data, server = receiver_task.result()
    print(f'received {data.decode()} from {server}')
    sender.close()

async def receive_messages(fromip, grpaddr, port):
    receiver = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP, fileno=None)

    bindaddr = ('', port)
    receiver.bind(bindaddr)

    mreq = struct.pack("=4s4s", socket.inet_aton(grpaddr), socket.inet_aton(fromip))
    receiver.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    while True:
        buf, senderaddr = await asyncio.to_thread(receiver.recvfrom, 1024)
        msg = json.loads(buf)

        print(f'received from {senderaddr}, message {msg}')

        await asyncio.to_thread(receiver.sendto, 'ack'.encode(), senderaddr)
