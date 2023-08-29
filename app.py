import threading
import signal
import atexit
from server import app

from multi_cast import mc


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
