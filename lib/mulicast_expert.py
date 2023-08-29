import threading
import socket
import multicast_expert
from flask import Flask

grpaddr = '239.1.2.3'
port = 5001
addr_family = socket.AF_INET

app = Flask(__name__)

def listener_thread(addr_family):
      with multicast_expert.McastRxSocket(addr_family, mcast_ips=[grpaddr], port=port, blocking=True) as rx_socket:
        while True:
            recv_result = rx_socket.recvfrom()
            if recv_result is not None:
                packet, sender_addr = recv_result

                print("Rx from %s:%d: %s" % (sender_addr[0], sender_addr[1], packet.decode("UTF-8")))

if __name__ == "__main__":
    # Start listener thread
    listener_thread_obj = threading.Thread(target=listener_thread, name="Multicast Listener Thread", args=(addr_family,), daemon=True)
    listener_thread_obj.start()

    # Run the Flask app
    app.run(host='0.0.0.0', port=5000)

