import socket
import json
import struct

host_ip = '192.168.1.10'
grpaddr = '239.1.2.3'
port = 5001

receiver = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP, fileno=None)

bindaddr = ('', port)
receiver.bind(bindaddr)

mreq = struct.pack("=4s4s", socket.inet_aton(grpaddr), socket.inet_aton(host_ip))
receiver.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

def receive_message():
    while True:
        buf, senderaddr = receiver.recvfrom(1024)
        msg = json.loads(buf)

        print(f'received from {senderaddr}, message {msg}')

        receiver.sendto('ack'.encode(), senderaddr)

if __name__ == '__main__':
    receive_message()