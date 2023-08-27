import socket
import json
import struct
import threading
import signal
import atexit
import logging
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, jsonify

app = Flask(__name__)

# Configuration
hostip = '192.168.1.3'
grpaddr = '239.1.2.3'
port = 5001
max_workers = 10  # Number of threads in the thread pool

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
shutdown_event = threading.Event()

def setup_socket():
    try:
        channel = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP, fileno=None)
        channel.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        channel.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        channel.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(hostip))
        channel.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
        channel.bind(('', port))
        mreq = struct.pack("=4s4s", socket.inet_aton(grpaddr), socket.inet_aton(hostip))
        channel.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        return channel
    except Exception as e:
        logger.error(f"Error setting up socket: {e}")
        raise SystemExit(1)

# Thread pool for handling requests
thread_pool = ThreadPoolExecutor(max_workers=max_workers)


def send_and_receive(channel):
    try:  
        mcgrp = (grpaddr, port)
        msg = {'type': 'message', 'message': 'message from' + hostip, 'status': 'success'}
        encoded = json.dumps(msg).encode('utf-8')
        channel.sendto(encoded, mcgrp)

    except Exception as e:
        logger.error(f"Error in sending: {e}")

def receive_messages(channel):
    try:
        while not shutdown_event.is_set():
            buf, senderaddr = channel.recvfrom(1024)
            received_msg = json.loads(buf)
            logger.info(f"Received message from {senderaddr}: {received_msg}")

    except Exception as e:
        logger.error(f"Error in receiving: {e}")

def shutdown(channel):
    global shutdown_event
    print("Shutting down...")
    channel.close()
    shutdown_event.set()

@app.route('/health', methods=["GET"])
def health():
    return jsonify(message="OK"), 200

@app.route('/send', methods=['GET'])
def send():
    thread_pool.submit(send_and_receive, channel)
    return jsonify(message="OK"), 200

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)  # Reset Ctrl+C handling to default
    
    channel = setup_socket()
    
    thread_pool = ThreadPoolExecutor(max_workers=max_workers)
    
    message_thread = threading.Thread(target=receive_messages, args=(channel,))
    message_thread.daemon = True
    message_thread.start()
    
    atexit.register(shutdown, channel)
    
    app.run(host='0.0.0.0', port=5000)