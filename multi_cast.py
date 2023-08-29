import socket
import json
import struct
import logging
import threading
import time

from scapy.contrib.igmp import IGMP

# Configuration
hostip = "192.168.1.4"
grpaddr = "234.0.0.1"
port = 42100
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

    def send_cast(self, msg):
        try:
            mcgrp = (grpaddr, port)
            encoded = json.dumps(msg).encode("utf-8")
            chunk_size = 700

            for i in range(0, len(encoded), chunk_size):
                chunk = encoded[i : i + chunk_size]
                chunk_msg = {
                    "chunk_id": i // chunk_size,
                    "total_chunks": (len(encoded) + chunk_size - 1) // chunk_size,
                    "data": chunk.decode("utf-8"),
                }

                with channel_lock:
                    self.channel.sendto(json.dumps(chunk_msg).encode("utf-8"), mcgrp)

        except Exception as e:
            logger.error(f"Error in sending: {e}")

    def receive_cast(self):
        try:
            chunk_buffer = {}
            while not shutdown_event.is_set():
                try:
                    buf, senderaddr = self.channel.recvfrom(1024)
                    if buf:
                        chunk_msg = json.loads(buf)
                        chunk_id = chunk_msg["chunk_id"]
                        total_chunks = chunk_msg["total_chunks"]
                        chunk_data = chunk_msg["data"]

                        chunk_buffer[chunk_id] = chunk_data

                        if len(chunk_buffer) == total_chunks:
                            complete_message = "".join(
                                chunk_buffer[i] for i in range(total_chunks)
                            )
                            chunk_buffer = {}
                            logger.info(
                                f"Received message from {senderaddr}: {complete_message}"
                            )

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
