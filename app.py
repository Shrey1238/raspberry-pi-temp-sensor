"""Flask dashboard serving a live temperature chart from the SQLite log.

    python3 app.py --db temperature_log.db --port 5000

Then open http://<pi-ip>:5000 from any device on the local network.
"""

from __future__ import annotations

import argparse
import sys

from flask import Flask, jsonify, render_template, request

from storage import DEFAULT_DB, TemperatureStore

MAX_LIMIT = 5000


def create_app(db_path: str = DEFAULT_DB) -> Flask:
    app = Flask(__name__)
    store = TemperatureStore(db_path)
    app.config["STORE"] = store

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/readings")
    def readings():
        try:
            limit = int(request.args.get("limit", 300))
        except ValueError:
            return jsonify(error="limit must be an integer"), 400
        limit = max(1, min(limit, MAX_LIMIT))
        return jsonify(store.recent(limit))

    @app.get("/api/latest")
    def latest():
        row = store.latest()
        if row is None:
            return jsonify(error="no readings yet"), 404
        return jsonify(row)

    @app.get("/api/stats")
    def stats():
        return jsonify(store.stats())

    return app


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Serve the live temperature dashboard.")
    p.add_argument("--db", default=DEFAULT_DB, help="SQLite database path (default: %(default)s)")
    p.add_argument("--host", default="0.0.0.0", help="Bind address (default: all interfaces)")
    p.add_argument("--port", type=int, default=5000)
    p.add_argument("--debug", action="store_true")
    args = p.parse_args(argv)

    create_app(args.db).run(host=args.host, port=args.port, debug=args.debug)
    return 0


if __name__ == "__main__":
    sys.exit(main())
