import os, sqlite3, hashlib, secrets, calendar, threading
from datetime import datetime, date
import streamlit as st
import pandas as pd
import numpy as np
import cv2
import av
from streamlit_webrtc import VideoProcessorBase, WebRtcMode, webrtc_streamer

# Optional AI libraries: app still opens if a model is unavailable.
try:
    from deepface import DeepFace
    DEEPFACE_OK = True
except Exception:
    DEEPFACE_OK = False
try:
    from ultralytics import YOLO
    YOLO_OK = True
except Exception:
    YOLO_OK = False

st.set_page_config(page_title="EduVision", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

# -------------------- CONFIG --------------------
DB = "data/eduvision.db"
FACE_ROOT = "data/face_samples"
CASCADE = "assets/haarcascade_frontalface_default.xml"
QR_IMAGE = "assets/EduVision_QR.png"
FACE_MODEL = "Facenet512"
FACE_THRESHOLD = 0.40
ENROLLMENT_SAMPLES = 30
os.makedirs("data", exist_ok=True)
os.makedirs(FACE_ROOT, exist_ok=True)
DB_LOCK = threading.Lock()

# -------------------- PREMIUM UI --------------------
st.markdown("""
<style>
:root{--purple:#8b5cf6;--pink:#ec4899;--cyan:#22d3ee;--ink:#101828}
.stApp{background:linear-gradient(120deg,#fff7ed 0%,#f5f3ff 32%,#ecfeff 68%,#fdf2f8 100%);background-size:300% 300%;animation:bgMove 14s ease infinite;color:var(--ink)}
.stApp:before,.stApp:after{content:"";position:fixed;border-radius:50%;filter:blur(10px);z-index:-1;opacity:.45;animation:floatBlob 10s ease-in-out infinite}
.stApp:before{width:320px;height:320px;left:-90px;top:18%;background:radial-gradient(circle,#c4b5fd,transparent 68%)}
.stApp:after{width:380px;height:380px;right:-120px;bottom:5%;background:radial-gradient(circle,#67e8f9,transparent 68%);animation-delay:-4s}
@keyframes bgMove{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}
@keyframes floatBlob{0%,100%{transform:translateY(0) scale(1)}50%{transform:translateY(-35px) scale(1.08)}}
@keyframes shine{0%{background-position:-200% center}100%{background-position:200% center}}
.block-container{padding-top:1.15rem;max-width:1380px}
.ev-hero{padding:38px 42px;border:1px solid rgba(255,255,255,.72);border-radius:30px;background:linear-gradient(125deg,rgba(255,255,255,.82),rgba(255,255,255,.48));backdrop-filter:blur(18px);box-shadow:0 24px 70px rgba(109,40,217,.12);margin:6px 0 24px;position:relative;overflow:hidden}
.ev-hero:after{content:"";position:absolute;inset:-60% -20%;background:linear-gradient(110deg,transparent 42%,rgba(255,255,255,.65) 50%,transparent 58%);background-size:200% 100%;animation:shine 7s linear infinite;pointer-events:none}
.ev-kicker{font-size:.82rem;font-weight:800;letter-spacing:.18em;text-transform:uppercase;color:#7c3aed;margin-bottom:8px}.ev-title{font-size:3.3rem;font-weight:900;letter-spacing:-2px;line-height:1;background:linear-gradient(90deg,#7c3aed,#db2777,#0891b2);-webkit-background-clip:text;color:transparent}.ev-sub{font-size:1.08rem;color:#475467;margin-top:12px;max-width:760px}.ev-pills{margin-top:20px;display:flex;gap:9px;flex-wrap:wrap}.ev-pill{padding:7px 11px;border-radius:999px;background:rgba(255,255,255,.7);border:1px solid rgba(124,58,237,.12);font-size:.82rem;font-weight:700;color:#475467}.ev-section-title{font-size:1.12rem;font-weight:850;color:#344054;margin-bottom:3px}.ev-section-sub{font-size:.88rem;color:#667085;margin-bottom:14px}
.ev-live{display:inline-block;width:9px;height:9px;border-radius:50%;background:#20d67b;box-shadow:0 0 0 6px rgba(32,214,123,.12);margin-right:8px}.ev-warn{padding:14px 16px;border-radius:14px;background:rgba(255,174,0,.12);border:1px solid rgba(255,174,0,.3)}
div.stButton>button{border-radius:14px;font-weight:800;border:1px solid rgba(124,58,237,.16);box-shadow:0 6px 18px rgba(16,24,40,.04);transition:.2s ease}div.stButton>button:hover{transform:translateY(-2px) scale(1.045);border-color:#8b5cf6;box-shadow:0 14px 32px rgba(124,58,237,.20)}[data-testid="stSidebar"]{background:rgba(255,255,255,.72);backdrop-filter:blur(16px);border-right:1px solid rgba(124,58,237,.10)}[data-testid="stDialog"]>div{border-radius:24px!important;background:rgba(255,255,255,.96)!important}.qr-label{font-size:.8rem;opacity:.7;text-align:center}.small{font-size:.86rem;opacity:.72}
</style>
""", unsafe_allow_html=True)

# -------------------- DATABASE --------------------
def conn():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def execute(sql, args=()):
    with DB_LOCK:
        c=conn(); cur=c.execute(sql,args); c.commit(); rid=cur.lastrowid; c.close(); return rid

def rows(sql,args=()):
    c=conn(); r=c.execute(sql,args).fetchall(); c.close(); return r

def one(sql,args=()):
    r=rows(sql,args); return r[0] if r else None

def hpass(p): return hashlib.sha256(("EduVision::"+p).encode()).hexdigest()

def init_db():
    c=conn(); c.executescript("""
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
    CREATE TABLE IF NOT EXISTS schools(id INTEGER PRIMARY KEY AUTOINCREMENT, school_code TEXT UNIQUE, name TEXT UNIQUE, city TEXT, email TEXT, phone TEXT, status TEXT DEFAULT 'pending', created_at TEXT);
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, school_id INTEGER, user_code TEXT, name TEXT, role TEXT, password_hash TEXT, status TEXT DEFAULT 'pending', force_password_change INTEGER DEFAULT 0, email TEXT, phone TEXT, dob TEXT, qualification TEXT, staff_id TEXT, experience TEXT, reason TEXT, created_at TEXT, UNIQUE(school_id,user_code));
    CREATE TABLE IF NOT EXISTS classes(id INTEGER PRIMARY KEY AUTOINCREMENT, school_id INTEGER, name TEXT, class_teacher_user_id INTEGER, UNIQUE(school_id,name));
    CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY AUTOINCREMENT, school_id INTEGER, class_id INTEGER, student_code TEXT, name TEXT, roll_no TEXT, dob TEXT, email TEXT, father_name TEXT, father_phone TEXT, father_email TEXT, mother_name TEXT, mother_phone TEXT, mother_email TEXT, address TEXT, blood_group TEXT, emergency_name TEXT, emergency_relation TEXT, emergency_phone TEXT, notes TEXT, status TEXT DEFAULT 'pending', face_registered INTEGER DEFAULT 0, created_at TEXT, UNIQUE(school_id,student_code));
    CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY AUTOINCREMENT, school_id INTEGER, class_id INTEGER, student_id INTEGER, day TEXT, time TEXT, status TEXT, method TEXT, marked_by INTEGER, UNIQUE(school_id,student_id,day));
    CREATE TABLE IF NOT EXISTS class_sessions(id INTEGER PRIMARY KEY AUTOINCREMENT, school_id INTEGER, class_id INTEGER, day TEXT, confirmed_by INTEGER, created_at TEXT, UNIQUE(school_id,class_id,day));
    CREATE TABLE IF NOT EXISTS holidays(id INTEGER PRIMARY KEY AUTOINCREMENT, school_id INTEGER, day TEXT, name TEXT, UNIQUE(school_id,day));
    CREATE TABLE IF NOT EXISTS announcements(id INTEGER PRIMARY KEY AUTOINCREMENT, school_id INTEGER, title TEXT, body TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS approvals(id INTEGER PRIMARY KEY AUTOINCREMENT, school_id INTEGER, kind TEXT, target_id INTEGER, title TEXT, detail TEXT, status TEXT DEFAULT 'pending', created_at TEXT, reviewed_at TEXT, reviewed_by INTEGER);
    CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT, action TEXT, detail TEXT, created_at TEXT);
    """)
    if not c.execute("SELECT 1 FROM settings WHERE key='super_admin_password'").fetchone():
        c.execute("INSERT INTO settings VALUES('super_admin_password',?)",(hpass("12126"),))
    c.commit(); c.close()
init_db()

def audit(actor,action,detail=""):
    execute("INSERT INTO audit(actor,action,detail,created_at) VALUES(?,?,?,?)",(actor,action,detail,datetime.now().isoformat(timespec="seconds")))

def new_code(prefix): return prefix + secrets.token_hex(3).upper()

def school_day(school_id, d=None):
    d=d or date.today()
    if d.weekday()==6: return False, "Sunday"
    h=one("SELECT name FROM holidays WHERE school_id=? AND day=?",(school_id,d.isoformat()))
    return (False,h["name"]) if h else (True,"School Day")

# -------------------- SESSION --------------------
for k,v in {"auth":False,"role":None,"user_id":None,"school_id":None,"school_name":None,"user_name":None,"guest_school":None,"view":"home","scan_results":None}.items():
    if k not in st.session_state: st.session_state[k]=v

def logout():
    for k in ["auth","role","user_id","school_id","school_name","user_name","guest_school"]: st.session_state[k]=None if k!="auth" else False
    st.session_state.view="home"; st.rerun()

def qr_button():
    @st.dialog("📱 Scan EduVision")
    def show_qr():
        if os.path.exists(QR_IMAGE):
            st.image(QR_IMAGE, width=245)
        else:
            st.error("QR image is missing from assets/EduVision_QR.png")
        st.caption("Scan to open the main EduVision website.")
    if st.button("◉", key="qr_circle", help="Open QR code"):
        show_qr()

# -------------------- PUBLIC / AUTH --------------------
def public_home():
    top1,top2=st.columns([14,1])
    with top1:
        st.markdown('''<div class="ev-hero"><div class="ev-kicker">SMARTER CLASSROOMS • POWERED BY AI</div><div class="ev-title">🎓 EduVision</div><div class="ev-sub">One intelligent space for attendance, classrooms, teachers and school management — designed to feel simple, fast and modern.</div><div class="ev-pills"><span class="ev-pill">✨ AI Attendance</span><span class="ev-pill">📸 Class Scan</span><span class="ev-pill">🧠 Classroom Monitor</span><span class="ev-pill">📊 Smart Reports</span></div></div>''',unsafe_allow_html=True)
    with top2:
        st.caption("SCAN")
        qr_button()
    st.markdown("### Welcome to EduVision")
    st.caption("Choose where you want to go. Your school data stays separated and protected.")
    a,b,c=st.columns(3,gap="large")
    with a:
        st.markdown('<div class="ev-section-title">🏫 Find Your School</div><div class="ev-section-sub">Students, teachers and school admins start here.</div>',unsafe_allow_html=True)
        schools=rows("SELECT * FROM schools WHERE status='approved' ORDER BY name")
        opts={f"{x['name']} • {x['school_code']}":x for x in schools}
        choice=st.selectbox("School",["Select school..."]+list(opts.keys()),label_visibility="collapsed")
        if choice!="Select school...":
            s=opts[choice]; st.session_state.selected_school=s["id"]
            st.success(f"✓ {s['name']}")
            if st.button("👨‍🏫 Teacher Login",use_container_width=True): st.session_state.view="school_login"; st.rerun()
            if st.button("🏫 School Admin Login",use_container_width=True): st.session_state.view="school_login"; st.rerun()
            if st.button("👨‍🎓 Continue as Student",use_container_width=True): st.session_state.guest_school=s["id"]; st.session_state.view="guest"; st.rerun()
        else: st.info("Select your school to continue.")
    with b:
        st.markdown('<div class="ev-section-title">🚀 Bring EduVision to Your School</div><div class="ev-section-sub">Register a school and send it for secure approval.</div>',unsafe_allow_html=True)
        st.write("AI-ready school management with attendance, classes, calendars and reports.")
        if st.button("🏫 Register New School",use_container_width=True,type="primary"): st.session_state.view="register_school"; st.rerun()
        if st.button("🛡️ Apply as Admin",use_container_width=True): st.session_state.view="admin_apply"; st.rerun()
    with c:
        st.markdown('<div class="ev-section-title">👑 EduVision Administration</div><div class="ev-section-sub">Secure platform controls for authorized administrators.</div>',unsafe_allow_html=True)
        st.write("Manage approvals, schools, accounts and platform-wide settings.")
        if st.button("👑 Super Admin Login",use_container_width=True): st.session_state.view="super_login"; st.rerun()
        st.caption("Super Admin access is separate from school accounts.")
    st.markdown("---")
    x,y,z=st.columns(3)
    x.markdown("**⚡ Fast**  \nQuick classroom workflows")
    y.markdown("**🔐 Controlled**  \nRole-based school access")
    z.markdown("**🌐 Multi-School**  \nBuilt to grow beyond one campus")

def register_school():
    st.title("🏫 Register New School")
    with st.form("schoolreg"):
        name=st.text_input("School Name *"); city=st.text_input("City"); email=st.text_input("Official Email"); phone=st.text_input("School Phone")
        submit=st.form_submit_button("Send Registration Request",type="primary")
    if submit:
        if not name.strip(): st.error("School name is required.")
        elif one("SELECT 1 FROM schools WHERE lower(name)=lower(?)",(name.strip(),)): st.error("This school is already registered or pending.")
        else:
            code=new_code("SCH-"); sid=execute("INSERT INTO schools(school_code,name,city,email,phone,status,created_at) VALUES(?,?,?,?,?,'pending',?)",(code,name.strip(),city,email,phone,datetime.now().isoformat(timespec="seconds")))
            execute("INSERT INTO approvals(school_id,kind,target_id,title,detail,created_at) VALUES(?,?,?,?,?,?)",(sid,"school",sid,f"New school: {name}",f"{city} | {email} | {phone}",datetime.now().isoformat(timespec="seconds")))
            st.success(f"Request sent. School code: {code}")
    if st.button("← Main Page"): st.session_state.view="home"; st.rerun()

def admin_apply():
    st.title("🛡️ Apply as School Admin")
    st.info("For the demo, use non-sensitive/sample verification details. Do not upload Aadhaar or other government-ID images.")
    schools=rows("SELECT * FROM schools WHERE status='approved' ORDER BY name")
    labels={f"{s['name']} • {s['school_code']}":s for s in schools}
    with st.form("adminapply"):
        school_label=st.selectbox("School *",list(labels.keys()) if labels else ["No approved schools"])
        name=st.text_input("Full Name *"); dob=st.date_input("Date of Birth",value=date(1990,1,1),min_value=date(1940,1,1),max_value=date.today())
        qualification=st.text_input("Qualification"); staff=st.text_input("Official Staff/Employee ID"); exp=st.text_input("Years of Experience"); email=st.text_input("Official School Email"); phone=st.text_input("Phone Number"); reason=st.text_area("Reason for requesting admin access")
        ok=st.form_submit_button("Send Admin Application",type="primary")
    if ok and labels:
        s=labels[school_label]; uid=execute("INSERT INTO users(school_id,user_code,name,role,password_hash,status,email,phone,dob,qualification,staff_id,experience,reason,created_at) VALUES(?,?,?,?,?,'pending',?,?,?,?,?,?,?,?)",(s['id'],new_code("ADM-"),name,"school_admin",hpass(secrets.token_urlsafe(12)),email,phone,dob.isoformat(),qualification,staff,exp,reason,datetime.now().isoformat(timespec="seconds")))
        execute("INSERT INTO approvals(school_id,kind,target_id,title,detail,created_at) VALUES(?,?,?,?,?,?)",(s['id'],"admin",uid,f"Admin application: {name}",f"Qualification: {qualification}; Staff ID: {staff}; Experience: {exp}; DOB: {dob}; Email: {email}",datetime.now().isoformat(timespec="seconds")))
        st.success("Application sent to the EduVision Super Admin.")
    if st.button("← Main Page"): st.session_state.view="home"; st.rerun()

def super_login():
    st.title("👑 EduVision Super Admin")
    with st.form("superlogin"):
        sid=st.text_input("Super Admin ID"); pw=st.text_input("Password",type="password"); ok=st.form_submit_button("Login",type="primary")
    if ok:
        saved=one("SELECT value FROM settings WHERE key='super_admin_password'")["value"]
        if sid=="12126" and hpass(pw)==saved:
            st.session_state.auth=True; st.session_state.role="super_admin"; st.session_state.user_name="EduVision Super Admin"; st.session_state.view="app"; audit("12126","login"); st.rerun()
        st.error("Invalid ID or password.")
    if st.button("← Main Page"): st.session_state.view="home"; st.rerun()

def school_login():
    sid=st.session_state.get("selected_school")
    s=one("SELECT * FROM schools WHERE id=? AND status='approved'",(sid,))
    if not s: st.session_state.view="home"; st.rerun()
    st.title(f"🏫 {s['name']}")
    tabs=st.tabs(["🔐 Login","📝 Register Teacher","🔑 Change Password"])
    with tabs[0]:
        with st.form("login"):
            code=st.text_input("Teacher/Admin ID"); pw=st.text_input("Password",type="password"); ok=st.form_submit_button("Login",type="primary")
        if ok:
            u=one("SELECT * FROM users WHERE school_id=? AND user_code=?",(sid,code.strip()))
            if not u or u['status']!='approved' or hpass(pw)!=u['password_hash']: st.error("Invalid, pending, or disabled account.")
            else:
                st.session_state.auth=True; st.session_state.role=u['role']; st.session_state.user_id=u['id']; st.session_state.school_id=sid; st.session_state.school_name=s['name']; st.session_state.user_name=u['name']; st.session_state.view="app"; audit(code,"login",s['name']); st.rerun()
    with tabs[1]:
        with st.form("teacherreg"):
            name=st.text_input("Teacher Name *"); code=st.text_input("Requested Teacher ID *"); email=st.text_input("School Email"); phone=st.text_input("Phone"); pw=st.text_input("Temporary Password *",type="password"); ok=st.form_submit_button("Request Registration")
        if ok:
            if not name or not code or not pw: st.error("Name, ID and password are required.")
            elif one("SELECT 1 FROM users WHERE school_id=? AND user_code=?",(sid,code)): st.error("That ID already exists.")
            else:
                uid=execute("INSERT INTO users(school_id,user_code,name,role,password_hash,status,email,phone,created_at) VALUES(?,?,?,?,?,'pending',?,?,?)",(sid,code.strip(),name.strip(),"teacher",hpass(pw),email,phone,datetime.now().isoformat(timespec="seconds")))
                execute("INSERT INTO approvals(school_id,kind,target_id,title,detail,created_at) VALUES(?,?,?,?,?,?)",(sid,"teacher",uid,f"Teacher registration: {name}",f"ID: {code}; Email: {email}",datetime.now().isoformat(timespec="seconds")))
                st.success("Registration request sent to the EduVision Super Admin for approval.")
    with tabs[2]:
        with st.form("changepw"):
            code=st.text_input("Teacher/Admin ID",key="cpid"); old=st.text_input("Current Password",type="password"); new=st.text_input("New Password",type="password"); confirm=st.text_input("Confirm New Password",type="password"); ok=st.form_submit_button("Change Password")
        if ok:
            u=one("SELECT * FROM users WHERE school_id=? AND user_code=?",(sid,code))
            if not u or hpass(old)!=u['password_hash']: st.error("Current ID/password is incorrect.")
            elif len(new)<6: st.error("Use at least 6 characters.")
            elif new!=confirm: st.error("Passwords do not match.")
            else: execute("UPDATE users SET password_hash=?,force_password_change=0 WHERE id=?",(hpass(new),u['id'])); audit(code,"password changed"); st.success("Password changed.")
    if st.button("← Main Page"): st.session_state.view="home"; st.rerun()

def guest_page():
    sid=st.session_state.guest_school; s=one("SELECT * FROM schools WHERE id=?",(sid,))
    if not s: st.session_state.view="home"; st.rerun()
    st.title(f"🏫 {s['name']}"); st.caption("Student / Guest • Read-only public information")
    tabs=st.tabs(["📢 Notices","📅 Calendar","🏫 Classes"])
    with tabs[0]:
        ann=rows("SELECT * FROM announcements WHERE school_id=? ORDER BY id DESC LIMIT 10",(sid,))
        if not ann: st.info("No announcements yet.")
        for a in ann: st.subheader(a['title']); st.write(a['body'])
    with tabs[1]:
        hs=rows("SELECT day,name FROM holidays WHERE school_id=? ORDER BY day",(sid,)); st.dataframe(pd.DataFrame([dict(x) for x in hs]),use_container_width=True,hide_index=True) if hs else st.info("No holidays added yet.")
    with tabs[2]:
        cs=rows("SELECT name FROM classes WHERE school_id=? ORDER BY name",(sid,)); st.write(", ".join(x['name'] for x in cs) if cs else "No classes listed yet.")
    st.warning("Private student records, attendance, cameras and staff tools are not available in Student/Guest mode.")
    if st.button("← Main Page"): st.session_state.guest_school=None; st.session_state.view="home"; st.rerun()

# -------------------- FACE AI --------------------
if hasattr(cv2, "CascadeClassifier"):
    face_detector = cv2.CascadeClassifier(CASCADE) if os.path.exists(CASCADE) else cv2.CascadeClassifier()
else:
    face_detector = None
def embedding(img):
    if not DEEPFACE_OK or img is None or img.size==0: return None
    try:
        r=DeepFace.represent(img_path=img,model_name=FACE_MODEL,detector_backend="skip",enforce_detection=False,align=False)
        e=np.asarray(r[0]["embedding"],dtype=np.float32); n=np.linalg.norm(e); return e/n if n else None
    except Exception: return None

def crop(img,b,p=.15):
    x,y,w,h=map(int,b); pad=int(max(w,h)*p); return img[max(0,y-pad):min(img.shape[0],y+h+pad),max(0,x-pad):min(img.shape[1],x+w+pad)]

def sample_dir(school_id,student_id): return os.path.join(FACE_ROOT,str(school_id),str(student_id))

def student_embeddings(school_id,class_id=None):
    sql="SELECT id,name,student_code FROM students WHERE school_id=? AND status='approved' AND face_registered=1"; args=[school_id]
    if class_id: sql+=" AND class_id=?"; args.append(class_id)
    db={}
    for s in rows(sql,tuple(args)):
        folder=sample_dir(school_id,s['id']); em=[]
        if os.path.isdir(folder):
            for fn in os.listdir(folder):
                im=cv2.imread(os.path.join(folder,fn)); e=embedding(im)
                if e is not None: em.append(e)
        if em: db[s['id']]={"name":s['name'],"code":s['student_code'],"emb":em}
    return db

def recognize_face(face,db):
    q=embedding(face)
    if q is None or not db: return None,999
    scores=[]
    for sid,d in db.items():
        ds=sorted(float(1-np.dot(q,e)) for e in d['emb']); scores.append((float(np.mean(ds[:min(5,len(ds))])),sid))
    scores.sort(); best,sid=scores[0]
    if best>FACE_THRESHOLD: return None,best
    if len(scores)>1 and scores[1][0]-best<.03: return None,best
    return sid,best

class EnrollmentCamera(VideoProcessorBase):
    def __init__(self): self.samples=[]; self.n=0; self.lock=threading.Lock()
    def recv(self,frame):
        img=frame.to_ndarray(format="bgr24"); gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY); faces=face_detector.detectMultiScale(gray,1.15,7,minSize=(120,120)) if face_detector is not None and not face_detector.empty() else []
        self.n+=1
        if len(faces)==1:
            x,y,w,h=faces[0]; cv2.rectangle(img,(x,y),(x+w,y+h),(40,220,110),2)
            if self.n%5==0 and len(self.samples)<ENROLLMENT_SAMPLES:
                f=crop(img,faces[0]);
                with self.lock: self.samples.append(f.copy())
        cv2.putText(img,f"Samples: {len(self.samples)}/{ENROLLMENT_SAMPLES}",(20,35),cv2.FONT_HERSHEY_SIMPLEX,.75,(255,255,255),2)
        if len(faces)!=1: cv2.putText(img,"Keep exactly one face in view",(20,70),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,180,255),2)
        return av.VideoFrame.from_ndarray(img,format="bgr24")

class SnapshotCamera(VideoProcessorBase):
    def __init__(self): self.latest=None; self.lock=threading.Lock()
    def recv(self,frame):
        img=frame.to_ndarray(format="bgr24")
        with self.lock: self.latest=img.copy()
        return av.VideoFrame.from_ndarray(img,format="bgr24")

@st.cache_resource
def yolo_model(): return YOLO("yolo11n.pt") if YOLO_OK else None
class OccupancyCamera(VideoProcessorBase):
    def __init__(self): self.inside=0; self.entered=0; self.exited=0; self.prev={}; self.last_movement="No movement yet"
    def recv(self,frame):
        img=frame.to_ndarray(format="bgr24"); model=yolo_model(); line=img.shape[1]//2
        cv2.line(img,(line,0),(line,img.shape[0]),(255,200,0),2)
        if model:
            try:
                result=model.track(img,persist=True,classes=[0],verbose=False)[0]
                if result.boxes is not None and result.boxes.id is not None:
                    for box,tid in zip(result.boxes.xyxy.cpu().numpy(),result.boxes.id.int().cpu().tolist()):
                        x1,y1,x2,y2=map(int,box); cx=(x1+x2)//2; old=self.prev.get(tid)
                        if old is not None and old<line<=cx: self.entered+=1; self.inside+=1; self.last_movement=f"Entry • {datetime.now().strftime('%I:%M:%S %p')}"
                        elif old is not None and old>line>=cx: self.exited+=1; self.inside=max(0,self.inside-1); self.last_movement=f"Exit • {datetime.now().strftime('%I:%M:%S %p')}"
                        self.prev[tid]=cx; cv2.rectangle(img,(x1,y1),(x2,y2),(60,220,120),2)
            except Exception: pass
        cv2.putText(img,f"Inside {self.inside} | Entered {self.entered} | Exited {self.exited}",(20,35),cv2.FONT_HERSHEY_SIMPLEX,.7,(255,255,255),2)
        return av.VideoFrame.from_ndarray(img,format="bgr24")

# -------------------- COMMON SCHOOL HELPERS --------------------
def school_classes(sid): return rows("SELECT * FROM classes WHERE school_id=? ORDER BY name",(sid,))
def approved_students(sid,cid): return rows("SELECT * FROM students WHERE school_id=? AND class_id=? AND status='approved' ORDER BY lower(name)",(sid,cid))
def today_present(sid,cid): return rows("SELECT a.*,s.name,s.student_code FROM attendance a JOIN students s ON s.id=a.student_id WHERE a.school_id=? AND a.class_id=? AND a.day=? AND a.status='Present' ORDER BY s.name",(sid,cid,date.today().isoformat()))
def mark_present(sid,cid,student_id,method,user_id):
    try: execute("INSERT INTO attendance(school_id,class_id,student_id,day,time,status,method,marked_by) VALUES(?,?,?,?,?,'Present',?,?)",(sid,cid,student_id,date.today().isoformat(),datetime.now().strftime("%H:%M:%S"),method,user_id)); return True
    except sqlite3.IntegrityError: return False

# -------------------- SUPER ADMIN --------------------
def super_dashboard():
    st.sidebar.title("👑 EduVision Super Admin")
    page=st.sidebar.radio("Management",["🌐 Overview","🏫 School Access","👨‍🏫 Teacher Approvals","🛡️ Admin Approvals","🏫 School Approvals","🔐 Login Management","📜 Audit Log"])
    st.sidebar.divider()
    if st.sidebar.button("🔑 Change Password",use_container_width=True): st.session_state.super_change=True
    if st.sidebar.button("🚪 Logout",use_container_width=True): logout()
    if st.session_state.get("super_change"):
        with st.sidebar.form("supercp"):
            old=st.text_input("Current",type="password"); new=st.text_input("New",type="password"); conf=st.text_input("Confirm",type="password"); ok=st.form_submit_button("Update")
        if ok:
            saved=one("SELECT value FROM settings WHERE key='super_admin_password'")["value"]
            if hpass(old)!=saved: st.sidebar.error("Current password incorrect")
            elif len(new)<6 or new!=conf: st.sidebar.error("Check new password")
            else: execute("UPDATE settings SET value=? WHERE key='super_admin_password'",(hpass(new),)); audit("12126","super password changed"); st.session_state.super_change=False; st.sidebar.success("Changed")
    st.title(page)
    if page=="🌐 Overview":
        a,b,c,d=st.columns(4); a.metric("Schools",one("SELECT count(*) n FROM schools WHERE status='approved'")["n"]); b.metric("Teachers/Admins",one("SELECT count(*) n FROM users WHERE status='approved'")["n"]); c.metric("Students",one("SELECT count(*) n FROM students WHERE status='approved'")["n"]); d.metric("Pending",one("SELECT count(*) n FROM approvals WHERE status='pending'")["n"])
    elif page=="🏫 School Access":
        schools=rows("SELECT * FROM schools WHERE status='approved' ORDER BY name")
        if not schools:
            st.info("No approved schools yet.")
            return
        labels={f"{x['name']} • {x['school_code']}":x for x in schools}
        chosen=st.selectbox("Choose a school to manage",list(labels.keys()))
        school=labels[chosen]
        st.info("Super Admin access: you can view and manage the same school tools available to the School Admin, including the calendar.")
        school_app(sid_override=school['id'], role_override="super_admin", super_mode=True)
    elif page in ["👨‍🏫 Teacher Approvals","🛡️ Admin Approvals","🏫 School Approvals"]:
        kind="teacher" if "Teacher" in page else ("admin" if "Admin" in page else "school"); aps=rows("SELECT * FROM approvals WHERE kind=? AND status='pending' ORDER BY id DESC",(kind,))
        if not aps: st.success("No pending requests.")
        for a in aps:
            with st.expander(a['title']):
                st.write(a['detail']); x,y=st.columns(2)
                if x.button("✅ Approve",key=f"ap{a['id']}"):
                    if kind=="school":
                        execute("UPDATE schools SET status='approved' WHERE id=?",(a['target_id'],))
                    elif kind=="teacher":
                        execute("UPDATE users SET status='approved' WHERE id=?",(a['target_id'],))
                    else:
                        temp="EV-"+secrets.token_hex(3).upper(); execute("UPDATE users SET status='approved',password_hash=?,force_password_change=1 WHERE id=?",(hpass(temp),a['target_id'])); st.session_state[f"temp{a['id']}"]=temp
                    execute("UPDATE approvals SET status='approved',reviewed_at=?,reviewed_by=-1 WHERE id=?",(datetime.now().isoformat(timespec="seconds"),a['id'])); audit("12126","approved",a['title']); st.rerun()
                if y.button("❌ Decline",key=f"de{a['id']}"):
                    execute("UPDATE approvals SET status='declined',reviewed_at=?,reviewed_by=-1 WHERE id=?",(datetime.now().isoformat(timespec="seconds"),a['id']));
                    if kind=="school": execute("UPDATE schools SET status='declined' WHERE id=?",(a['target_id'],))
                    else: execute("UPDATE users SET status='declined' WHERE id=?",(a['target_id'],))
                    audit("12126","declined",a['title']); st.rerun()
        for k,v in list(st.session_state.items()):
            if str(k).startswith("temp"): st.warning(f"Temporary password generated: **{v}** — give it securely to the approved admin; they must change it after login.")
    elif page=="🔐 Login Management":
        schools=rows("SELECT * FROM schools WHERE status='approved' ORDER BY name"); labels={f"{s['name']} • {s['school_code']}":s for s in schools}; q=st.text_input("🔎 Search school")
        filtered={k:v for k,v in labels.items() if q.lower() in k.lower()}
        if filtered:
            lab=st.selectbox("School",list(filtered.keys())); s=filtered[lab]; us=rows("SELECT * FROM users WHERE school_id=? ORDER BY role,name",(s['id'],))
            for u in us:
                if st.button(f"{u['user_code']}  •  {u['name']}  •  {u['role']}  •  {u['status']}",key=f"u{u['id']}",use_container_width=True): st.session_state.manage_user=u['id']
            uid=st.session_state.get("manage_user")
            if uid:
                u=one("SELECT * FROM users WHERE id=?",(uid,)); st.subheader(f"Account: {u['name']}"); st.write(f"**ID:** {u['user_code']}  |  **Role:** {u['role']}  |  **Status:** {u['status']}")
                x,y=st.columns(2)
                if x.button("🔑 Reset Password"):
                    temp="EV-"+secrets.token_hex(3).upper(); execute("UPDATE users SET password_hash=?,force_password_change=1 WHERE id=?",(hpass(temp),uid)); audit("12126","password reset",u['user_code']); st.success(f"Temporary password: **{temp}**")
                label="✅ Enable Account" if u['status']=='disabled' else "🚫 Disable Account"
                if y.button(label): execute("UPDATE users SET status=? WHERE id=?",("approved" if u['status']=='disabled' else "disabled",uid)); audit("12126",label,u['user_code']); st.rerun()
    else:
        a=rows("SELECT * FROM audit ORDER BY id DESC LIMIT 300"); st.dataframe(pd.DataFrame([dict(x) for x in a]),use_container_width=True,hide_index=True)

# -------------------- SCHOOL APP --------------------
def school_app(sid_override=None, role_override=None, super_mode=False):
    sid = sid_override if sid_override is not None else st.session_state.school_id
    uid = -1 if super_mode else st.session_state.user_id
    role = role_override if role_override is not None else st.session_state.role
    school = one("SELECT * FROM schools WHERE id=?",(sid,))
    school_name = school['name'] if school else "School"
    can_admin = role in ("school_admin","super_admin")
    pages=["🏠 Dashboard","🏫 Classes","👤 Student Registration","📋 Smart Attendance","📸 Scan Class","🧠 AI Classroom Monitor","📅 Calendar","📊 Reports"]
    if can_admin:
        pages += ["🛡️ Student Approvals","👨‍🏫 Staff Accounts","📢 Announcements"]
    if super_mode:
        page=st.selectbox("School workspace",pages,key=f"super_school_page_{sid}")
        st.caption(f"👑 Super Admin → 🏫 {school_name}")
    else:
        st.sidebar.title("🎓 EduVision")
        st.sidebar.caption(school_name)
        st.sidebar.write(f"👤 {st.session_state.user_name} • {role.replace('_',' ').title()}")
        page=st.sidebar.radio("Navigation",pages)
        st.sidebar.divider()
        st.sidebar.success("● System Online")
        if st.sidebar.button("🚪 Logout",use_container_width=True): logout()
    st.title(page)
    st.caption(f"🏫 {school_name}")

    classes=school_classes(sid); class_map={x['name']:x for x in classes}
    if page=="🏠 Dashboard":
        total=one("SELECT count(*) n FROM students WHERE school_id=? AND status='approved'",(sid,))["n"]; pres=one("SELECT count(DISTINCT student_id) n FROM attendance WHERE school_id=? AND day=? AND status='Present'",(sid,date.today().isoformat()))["n"]
        a,b,c,d=st.columns(4); a.metric("Students",total); b.metric("Present Today",pres); c.metric("Classes",len(classes)); d.metric("Pending Approvals",one("SELECT count(*) n FROM approvals WHERE school_id=? AND status='pending' AND kind IN ('teacher','student')",(sid,))["n"])
        st.subheader("Class Overview")
        for cl in classes:
            totalc=len(approved_students(sid,cl['id'])); pc=len(today_present(sid,cl['id'])); ok,_=school_day(sid); absent=max(0,totalc-pc) if ok and one("SELECT 1 FROM class_sessions WHERE school_id=? AND class_id=? AND day=?",(sid,cl['id'],date.today().isoformat())) else 0
            st.markdown(f"**{cl['name']}** — 👥 {totalc} students • ✅ {pc} present • ❌ {absent} absent")
    elif page=="🏫 Classes":
        if can_admin:
            with st.form("newclass",clear_on_submit=True):
                n=st.text_input("New Class Name",placeholder="10-A"); ok=st.form_submit_button("➕ Add Class")
            if ok and n.strip():
                try: execute("INSERT INTO classes(school_id,name) VALUES(?,?)",(sid,n.strip())); st.rerun()
                except sqlite3.IntegrityError: st.warning("Class already exists.")
        if not classes: st.info("No classes yet.")
        for cl in classes:
            ss=approved_students(sid,cl['id']); pp={x['student_id'] for x in today_present(sid,cl['id'])}; st.subheader(cl['name']); a,b,c=st.columns(3); a.metric("Total",len(ss)); b.metric("Present",len(pp)); c.metric("Not Confirmed",max(0,len(ss)-len(pp)))
            for s in ss:
                if st.button(f"👤 {s['name']} • {s['student_code']} • {'Present' if s['id'] in pp else 'Not marked'}",key=f"stud{s['id']}",use_container_width=True): st.session_state.profile_student=s['id']
            ps=st.session_state.get("profile_student")
            if ps and one("SELECT class_id FROM students WHERE id=?",(ps,))["class_id"]==cl['id']:
                s=one("SELECT * FROM students WHERE id=?",(ps,)); st.markdown("### Student Profile")
                hist=rows("SELECT day,time,status,method FROM attendance WHERE student_id=? ORDER BY day DESC",(ps,)); sessions=one("SELECT count(*) n FROM class_sessions WHERE class_id=?",(cl['id'],))["n"]; present=len(hist); pct=round(100*present/sessions,1) if sessions else 0
                st.write(f"**{s['name']}** • {s['student_code']} • Roll {s['roll_no']} • Attendance {pct}%"); st.progress(min(pct/100,1.0))
                with st.expander("🔒 Private Details — authorized staff only"):
                    st.write(f"DOB: {s['dob']} | Blood group: {s['blood_group']}"); st.write(f"Father/Guardian: {s['father_name']} • {s['father_phone']} • {s['father_email']}"); st.write(f"Mother/Guardian: {s['mother_name']} • {s['mother_phone']} • {s['mother_email']}"); st.write(f"Address: {s['address']}"); st.write(f"Emergency: {s['emergency_name']} ({s['emergency_relation']}) • {s['emergency_phone']}"); st.write(f"Notes: {s['notes']}")
                if hist: st.dataframe(pd.DataFrame([dict(x) for x in hist]),use_container_width=True,hide_index=True)
    elif page=="👤 Student Registration":
        if not classes: st.warning("Create a class first."); return
        with st.form("studentreg"):
            cln=st.selectbox("Class *",list(class_map)); name=st.text_input("Full Name *"); code=st.text_input("Student ID *"); roll=st.text_input("Roll No."); dob=st.date_input("Date of Birth",value=date(2010,1,1),min_value=date(1995,1,1),max_value=date.today()); email=st.text_input("Student Email (optional)")
            st.markdown("**Parent / Guardian Information**"); f=st.text_input("Father / Guardian Name"); fp=st.text_input("Father / Guardian Phone"); fe=st.text_input("Father / Guardian Email"); m=st.text_input("Mother / Guardian Name"); mp=st.text_input("Mother / Guardian Phone"); me=st.text_input("Mother / Guardian Email")
            st.markdown("**🔒 Private Details**"); addr=st.text_area("Home Address"); blood=st.selectbox("Blood Group",["Unknown","A+","A-","B+","B-","AB+","AB-","O+","O-"]); en=st.text_input("Emergency Contact Name"); er=st.text_input("Relationship"); ep=st.text_input("Emergency Phone"); notes=st.text_area("Notes")
            ok=st.form_submit_button("Send Student Registration",type="primary")
        if ok:
            if not name.strip() or not code.strip(): st.error("Name and Student ID are required.")
            elif one("SELECT 1 FROM students WHERE school_id=? AND student_code=?",(sid,code.strip())): st.error("That Student ID is already registered or pending.")
            else:
                cid=class_map[cln]['id']; status='approved' if can_admin else 'pending'; stid=execute("INSERT INTO students(school_id,class_id,student_code,name,roll_no,dob,email,father_name,father_phone,father_email,mother_name,mother_phone,mother_email,address,blood_group,emergency_name,emergency_relation,emergency_phone,notes,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(sid,cid,code.strip(),name.strip(),roll,dob.isoformat(),email,f,fp,fe,m,mp,me,addr,blood,en,er,ep,notes,status,datetime.now().isoformat(timespec="seconds")))
                if status=='pending': execute("INSERT INTO approvals(school_id,kind,target_id,title,detail,created_at) VALUES(?,?,?,?,?,?)",(sid,"student",stid,f"Student registration: {name}",f"ID {code} • Class {cln}",datetime.now().isoformat(timespec="seconds"))); st.success("Sent for school-admin approval.")
                else: st.success("Student created. Now capture the 30 face samples below.")
        approved=rows("SELECT id,name,student_code FROM students WHERE school_id=? AND status='approved' AND face_registered=0 ORDER BY name",(sid,));
        if approved:
            st.divider(); st.subheader("📸 30-Sample Face Registration"); labels={f"{x['name']} • {x['student_code']}":x for x in approved}; lab=st.selectbox("Student to enroll",list(labels)); ctx=webrtc_streamer(key="enroll",mode=WebRtcMode.SENDRECV,video_processor_factory=EnrollmentCamera,media_stream_constraints={"video":True,"audio":False},async_processing=True)
            if st.button("💾 Save 30 Face Samples"):
                p=ctx.video_processor; s=labels[lab]
                if not p or len(p.samples)<ENROLLMENT_SAMPLES: st.warning(f"Capture all {ENROLLMENT_SAMPLES} samples first.")
                else:
                    folder=sample_dir(sid,s['id']); os.makedirs(folder,exist_ok=True)
                    for i,img in enumerate(p.samples[:ENROLLMENT_SAMPLES],1): cv2.imwrite(os.path.join(folder,f"{i:02d}.jpg"),img)
                    execute("UPDATE students SET face_registered=1 WHERE id=?",(s['id'],)); st.success("Face registration complete.")
    elif page=="📋 Smart Attendance":
        if not classes: st.warning("No classes."); return
        cln=st.selectbox("Class",list(class_map)); cid=class_map[cln]['id']; okday,why=school_day(sid)
        if not okday: st.warning(f"Attendance disabled: {why}"); return
        db=student_embeddings(sid,cid); st.info("Individual mode: keep one student in view. Use Scan Class for multiple students.")
        ctx=webrtc_streamer(key="individual",mode=WebRtcMode.SENDRECV,video_processor_factory=SnapshotCamera,media_stream_constraints={"video":True,"audio":False},async_processing=True)
        if st.button("🔍 Recognize Student",type="primary"):
            p=ctx.video_processor
            if not p or p.latest is None: st.warning("Start camera first.")
            else:
                img=p.latest.copy(); faces=face_detector.detectMultiScale(cv2.cvtColor(img,cv2.COLOR_BGR2GRAY),1.15,7,minSize=(120,120)) if face_detector is not None else []
                if len(faces)!=1: st.warning("Keep exactly one face in view.")
                else:
                    stud,dist=recognize_face(crop(img,faces[0]),db)
                    if stud: mark_present(sid,cid,stud,"Individual Scan",uid); st.success(f"Present: {db[stud]['name']} • {db[stud]['code']}")
                    else: st.error("UNKNOWN — no attendance saved.")
    elif page=="📸 Scan Class":
        if not classes: st.warning("No classes."); return
        cln=st.selectbox("Class",list(class_map),key="scanclass"); cid=class_map[cln]['id']; okday,why=school_day(sid)
        if not okday: st.warning(f"Class Scan disabled: {why}"); return
        st.info("Teacher-controlled: start camera, get the class in view, then click Scan Class Now. Nothing is saved until you confirm.")
        ctx=webrtc_streamer(key="classscan",mode=WebRtcMode.SENDRECV,video_processor_factory=SnapshotCamera,media_stream_constraints={"video":True,"audio":False},async_processing=True)
        if st.button("📸 Scan Class Now",type="primary"):
            p=ctx.video_processor
            if not p or p.latest is None: st.warning("Start camera first.")
            else:
                img=p.latest.copy(); faces=face_detector.detectMultiScale(cv2.cvtColor(img,cv2.COLOR_BGR2GRAY),1.12,6,minSize=(90,90)) if face_detector is not None else []; db=student_embeddings(sid,cid); found=[]; unknown=0
                for b in faces:
                    stud,dist=recognize_face(crop(img,b),db)
                    if stud and stud not in found: found.append(stud)
                    elif not stud: unknown+=1
                st.session_state.scan_results={"class_id":cid,"found":found,"unknown":unknown,"at":datetime.now().isoformat(timespec="seconds")}
        sr=st.session_state.get("scan_results")
        if sr and sr['class_id']==cid:
            allst=approved_students(sid,cid); found=set(sr['found']); missing=[x for x in allst if x['id'] not in found]
            a,b,c=st.columns(3); a.metric("Class Strength",len(allst)); b.metric("Recognized",len(found)); c.metric("Missing",len(missing))
            if missing: st.markdown(f'<div class="ev-warn">⚠️ <b>{len(missing)} student(s) missing</b> — review before confirming.</div>',unsafe_allow_html=True)
            st.write("**Recognized:**",", ".join(x['name'] for x in allst if x['id'] in found) or "None")
            st.write("**Not detected:**",", ".join(f"{x['name']} ({x['student_code']})" for x in missing) or "None")
            if sr['unknown']: st.warning(f"{sr['unknown']} unknown face(s) detected; they will not be added.")
            st.caption("Teacher review: tick any registered student the camera missed before confirming.")
            manual=st.multiselect("Add students manually after checking",[f"{x['name']} • {x['student_code']}" for x in missing]); mapm={f"{x['name']} • {x['student_code']}":x['id'] for x in missing}; final=found|{mapm[x] for x in manual}
            x,y=st.columns(2)
            if x.button("✅ Confirm Attendance",type="primary"):
                execute("INSERT OR IGNORE INTO class_sessions(school_id,class_id,day,confirmed_by,created_at) VALUES(?,?,?,?,?)",(sid,cid,date.today().isoformat(),uid,datetime.now().isoformat(timespec="seconds")))
                for student_id in final: mark_present(sid,cid,student_id,"Whole-Class Scan",uid)
                st.success(f"Attendance confirmed: {len(final)}/{len(allst)} present • {len(allst)-len(final)} absent."); st.session_state.scan_results=None
            if y.button("🔄 Discard / Rescan"): st.session_state.scan_results=None; st.rerun()
    elif page=="🧠 AI Classroom Monitor":
        if not classes: st.warning("No classes."); return
        cln=st.selectbox("Class",list(class_map),key="monitorclass"); cid=class_map[cln]['id']; strength=len(approved_students(sid,cid)); pres=len(today_present(sid,cid)); teacher=one("SELECT u.name FROM classes c LEFT JOIN users u ON u.id=c.class_teacher_user_id WHERE c.id=?",(cid,)); teacher_name=teacher['name'] if teacher and teacher['name'] else "Not assigned"
        ctx=webrtc_streamer(key="occupancy",mode=WebRtcMode.SENDRECV,video_processor_factory=OccupancyCamera,media_stream_constraints={"video":True,"audio":False},async_processing=True)
        p=ctx.video_processor; inside=p.inside if p else 0; entered=p.entered if p else 0; exited=p.exited if p else 0
        a,b,c,d,e=st.columns(5); a.metric("👥 Students Inside",f"{inside}/{strength}"); b.metric("⚠️ Missing",max(0,strength-pres)); c.metric("👨‍🏫 Teacher",teacher_name); d.metric("🚪 Entry / Exit",f"{entered} / {exited}"); e.metric("🟢 Class Status","ACTIVE" if inside else "WAITING / EMPTY")
        st.caption("Teacher presence should be treated as 'not detected' rather than proof of absence; staff should verify before acting.")
    elif page=="📅 Calendar":
        st.subheader(datetime.now().strftime("%B %Y")); st.code(calendar.month(datetime.now().year,datetime.now().month))
        hs=rows("SELECT * FROM holidays WHERE school_id=? ORDER BY day",(sid,)); st.dataframe(pd.DataFrame([dict(x) for x in hs])[['day','name']] if hs else pd.DataFrame(columns=['day','name']),use_container_width=True,hide_index=True)
        if can_admin:
            with st.form("holiday"):
                d=st.date_input("Holiday date"); n=st.text_input("Holiday name"); ok=st.form_submit_button("Add Holiday")
            if ok and n:
                execute("INSERT OR REPLACE INTO holidays(school_id,day,name) VALUES(?,?,?)",(sid,d.isoformat(),n)); st.rerun()
    elif page=="📊 Reports":
        data=rows("SELECT a.day,a.time,c.name class,s.student_code,s.name student,a.status,a.method FROM attendance a JOIN students s ON s.id=a.student_id JOIN classes c ON c.id=a.class_id WHERE a.school_id=? ORDER BY a.day DESC,a.time DESC",(sid,)); df=pd.DataFrame([dict(x) for x in data]); st.dataframe(df,use_container_width=True,hide_index=True) if not df.empty else st.info("No attendance yet.");
        if not df.empty: st.download_button("⬇️ Export CSV",df.to_csv(index=False),"EduVision_Attendance.csv","text/csv")
    elif page=="🛡️ Student Approvals":
        aps=rows("SELECT * FROM approvals WHERE school_id=? AND status='pending' AND kind='student' ORDER BY id DESC",(sid,));
        if not aps: st.success("No pending student requests.")
        for a in aps:
            with st.expander(a['title']):
                st.write(a['detail']); x,y=st.columns(2)
                if x.button("✅ Approve",key=f"sap{a['id']}"):
                    table="students"; execute("UPDATE students SET status='approved' WHERE id=?",(a['target_id'],)); execute("UPDATE approvals SET status='approved',reviewed_at=?,reviewed_by=? WHERE id=?",(datetime.now().isoformat(timespec="seconds"),uid,a['id'])); st.rerun()
                if y.button("❌ Decline",key=f"sde{a['id']}"):
                    table="students"; execute("UPDATE students SET status='declined' WHERE id=?",(a['target_id'],)); execute("UPDATE approvals SET status='declined',reviewed_at=?,reviewed_by=? WHERE id=?",(datetime.now().isoformat(timespec="seconds"),uid,a['id'])); st.rerun()
    elif page=="👨‍🏫 Staff Accounts":
        us=rows("SELECT * FROM users WHERE school_id=? AND role='teacher' ORDER BY name",(sid,));
        for u in us:
            if st.button(f"{u['user_code']} • {u['name']} • {u['status']}",key=f"staff{u['id']}",use_container_width=True): st.session_state.staff_manage=u['id']
        mid=st.session_state.get("staff_manage")
        if mid:
            u=one("SELECT * FROM users WHERE id=? AND school_id=?",(mid,sid)); st.subheader(u['name']); x,y=st.columns(2)
            if x.button("🔑 Reset Password",key="schoolreset"):
                temp="EV-"+secrets.token_hex(3).upper(); execute("UPDATE users SET password_hash=?,force_password_change=1 WHERE id=?",(hpass(temp),mid)); st.success(f"Temporary password: **{temp}**")
            if y.button("🚫 Disable" if u['status']!='disabled' else "✅ Enable",key="schooldisable"): execute("UPDATE users SET status=? WHERE id=?",("disabled" if u['status']!='disabled' else "approved",mid)); st.rerun()
        st.caption("School admins cannot create or approve other school admins. Only the EduVision Super Admin can approve admin applications.")
    elif page=="📢 Announcements":
        with st.form("ann"):
            t=st.text_input("Title"); body=st.text_area("Announcement"); ok=st.form_submit_button("Publish")
        if ok and t: execute("INSERT INTO announcements(school_id,title,body,created_at) VALUES(?,?,?,?)",(sid,t,body,datetime.now().isoformat(timespec="seconds"))); st.rerun()
        aa=rows("SELECT * FROM announcements WHERE school_id=? ORDER BY id DESC",(sid,));
        for a in aa: st.subheader(a['title']); st.write(a['body'])

# -------------------- ROUTER --------------------
if st.session_state.auth:
    if st.session_state.role=="super_admin": super_dashboard()
    else: school_app()
else:
    v=st.session_state.view
    if v=="home": public_home()
    elif v=="register_school": register_school()
    elif v=="admin_apply": admin_apply()
    elif v=="super_login": super_login()
    elif v=="school_login": school_login()
    elif v=="guest": guest_page()
    else: st.session_state.view="home"; st.rerun()
