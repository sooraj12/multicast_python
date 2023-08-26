from flask import Flask, jsonify
import asyncio
from udp_multicast_module import send_and_receive, receive_messages

hostip = '192.168.1.3'
grpaddr = '239.1.2.3'
port = 5001
msg = {'message': 'message from sender'}

app = Flask(__name__)

@app.route('/health', methods=["GET"])
def health():
    print('test request received')
    return jsonify(message="OK"), 200

if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    # send_receive_task = loop.create_task(send_and_receive(hostip, grpaddr, port, msg))
    receive_task = loop.create_task(receive_messages(hostip, grpaddr, port))

    app.run(host='0.0.0.0', port=5000)