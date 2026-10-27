import os
import secrets

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
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
        raise HTTPException(
            status_code=401,
            detail="Incorrect Admin ID or password."
        )

    return {"ok": True}


@app.get("/api/health")
def health():
    return {"ok": True, "app": "EduVision"}


@app.get("/styles.css")
def styles():
    return FileResponse("styles.css", media_type="text/css")


@app.get("/app.js")
def javascript():
    return FileResponse("app.js", media_type="application/javascript")


@app.get("/config.js")
def config():
    return FileResponse("config.js", media_type="application/javascript")


@app.get("/")
def home():
    return FileResponse("index.html")
