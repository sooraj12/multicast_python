from flask import Flask, jsonify
from udp_multicast_module import send_and_receive, receive_messages
import threading

app = Flask(__name__)

@app.route('/health', methods=["GET"])
def health():
    print('test request received')
    return jsonify(message="OK"), 200

@app.route('/send', methods=['GET'])
def send():
    print('send message') 
    send_thread = threading.Thread(target=send_and_receive)
    send_thread.daemon = True
    send_thread.start()
    return jsonify(message="OK"), 200

if __name__ == "__main__":
    # Create and start the thread for receiving messages
    message_thread = threading.Thread(target=receive_messages)
    message_thread.daemon = True
    message_thread.start()

    app.run(host='0.0.0.0', port=5000)