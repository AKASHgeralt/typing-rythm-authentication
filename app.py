import argparse

from flask import Flask, jsonify, render_template, request

from src import authenticate as auth
from src import config, storage

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
    return render_template("index.html", sentence=config.SENTENCE,
                           n_enrolled=len(config.ENROLLED_IDS))


@app.route("/enroll")
def enroll():
    return render_template("enroll.html", sentence=config.SENTENCE,
                           enrolled_ids=config.ENROLLED_IDS,
                           impostor_ids=config.IMPOSTOR_IDS)


@app.route("/authenticate")
def authenticate_page():
    return render_template("authenticate.html", sentence=config.SENTENCE,
                           enrolled_ids=config.ENROLLED_IDS,
                           models=auth.available(workspace()))


@app.get("/api/progress/<participant_id>")
def api_progress(participant_id):
    try:
        return jsonify(storage.progress(workspace().raw_file, participant_id))
    except storage.AttemptError as e:
        return jsonify(error=str(e)), 404


@app.post("/api/attempts")
def api_save_attempt():
    path = workspace().raw_file
    payload = request.get_json(silent=True)
    try:
        attempt_id = storage.save_attempt(path, payload)
    except storage.AttemptError as e:
        return jsonify(error=str(e)), 400
    return jsonify(attempt_id=attempt_id,
                   progress=storage.progress(path, payload["participant_id"])), 201


@app.post("/api/authenticate")
def api_authenticate():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="Request body must be a JSON object."), 400
    try:
        keys = storage.validate_keys(payload.get("keys"))
        result = auth.authenticate(workspace(), payload.get("claimed_id"),
                                   payload.get("model"), keys)
    except (storage.AttemptError, ValueError) as e:
        return jsonify(error=str(e)), 400
    except auth.NotTrained as e:
        return jsonify(error=str(e)), 409
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
