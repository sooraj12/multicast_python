import socket
import json
import struct

hostip = '192.168.1.4'
grpaddr = '239.1.2.3'
port = 5001
msg = {'message': 'message from sender', 'status': 'success'}

sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP, fileno=None)

def send_and_receive():
   
    mcgrp = (grpaddr, port)

    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(hostip))

    print(f'sending {msg}')
    encoded = json.dumps(msg).encode('utf-8')
    sock.sendto(encoded, mcgrp)


    data, server = sock.recvfrom(16)
    print(f'received {data.decode()} from {server}')
    # sock.close()

def receive_messages():

    bindaddr = ('', port)
    sock.bind(bindaddr)

    mreq = struct.pack("=4s4s", socket.inet_aton(grpaddr), socket.inet_aton(hostip))
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    while True:
        buf, senderaddr = sock.recvfrom(1024)
        msg = json.loads(buf)

        print(f'received from {senderaddr}, message {msg}')

        sock.sendto('ack'.encode(), senderaddr)
