import os,secrets
from fastapi import FastAPI,HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
app=FastAPI()
class Login(BaseModel):
 admin_id:str
 password:str
@app.post("/api/admin-login")
def admin_login(x:Login):
 if not(secrets.compare_digest(x.admin_id,os.getenv("EDUVISION_ADMIN_ID","12126")) and secrets.compare_digest(x.password,os.getenv("EDUVISION_ADMIN_PASSWORD","12126"))): raise HTTPException(401,"Incorrect login")
 return {"ok":True}
@app.get("/api/health")
def health(): return {"ok":True,"app":"EduVision"}
@app.get("/")
def home(): return FileResponse("index.html")
