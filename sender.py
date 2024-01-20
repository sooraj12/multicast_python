import json
import socket

hostip = '192.168.1.10'
grpaddr = '239.1.2.3'
port = 5001
msg = {'message': 'message from sender'}

def send():
    sender = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM,
                       proto=socket.IPPROTO_UDP, fileno=None)
    
    mcgrp = (grpaddr, port)

    sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF,
                    socket.inet_aton(hostip))    

    print(f'sending {msg}')
    encoded = json.dumps(msg).encode('utf-8')
    sent = sender.sendto(encoded, mcgrp)

    sender.close()

if __name__ == "__main__":
    send()