"""
auth.py
-------
Everything related to "who is making this request" lives here, separate
from business logic (service.py) and routing (api.py) — auth is its own
concern.

Two distinct things happen in this file:

1. PASSWORD HASHING: we never store a user's actual password anywhere.
   We store a one-way hash of it. bcrypt (via passlib) is a well-vetted
   algorithm for this — it's deliberately slow, which makes brute-force
   guessing impractical, and it includes a random "salt" automatically
   so two users with the same password get different stored hashes.

2. JWT (JSON Web Token): after a successful login, we hand the browser
   a signed token instead of asking it to resend the password on every
   request. The token contains the username and an expiry, cryptographically
   signed with SECRET_KEY so it can't be tampered with. The browser sends
   this token back on every request (in an Authorization header); we
   verify the signature and trust what's inside without hitting the
   database again just to check "is this really them."
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

import storage
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Tells FastAPI: "clients get a token from POST /api/token, and must send
# it back as 'Authorization: Bearer <token>' on protected routes."
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Returns the user record if username/password are correct, else None."""
    user = storage.get_user_by_username(username)
    if not user or not verify_password(password, user["password_hash"]):
        return None
    return user


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    A FastAPI dependency: any route that adds `Depends(get_current_user)`
    automatically requires a valid token. FastAPI extracts the token from
    the Authorization header, runs this function, and passes the return
    value into your route function as an argument. If this function
    raises HTTPException, the route never runs at all.
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_error
    except JWTError:
        raise credentials_error

    user = storage.get_user_by_username(username)
    if user is None:
        raise credentials_error
    return user
