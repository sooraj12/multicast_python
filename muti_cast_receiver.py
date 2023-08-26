import socket
import struct
import json
import asyncio

from flask import Flask, jsonify

fromip = '192.168.1.4'
grpaddr = '239.1.2.3'
port = 5001

app = Flask(__name__)

receiver = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP, fileno=None)

bindaddr = ('', port)
receiver.bind(bindaddr)


mreq = struct.pack("=4s4s", socket.inet_aton(grpaddr), socket.inet_aton(fromip))
receiver.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)


async def receive_messages():
    while True:
        buf, senderaddr = await asyncio.to_thread(receiver.recvfrom, 1024)
        msg = json.loads(buf)

        print(f'received from {senderaddr}, message {msg}')

        await asyncio.to_thread(receiver.sendto, 'ack'.encode(), senderaddr)

@app.route('/health' , methods = ["GET"])
def health():
    print('test request received')
    return jsonify(message="OK"), 200


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    receive_task = loop.create_task(receive_messages())

    app.run(host='0.0.0.0', port=5000)


