import socket
import json
import struct
from flask import Flask, jsonify
import threading
import signal
import atexit
import sys

# Global variables
shutdown_event = threading.Event()
hostip = '192.168.1.4'
grpaddr = '239.1.2.3'
port = 5001
msg = {'type': 'message', 'message': 'message from windows', 'status': 'success'}
ack = {'type': 'ack', 'res': 'acknowledge from windows'}

def send_and_receive():
    try:
        sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        mcgrp = (grpaddr, port)

        sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(hostip))

        encoded = json.dumps(msg).encode('utf-8')
        sender.sendto(encoded, mcgrp)
    except Exception as e:
        print(f"Error in sending: {e}")

def receive_messages():
    try:
        receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        bindaddr = ('', port)
        receiver.bind(bindaddr)

        mreq = struct.pack("=4s4s", socket.inet_aton(grpaddr), socket.inet_aton(hostip))
        receiver.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        while not shutdown_event.is_set():
            buf, senderaddr = receiver.recvfrom(1024)

            msg = json.loads(buf)

            print(f'received from {senderaddr}, message {msg}')
    except Exception as e:
        print(f"Error in receiving: {e}")

def shutdown():
    global shutdown_event
    print("Shutting down...")
    shutdown_event.set()

app = Flask(__name__)

@app.route('/health', methods=["GET"])
def health():
    return jsonify(message="OK"), 200

@app.route('/send', methods=['GET'])
def send():
    send_thread = threading.Thread(target=send_and_receive)
    send_thread.daemon = True
    send_thread.start()
    return jsonify(message="OK"), 200

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)  # Reset Ctrl+C handling to default

    message_thread = threading.Thread(target=receive_messages)
    message_thread.daemon = True
    message_thread.start()

    atexit.register(shutdown)  # Register the shutdown function with atexit

    app.run(host='0.0.0.0', port=5000)
