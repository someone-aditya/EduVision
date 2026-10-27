import os
import secrets
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class Login(BaseModel):
    admin_id: str
    password: str

@app.post("/api/admin-login")
def admin_login(body: Login):
    expected_id = os.getenv("EDUVISION_ADMIN_ID", "12126")
    expected_password = os.getenv("EDUVISION_ADMIN_PASSWORD", "12126")

    if not (
        secrets.compare_digest(body.admin_id, expected_id)
        and secrets.compare_digest(body.password, expected_password)
    ):
        raise HTTPException(status_code=401, detail="Incorrect Admin ID or password.")

    # Demo session token. Platform-admin actions still use the browser's
    # configured Supabase access, matching the current prototype setup.
    return {"ok": True, "token": secrets.token_urlsafe(24)}

