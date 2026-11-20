"""User accounts: name, email and a HASHED password (never the password itself).

Accounts are stored in data/users.json, which stays on this computer and is not
uploaded to GitHub. Each user gets an anonymous ID (U01, U02 ...). Only these IDs
appear in the typing data.

Add a user (asks for the password without showing it):
    python -m src.users add --name Akash --email akash@gmail.com
List users:
    python -m src.users list
"""
import argparse
import getpass
import json
import re

from werkzeug.security import check_password_hash, generate_password_hash

from src import config

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserError(ValueError):
    pass


def load_users(ws):
    if not ws.users_file.exists():
        return []
    return json.loads(ws.users_file.read_text(encoding="utf-8"))


def save_users(ws, users):
    ws.data_dir.mkdir(parents=True, exist_ok=True)
    ws.users_file.write_text(json.dumps(users, indent=2), encoding="utf-8")


def add_user(ws, name, email, password):
    users = load_users(ws)
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        raise UserError(f"Not a valid email address: {email}")
    if any(u["email"] == email for u in users):
        raise UserError(f"Email already registered: {email}")
    if len(users) >= config.N_USERS:
        raise UserError(f"The study uses {config.N_USERS} users; all are registered.")
    if not config.MIN_PASSWORD_LENGTH <= len(password) <= config.MAX_PASSWORD_LENGTH:
        raise UserError("Password length must be between "
                        f"{config.MIN_PASSWORD_LENGTH} and {config.MAX_PASSWORD_LENGTH}.")
    if any(c.isspace() for c in password):
        raise UserError("Passwords may not contain spaces.")
    user = {"user_id": f"U{len(users) + 1:02d}", "name": name.strip(), "email": email,
            "password_length": len(password),
            "password_hash": generate_password_hash(password)}
    users.append(user)
    save_users(ws, users)
    return user


def by_id(ws, user_id):
    for u in load_users(ws):
        if u["user_id"] == user_id:
            return u
    return None


def by_email(ws, email):
    email = (email or "").strip().lower()
    for u in load_users(ws):
        if u["email"] == email:
            return u
    return None


def password_ok(user, password):
    return isinstance(password, str) and check_password_hash(user["password_hash"], password)


def public(user):
    """User details that are safe to send to the browser."""
    return {"user_id": user["user_id"], "name": user["name"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    config.add_workspace_argument(parser)
    sub = parser.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add", help="register a user")
    add.add_argument("--name", required=True)
    add.add_argument("--email", required=True)
    sub.add_parser("list", help="list registered users")
    args = parser.parse_args()
    ws = config.Workspace(args.workspace)

    if args.cmd == "add":
        pw = getpass.getpass("Password (not shown): ")
        if pw != getpass.getpass("Repeat password: "):
            raise SystemExit("Passwords do not match.")
        try:
            u = add_user(ws, args.name, args.email, pw)
        except UserError as e:
            raise SystemExit(str(e))
        print(f"Added {u['user_id']}: {u['name']} <{u['email']}>")
    else:
        users = load_users(ws)
        if not users:
            print("No users registered.")
        for u in users:
            print(f"{u['user_id']}  {u['name']:<12} {u['email']:<28} "
                  f"password length {u['password_length']}")


if __name__ == "__main__":
    main()
