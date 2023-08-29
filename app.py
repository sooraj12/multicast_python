import threading
import signal
import atexit

from multi_cast import mc
from flask import Flask
from flask import jsonify, request
from threadpool import thread_pool
from multi_cast import mc

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify(message="OK"), 200


@app.route("/send", methods=["POST"])
def send():
    thread_pool.submit(mc.send_cast, request.json)
    return jsonify(message="OK"), 200


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    message_thread = threading.Thread(target=mc.receive_cast)
    message_thread.daemon = True
    message_thread.start()

    keep_alive_thread = threading.Thread(target=mc.send_membership_report)
    keep_alive_thread.daemon = True
    keep_alive_thread.start()

    atexit.register(mc.shutdown)

    app.run(host="0.0.0.0", port=5000)
