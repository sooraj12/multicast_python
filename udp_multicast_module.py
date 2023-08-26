import socket
import json
import struct

hostip = '192.168.1.4'
grpaddr = '239.1.2.3'
port = 5001
msg = {'type': 'message', 'message': 'message from windows', 'status': 'success'}
ack = {'type': 'ack', 'res': 'acknowledge from windows'}


def send_and_receive():
   
    sender = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP, fileno=None)
    mcgrp = (grpaddr, port)

    sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(hostip))

    print(f'sending {msg}')
    encoded = json.dumps(msg).encode('utf-8')
    sender.sendto(encoded, mcgrp)


    # data, server = sender.recvfrom(16)
    # print(f'received {json.loads(data)} from {server}')

def receive_messages():
    receiver = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP, fileno=None)
    bindaddr = ('', port)
    receiver.bind(bindaddr)

    mreq = struct.pack("=4s4s", socket.inet_aton(grpaddr), socket.inet_aton(hostip))
    receiver.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    while True:
        buf, senderaddr = receiver.recvfrom(1024)

        msg = json.loads(buf)

        print(f'received from {senderaddr}, message {msg}')

        # receiver.sendto(json.dumps(ack).encode('utf-8'), senderaddr)
