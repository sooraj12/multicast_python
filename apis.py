from flask import jsonify, request
from threadpool import thread_pool
from server import app
from multi_cast import mc


@app.route("/health", methods=["GET"])
def health():
    return jsonify(message="OK"), 200


@app.route("/send", methods=["POST"])
def send():
    thread_pool.submit(mc.send_cast, request.json)
    return jsonify(message="OK"), 200
