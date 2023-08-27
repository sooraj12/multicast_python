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
from flask import Flask, jsonify, request
from scapy.contrib.igmp import IGMP

app = Flask(__name__)

# Configuration
hostip = '192.168.1.3'
grpaddr = '234.0.0.1'
port = 42100
max_workers = 10  # Number of threads in the thread pool
keep_alive_interval = 150  # Interval for sending keep-alive messages in seconds

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
shutdown_event = threading.Event()
channel_lock = threading.Lock()
channel = None

# Construct IGMP Membership Report packet
igmp_type = 0x11  # IGMP Membership Report

# Create an IGMP packet
igmp_packet = IGMP(type=igmp_type, gaddr=grpaddr)


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

def send_membership_report():
    while not shutdown_event.is_set():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IGMP)
            sock.bind((hostip, port)) 
            sock.sendto(bytes(igmp_packet), (grpaddr, port))
            logger.info("Sent membership report")

            # # Wait for the next interval before sending the next report
            shutdown_event.wait(keep_alive_interval)
        except Exception as e:
            logger.error(f"Error sending membership report: {e}")


def send_and_receive(msg):
    try:
        mcgrp = (grpaddr, port)
        encoded = json.dumps(msg).encode('utf-8')
        chunk_size = 256 

        for i in range(0, len(encoded), chunk_size):
            chunk = encoded[i:i + chunk_size]
            chunk_msg = {
                "chunk_id": i // chunk_size,
                "total_chunks": (len(encoded) + chunk_size - 1) // chunk_size,
                "data": chunk.decode('utf-8')
            }

            with channel_lock:
                channel.sendto(json.dumps(chunk_msg).encode('utf-8'), mcgrp)

    except Exception as e:
        logger.error(f"Error in sending: {e}")

def receive_messages():
    try:
        chunk_buffer = {} 
        while not shutdown_event.is_set():
            try:
                buf, senderaddr = channel.recvfrom(1024)
                if buf:
                    chunk_msg = json.loads(buf)
                    chunk_id = chunk_msg["chunk_id"]
                    total_chunks = chunk_msg["total_chunks"]
                    chunk_data = chunk_msg["data"]

                    chunk_buffer[chunk_id] = chunk_data

                    if len(chunk_buffer) == total_chunks:
                        complete_message = "".join(chunk_buffer[i] for i in range(total_chunks))
                        del chunk_buffer
                        logger.info(f"Received message from {senderaddr}: {complete_message}")

            except socket.error as e:
                if e.errno == 35:
                    time.sleep(0.1)
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

@app.route('/send', methods=['POST'])
def send():
    thread_pool.submit(send_and_receive, request.json)
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

    keep_alive_thread = threading.Thread(target=send_membership_report)
    keep_alive_thread.daemon = True
    keep_alive_thread.start()
    
    atexit.register(shutdown)
    
    app.run(host='0.0.0.0', port=5000)
