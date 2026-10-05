"""Create or reset an Admin account directly against a database.

Usage (password is prompted for, never passed as an argument):
    $env:DATABASE_URL = "<external connection string>"
    python scripts/reset_admin_password.py --email admin@example.com
"""

import argparse
import os
import sys
from getpass import getpass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import Role, User
from app.security import hash_password


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or reset an Admin account.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default="Initial Admin")
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1

    password = getpass("New password: ")
    if len(password) < 12:
        print("Password must be at least 12 characters.", file=sys.stderr)
        return 1
    if password != getpass("Confirm password: "):
        print("Passwords do not match.", file=sys.stderr)
        return 1

    email = args.email.strip().lower()
    engine = create_engine(database_url, pool_pre_ping=True)
    print(f"Connecting to {engine.url.get_backend_name()} host={engine.url.host or 'local'}")

    with Session(engine) as db:
        admin_role = db.execute(select(Role).where(Role.name == "Admin")).scalar_one_or_none()
        if not admin_role:
            print("No 'Admin' role found. Start the app once so reference data is seeded.", file=sys.stderr)
            return 1

        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user:
            user.password_hash = hash_password(password)
            user.role_id = admin_role.id
            user.active = True
            action = "reset"
        else:
            db.add(User(email=email, display_name=args.name, password_hash=hash_password(password), role_id=admin_role.id, active=True))
            action = "created"
        db.commit()

        print(f"Admin {email} {action}.")
        print("Existing users:")
        for row in db.execute(select(User.email, User.active).order_by(User.email)).all():
            print(f"  {row.email} active={row.active}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
