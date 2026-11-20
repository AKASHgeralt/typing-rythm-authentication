import argparse

from flask import Flask, jsonify, render_template, request

from src import authenticate as auth
from src import config, storage, users

app = Flask(__name__)


def use_workspace(ws):
    app.config["WORKSPACE"] = ws


use_workspace(config.Workspace())


def workspace():
    return app.config["WORKSPACE"]


@app.context_processor
def inject_workspace():
    return {"workspace_name": workspace().name}


@app.route("/")
def index():
    return render_template("index.html", users=users.load_users(workspace()),
                           n_users=config.N_USERS)


@app.route("/collect")
def collect():
    return render_template("enroll.html",
                           users=[users.public(u) for u in users.load_users(workspace())])


@app.route("/login")
def login_page():
    return render_template("authenticate.html")


@app.get("/api/progress/<typist_id>/<int:session>")
def api_progress(typist_id, session):
    try:
        return jsonify(storage.progress(workspace(), typist_id, session))
    except storage.AttemptError as e:
        return jsonify(error=str(e)), 404


@app.post("/api/attempts")
def api_save_attempt():
    payload = request.get_json(silent=True)
    try:
        attempt_id = storage.save_attempt(workspace(), payload)
    except storage.AttemptError as e:
        return jsonify(error=str(e)), 400
    return jsonify(attempt_id=attempt_id, practice=attempt_id is None,
                   progress=storage.progress(workspace(), payload["typist_id"],
                                             payload["session"])), 201


@app.post("/api/login")
def api_login():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="Request body must be a JSON object."), 400
    try:
        result = auth.login(workspace(), payload.get("email"), payload.get("password"),
                            payload.get("keys"))
    except storage.AttemptError as e:
        return jsonify(error=str(e)), 400
    return jsonify(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the web application.")
    config.add_workspace_argument(parser)
    args = parser.parse_args()
    use_workspace(config.Workspace(args.workspace))
    if args.workspace:
        print(f"*** Using workspace '{args.workspace}': {workspace().root} ***")
    # Runs only on this computer (127.0.0.1); debug mode is for development.
    app.run(debug=True)
