import socket
import json
import struct
from flask import Flask, jsonify
import threading
import signal
import atexit
import time

# Global variables
shutdown_event = threading.Event()
hostip = '192.168.1.4'
grpaddr = '239.1.2.3'
port = 5001
msg = {'type': 'message', 'message': 'message from windows', 'status': 'success'}
ack = {'type': 'ack', 'res': 'acknowledge from windows'}
# Maintain a dictionary to store sent messages awaiting acknowledgment
sent_messages = {}
# Use a lock for thread-safe access to sent_messages dictionary
sent_messages_lock = threading.Lock()

current_sequence_number = 0
channel = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP, fileno=None)

def send_and_receive():
    global current_sequence_number
    try:
      
        mcgrp = (grpaddr, port)

        # Increment sequence number for each message
        current_sequence_number += 1
        msg['sequence_number'] = current_sequence_number

        channel.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        channel.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(hostip))
        channel.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)

        with sent_messages_lock:
            sent_messages[current_sequence_number] = {
                'message': msg,
                'timestamp': time.time()
            }

        encoded = json.dumps(msg).encode('utf-8')
        channel.sendto(encoded, mcgrp)

         # Wait for acknowledgment
        channel.settimeout(5)  # Adjust the timeout as needed
        try:
            ack_data, _ = channel.recvfrom(1024)
            received_ack = json.loads(ack_data)
            received_sequence_number = received_ack.get('sequence_number')

            with sent_messages_lock:
                if received_sequence_number in sent_messages:
                    del sent_messages[received_sequence_number]
                else:
                    print("Received acknowledgment for an unknown sequence number.")

            print("Acknowledgment received from receiver.")
        except socket.timeout:
            print("No acknowledgment received.")


    except Exception as e:
        print(f"Error in sending: {e}")

def receive_messages():
    try:
        bindaddr = ('', port)
        channel.bind(bindaddr)

        mreq = struct.pack("=4s4s", socket.inet_aton(grpaddr), socket.inet_aton(hostip))
        channel.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        received_sequence_numbers = set()

        while not shutdown_event.is_set():
            buf, senderaddr = channel.recvfrom(1024)

            msg = json.loads(buf)
            received_sequence_number = msg.get('sequence_number')

            if received_sequence_number not in received_sequence_numbers:
                received_sequence_numbers.add(received_sequence_number)

                # Send acknowledgment back to sender with the received sequence number
                ack_msg = {'type': 'ack', 'sequence_number': received_sequence_number}
                ack_msg_encoded = json.dumps(ack_msg).encode('utf-8')
                channel.sendto(ack_msg_encoded, senderaddr)

                with sent_messages_lock:
                    if received_sequence_number in sent_messages:
                        received_msg = sent_messages.pop(received_sequence_number)
                        print(f"Received message with sequence number {received_sequence_number} from {senderaddr}: {received_msg['message']}")
                    else:
                        print(f"Received duplicate or out-of-order message with sequence number {received_sequence_number}.")

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
