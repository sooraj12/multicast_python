import socket
import json
import struct
import logging
import threading
import time

from scapy.contrib.igmp import IGMP

# Configuration
hostip = "192.168.1.2"
grpaddr = "234.0.0.1"
port = 5003
keep_alive_interval = 150  # Interval for sending keep-alive messages in seconds
igmp_type = 0x11  # IGMP Membership Report

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
shutdown_event = threading.Event()
channel_lock = threading.Lock()
# Construct IGMP Membership Report packet


# Create an IGMP packet
igmp_packet = IGMP(type=igmp_type, gaddr=grpaddr)


class MultiCast:
    def __init__(self):
        self.channel = self.setup_socket()

    def setup_socket(self):
        try:
            sock = socket.socket(
                family=socket.AF_INET,
                type=socket.SOCK_DGRAM,
                proto=socket.IPPROTO_UDP,
                fileno=None,
            )
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
            sock.setsockopt(
                socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(hostip)
            )
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
            sock.bind(("", port))
            mreq = struct.pack(
                "=4s4s", socket.inet_aton(grpaddr), socket.inet_aton(hostip)
            )
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

            return sock
        except Exception as e:
            logger.error(f"Error setting up socket: {e}")
        raise SystemExit(1)

    def send_membership_report(self):
        while not shutdown_event.is_set():
            try:
                sock = socket.socket(
                    socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IGMP
                )
                sock.bind((hostip, port))
                sock.sendto(bytes(igmp_packet), (grpaddr, port))
                logger.info("Sent membership report")

                # # Wait for the next interval before sending the next report
                shutdown_event.wait(keep_alive_interval)
            except Exception as e:
                logger.error(f"Error sending membership report: {e}")

    def send_cast(self, msg, target_ips=None):
        try:
            if target_ips is None:
                target_ips = [grpaddr]
            
            encoded = json.dumps(msg).encode("utf-8")
            chunk_size = 2096
            total_chunks = (len(encoded) + chunk_size - 1) // chunk_size  # Calculate total chunks

            # Generate a unique message ID
            message_id = str(time.time())  # You can use a more sophisticated approach

            for target_ip in target_ips:
                mcgrp = (target_ip, port)
            
                for i in range(0, len(encoded), chunk_size):
                    chunk = encoded[i: i + chunk_size]
                    chunk_id = i // chunk_size  # Calculate chunk_id based on the chunk index

                    chunk_msg = {
                        "message_id": message_id,
                        "chunk_id": chunk_id,
                        "total_chunks": total_chunks,
                        "data": chunk.decode("utf-8"),
                    }

                    with channel_lock:
                        self.channel.sendto(json.dumps(chunk_msg).encode("utf-8"), mcgrp)

        except Exception as e:
            logger.error(f"Error in sending: {e}")

    def receive_cast(self):
        try:
            message_buffers = {}  # Store incomplete messages until all chunks are received

            while not shutdown_event.is_set():
                try:
                    buf, senderaddr = self.channel.recvfrom(8192)
                    if buf:
                        chunk_msg = json.loads(buf)
                        message_id = chunk_msg["message_id"]
                        chunk_id = chunk_msg["chunk_id"]
                        total_chunks = chunk_msg["total_chunks"]
                        chunk_data = chunk_msg["data"]
                        print(chunk_id)
                        print(total_chunks)
                        if message_id not in message_buffers:
                            message_buffers[message_id] = [None] * total_chunks
                        
                        message_buffers[message_id][chunk_id] = chunk_data
                        if None not in message_buffers[message_id]:
                            complete_message = "".join(message_buffers[message_id])
                            del message_buffers[message_id]
                            logger.info(
                                f"Received message from {senderaddr}: {complete_message}"
                            )
                            message = json.loads(complete_message)
                            print(message['type'])

                except socket.error as e:
                    if e.errno == 35:
                        time.sleep(0.1)
                        continue
                    else:
                        logger.error(f"Socket error in receiving: {e}")
        except Exception as e:
            logger.error(f"Error in receiving: {e}")

    def shutdown(self):
        with channel_lock:
            if self.channel:
                self.channel.close()
            shutdown_event.set()


mc = MultiCast()
