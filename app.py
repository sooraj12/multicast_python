import socket
import json
import struct
from flask import Flask, jsonify
import threading
import signal
import atexit

# Global variables
shutdown_event = threading.Event()
hostip = '192.168.1.4'
grpaddr = '239.1.2.3'
port = 5001
msg = {'type': 'message', 'message': 'message from windows', 'status': 'success'}
ack = {'type': 'ack', 'res': 'acknowledge from windows'}

channel = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM,
                       proto=socket.IPPROTO_UDP, fileno=None)

def send_and_receive():
    try:
      
        mcgrp = (grpaddr, port)

        channel.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        channel.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(hostip))

        encoded = json.dumps(msg).encode('utf-8')
        channel.sendto(encoded, mcgrp)
    except Exception as e:
        print(f"Error in sending: {e}")

def receive_messages():
    try:
      
        bindaddr = ('', port)
        channel.bind(bindaddr)

        mreq = struct.pack("=4s4s", socket.inet_aton(grpaddr), socket.inet_aton(hostip))
        channel.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        while not shutdown_event.is_set():
            buf, senderaddr = channel.recvfrom(1024)

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
