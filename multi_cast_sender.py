import socket
import json
import asyncio

from flask import Flask, jsonify

hostip = '192.168.1.3'
grpaddr = '239.1.2.3'
port = 5001
msg = {'message': 'message from sender'}

app = Flask(__name__)


async def send_and_receive():
    sender = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM,
                       proto=socket.IPPROTO_UDP, fileno=None)
    
    mcgrp = (grpaddr, port)

    sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF,
                    socket.inet_aton(hostip))    

    print(f'sending {msg}')
    encoded = json.dumps(msg).encode('utf-8')
    sent = sender.sendto(encoded, mcgrp)

    loop = asyncio.get_event_loop()
    receiver_task = loop.run_in_executor(None, sender.recvfrom, 16)
    await asyncio.wait([receiver_task])

    data, server = receiver_task.result()
    print(f'received {data.decode()} from {server}')
    sender.close()

@app.route('/health', methods=["GET"])
def health():
    print('test request received')
    return jsonify(message="OK"), 200

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    send_receive_task = loop.create_task(send_and_receive())

    app.run(host='0.0.0.0', port=5000, threaded=True)