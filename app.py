import socket
import json
import struct
import threading
import signal
import atexit
import logging
import sys
import time

from concurrent.futures import ThreadPoolExecutor
from flask import Flask, jsonify

app = Flask(__name__)

# Configuration
hostip = '192.168.1.3'
grpaddr = '234.0.0.1'
port = 42100
max_workers = 10  # Number of threads in the thread pool
keep_alive_interval = 30  # Interval for sending keep-alive messages in seconds

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
shutdown_event = threading.Event()
channel_lock = threading.Lock()
channel = None

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
        channel.settimeout(0.1)

        return channel
    except Exception as e:
        logger.error(f"Error setting up socket: {e}")
        raise SystemExit(1)

def send_membership_report():
    while not shutdown_event.is_set():
        try:
            # Create a socket for sending membership reports
            report_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Send an empty UDP packet to the multicast group address and port
            report_socket.sendto(b'', (grpaddr, port))
            report_socket.close()

            logger.info("Sent membership report")

            # Wait for the next interval before sending the next report
            shutdown_event.wait(keep_alive_interval)
        except Exception as e:
            logger.error(f"Error sending membership report: {e}")


def send_keep_alive():
    # Start the thread for sending membership reports
    membership_thread = threading.Thread(target=send_membership_report)
    membership_thread.daemon = True
    membership_thread.start()

    while not shutdown_event.is_set():
        try:
            msg = {'type': 'keep_alive', 'status': 'OK'}
            encoded = json.dumps(msg).encode('utf-8')
            with channel_lock:
                channel.sendto(encoded, (grpaddr, port))
            logger.info("Sent keep-alive message")

            shutdown_event.wait(keep_alive_interval)
        except Exception as e:
            logger.error(f"Error sending keep-alive: {e}")

def send_and_receive():
    try:  
        mcgrp = (grpaddr, port)
        msg = {'type': 'message', 'message': 'message from ' + hostip, 'status': 'success'}
        encoded = json.dumps(msg).encode('utf-8')
        with channel_lock:
            channel.sendto(encoded, mcgrp)

    except Exception as e:
        logger.error(f"Error in sending: {e}")

def receive_messages():
    try:
        while not shutdown_event.is_set():
            try:
                buf, senderaddr = channel.recvfrom(1024)
                if buf:
                    received_msg = json.loads(buf)
                    logger.info(f"Received message from {senderaddr}: {received_msg}")
            except socket.error as e:
                if e.errno == 35:
                    time.sleep(0.1)  # Sleep for a short time before trying again
                    continue
                else:
                    logger.error(f"Socket error in receiving: {e}")
    except Exception as e:
        logger.error(f"Error in receiving: {e}")

def shutdown():
    with channel_lock:
        if channel:
            channel.close()
        shutdown_event.set()

@app.route('/health', methods=["GET"])
def health():
    return jsonify(message="OK"), 200

@app.route('/send', methods=['GET'])
def send():
    thread_pool.submit(send_and_receive)
    return jsonify(message="OK"), 200

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    try:
        channel = setup_socket()
    except SystemExit:
        logger.error("Exiting due to socket setup failure.")
        sys.exit(1)
    thread_pool = ThreadPoolExecutor(max_workers=max_workers)
    
    message_thread = threading.Thread(target=receive_messages)
    message_thread.daemon = True
    message_thread.start()

    keep_alive_thread = threading.Thread(target=send_keep_alive)
    keep_alive_thread.daemon = True
    keep_alive_thread.start()
    
    atexit.register(shutdown)
    
    app.run(host='0.0.0.0', port=5000)
