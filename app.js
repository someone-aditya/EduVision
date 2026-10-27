
const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];
const app = $("#app");
const cfg = window.EDUVISION_CONFIG || {};
let supabase = null;

const state = {
  screen: "welcome",
  role: null,
  schoolId: null,
  schoolName: null,
  userId: null,
  userName: null,
  page: "Dashboard",
  platformToken: null
};

function toast(message, type="info"){
  const el=$("#toast"); el.textContent=message; el.style.display="block";
  el.style.borderColor=type==="error"?"#7f1d1d":type==="ok"?"#166534":"#334155";
  clearTimeout(window.__toastTimer); window.__toastTimer=setTimeout(()=>el.style.display="none",3500);
}
function esc(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]))}
async function sha256(text){
  const data=new TextEncoder().encode(String(text));
  const digest=await crypto.subtle.digest("SHA-256",data);
  return [...new Uint8Array(digest)].map(b=>b.toString(16).padStart(2,"0")).join("");
}
function randomSchoolId(){
  const a=new Uint8Array(3); crypto.getRandomValues(a);
  return "SCH-"+[...a].map(x=>x.toString(16).padStart(2,"0")).join("").toUpperCase();
}
function initSupabase(){
  if(!window.supabase) return false;
  if(!cfg.SUPABASE_URL || !cfg.SUPABASE_ANON_KEY || cfg.SUPABASE_URL.includes("PASTE_")) return false;
  supabase=window.supabase.createClient(cfg.SUPABASE_URL.replace(/\/rest\/v1\/?$/,"").replace(/\/$/,""),cfg.SUPABASE_ANON_KEY);
  return true;
}
function needDb(){ if(!supabase){toast("Add your Supabase URL and anon key in config.js","error"); return false} return true }
function hero(kicker,title,subtitle){
  return `<section class="hero"><div class="kicker">${esc(kicker)}</div><h1>${esc(title)}</h1>${subtitle?`<p class="muted">${esc(subtitle)}</p>`:""}</section>`;
}
function card(title,text){
  return `<section class="card"><h2>${esc(title)}</h2>${text?`<p class="muted">${esc(text)}</p>`:""}</section>`;
}
function go(screen){state.screen=screen;render()}
function resetLogin(){state.role=state.schoolId=state.schoolName=state.userId=state.userName=state.platformToken=null;state.page="Dashboard"}

async function render(){
  if(state.screen==="welcome") return renderWelcome();
  if(state.screen==="portal") return renderPortal();
  if(state.screen==="schoolPortal") return renderSchoolPortal();
  if(state.screen==="schoolLogin") return renderSchoolLogin();
  if(state.screen==="platformLogin") return renderPlatformLogin();
  if(state.screen==="platformAdmin") return renderPlatformAdmin();
  if(state.screen==="schoolApp") return renderSchoolApp();
}

function renderWelcome(){
  app.innerHTML=`<main class="center-page">${hero("AI • SMART CLASSROOM","EduVision","Smarter classrooms through fast attendance, classroom monitoring and simple management.")}
  <div class="notice">● System Online</div><button class="btn full" id="enter">Enter EduVision →</button></main>`;
  $("#enter").onclick=()=>go("portal");
}
function renderPortal(){
  app.innerHTML=`<main class="center-page">${hero("SMART CLASSROOM PLATFORM","EduVision","Choose your workspace.")}
  <div class="grid two" style="margin-top:20px">
   <div>${card("School Portal","Attendance, students and classroom management.")}<button class="btn full" id="school">Open School Portal →</button></div>
   <div>${card("EduVision Admin","School registration and platform access.")}<button class="btn full" id="admin">Open Admin →</button></div>
  </div><div class="actions"><button class="btn secondary" id="back">← Back</button></div></main>`;
  $("#school").onclick=()=>go("schoolPortal"); $("#admin").onclick=()=>go("platformLogin"); $("#back").onclick=()=>go("welcome");
}

async function renderSchoolPortal(){
  app.innerHTML=`<main class="center-page">${hero("EDUVISION","School Portal","Register or open your school.")}
  <div class="tabs"><button class="tab active" data-tab="register">Register School</button><button class="tab" data-tab="open">Open School</button></div>
  <div id="tabBody"></div><div class="actions"><button class="btn secondary" id="back">← Back</button></div></main>`;
  $("#back").onclick=()=>go("portal");
  $$(".tab").forEach(b=>b.onclick=()=>{$$(".tab").forEach(x=>x.classList.remove("active"));b.classList.add("active");b.dataset.tab==="register"?schoolRegisterView():schoolOpenView()});
  schoolRegisterView();
}
function schoolRegisterView(){
  $("#tabBody").innerHTML=`<section class="card"><h2>Register School</h2>
  <form class="form two" id="reg">
   <label>School Name<input id="schoolName" required></label><label>Admin ID<input id="adminId" required></label>
   <label>Password<input id="pass" type="password" minlength="6" required></label><label>Confirm Password<input id="confirm" type="password" minlength="6" required></label>
   <button class="btn" type="submit">Submit Registration</button>
  </form></section>`;
  $("#reg").onsubmit=async e=>{
    e.preventDefault(); if(!needDb()) return;
    const name=$("#schoolName").value.trim(), aid=$("#adminId").value.trim(), pass=$("#pass").value, conf=$("#confirm").value;
    if(pass!==conf) return toast("Passwords do not match","error");
    const sid=randomSchoolId(), hash=await sha256(pass);
    const {error}=await supabase.from("schools").insert({school_id:sid,school_name:name,admin_id:aid,admin_password_hash:hash,approval_status:"pending"});
    if(error) return toast(error.message,"error");
    $("#tabBody").innerHTML=`<section class="card"><h2>Registration Submitted</h2><p>School ID: <b>${esc(sid)}</b></p><p>Admin ID: <b>${esc(aid)}</b></p><div class="notice">Waiting for EduVision Admin approval.</div></section>`;
  };
}
async function schoolOpenView(){
  $("#tabBody").innerHTML=`<section class="card"><h2>Open School</h2><p class="muted">Loading approved schools…</p></section>`;
  if(!needDb()) return;
  const {data,error}=await supabase.from("schools").select("school_id,school_name,approval_status");
  if(error) return $("#tabBody").innerHTML=`<div class="notice">${esc(error.message)}</div>`;
  const schools=(data||[]).filter(x=>String(x.approval_status).toLowerCase()==="approved");
  if(!schools.length) return $("#tabBody").innerHTML=`<div class="notice">No approved schools available.</div>`;
  $("#tabBody").innerHTML=`<section class="card"><h2>Open School</h2><label>School<select id="schoolSelect">${schools.map(s=>`<option value="${esc(s.school_id)}">${esc(s.school_name)} • ${esc(s.school_id)}</option>`).join("")}</select></label>
  <div class="actions"><button class="btn" id="continue">Continue →</button></div></section>`;
  $("#continue").onclick=()=>{
    const sid=$("#schoolSelect").value, s=schools.find(x=>x.school_id===sid);
    state.schoolId=sid; state.schoolName=s.school_name; go("schoolLogin");
  };
}

function renderSchoolLogin(){
  app.innerHTML=`<main class="center-page">${hero("SCHOOL WORKSPACE",state.schoolName,`School ID • ${state.schoolId}`)}
  <div class="tabs"><button class="tab active" data-tab="admin">School Admin</button><button class="tab" data-tab="teacher">Teacher</button></div>
  <div id="loginBody"></div><div class="actions"><button class="btn secondary" id="change">← Change School</button></div></main>`;
  $("#change").onclick=()=>{resetLogin();go("schoolPortal")};
  $$(".tab").forEach(b=>b.onclick=()=>{$$(".tab").forEach(x=>x.classList.remove("active"));b.classList.add("active");loginView(b.dataset.tab)});
  loginView("admin");
}
function loginView(kind){
  const isAdmin=kind==="admin";
  $("#loginBody").innerHTML=`<section class="card"><h2>${isAdmin?"School Admin":"Teacher"}</h2>
  <form class="form" id="loginForm"><label>${isAdmin?"Admin":"Teacher"} ID<input id="loginId" required></label><label>Password<input id="loginPass" type="password" required></label>
  <button class="btn" type="submit">Login →</button></form></section>`;
  $("#loginForm").onsubmit=async e=>{
    e.preventDefault(); if(!needDb()) return;
    const id=$("#loginId").value.trim(), hash=await sha256($("#loginPass").value);
    if(isAdmin){
      const {data,error}=await supabase.from("schools").select("*").eq("school_id",state.schoolId).eq("admin_id",id).maybeSingle();
      if(error||!data||data.admin_password_hash!==hash) return toast("Incorrect Admin ID or password","error");
      state.role="School Admin";state.userId=id;state.userName=`${state.schoolName} Admin`;
    }else{
      const {data,error}=await supabase.from("teachers").select("*").eq("school_id",state.schoolId).eq("teacher_id",id).maybeSingle();
      if(error||!data) return toast("Teacher account not found","error");
      if(data.enabled===false) return toast("Teacher account is disabled","error");
      if(data.password_hash!==hash) return toast("Incorrect password","error");
      state.role="Teacher";state.userId=id;state.userName=data.teacher_name||id;
    }
    state.page="Dashboard";go("schoolApp");
  };
}

function renderPlatformLogin(){
  app.innerHTML=`<main class="center-page">${hero("ADMINISTRATION","EduVision Admin","Platform management.")}
  <section class="card" style="margin-top:20px"><form class="form" id="pLogin"><label>Admin ID<input id="pid" required></label><label>Password<input id="ppass" type="password" required></label>
  <button class="btn" type="submit">Login →</button></form></section><div class="actions"><button class="btn secondary" id="back">← Back</button></div></main>`;
  $("#back").onclick=()=>go("portal");
  $("#pLogin").onsubmit=async e=>{
    e.preventDefault();
    const r=await fetch("/api/admin-login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({admin_id:$("#pid").value.trim(),password:$("#ppass").value})});
    const out=await r.json().catch(()=>({ok:false}));
    if(!r.ok||!out.ok) return toast(out.detail||"Incorrect Admin ID or password","error");
    state.role="EduVision Admin";state.userId=$("#pid").value.trim();state.platformToken=out.token;go("platformAdmin");
  };
}
async function renderPlatformAdmin(){
  app.innerHTML=`<main class="center-page">${hero("EDUVISION","Admin Dashboard","School registrations.")}
  <div id="adminData" class="notice">Loading…</div><div class="actions"><button class="btn secondary" id="logout">Log Out</button></div></main>`;
  $("#logout").onclick=()=>{resetLogin();go("portal")};
  if(!needDb()) return;
  const {data,error}=await supabase.from("schools").select("*");
  if(error) return $("#adminData").textContent=error.message;
  const schools=data||[], pending=schools.filter(s=>String(s.approval_status).toLowerCase()==="pending"),
    approved=schools.filter(s=>String(s.approval_status).toLowerCase()==="approved"),
    rejected=schools.filter(s=>["rejected","declined"].includes(String(s.approval_status).toLowerCase()));
  $("#adminData").outerHTML=`<div id="adminData"><div class="grid four">
   <div class="metric"><div class="label">PENDING</div><div class="value">${pending.length}</div></div>
   <div class="metric"><div class="label">APPROVED</div><div class="value">${approved.length}</div></div>
   <div class="metric"><div class="label">REJECTED</div><div class="value">${rejected.length}</div></div>
  </div><h2>Pending Registrations</h2><div class="grid">${pending.length?pending.map(s=>`<section class="card"><h3>${esc(s.school_name)}</h3><p class="muted">${esc(s.school_id)} • Admin ${esc(s.admin_id)}</p>
  <div class="actions"><button class="btn good schoolAction" data-id="${esc(s.school_id)}" data-status="approved">Approve</button><button class="btn danger schoolAction" data-id="${esc(s.school_id)}" data-status="rejected">Reject</button></div></section>`).join(""):`<div class="notice">No pending registrations.</div>`}</div>
  <h2>Approved Schools</h2>${table(approved.map(s=>({School:s.school_name,"School ID":s.school_id,"Admin ID":s.admin_id,Status:"Approved"})))}</div>`;
  $$(".schoolAction").forEach(b=>b.onclick=async()=>{
    const patch={approval_status:b.dataset.status};
    if(b.dataset.status==="approved"){patch.approved_by=state.userId;patch.approved_at=new Date().toISOString()}
    let {error}=await supabase.from("schools").update(patch).eq("school_id",b.dataset.id);
    if(error && b.dataset.status==="approved") ({error}=await supabase.from("schools").update({approval_status:"approved"}).eq("school_id",b.dataset.id));
    if(error) return toast(error.message,"error"); renderPlatformAdmin();
  });
}

function table(rows){
  if(!rows.length) return `<div class="notice">No records.</div>`;
  const keys=Object.keys(rows[0]);
  return `<div class="table-wrap"><table class="table"><thead><tr>${keys.map(k=>`<th>${esc(k)}</th>`).join("")}</tr></thead><tbody>${rows.map(r=>`<tr>${keys.map(k=>`<td>${esc(r[k])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}
function schoolNav(){
  const pages=state.role==="School Admin"?["Dashboard","Students","Teachers","Smart Attendance","Smart Occupancy","Reports","Settings"]:["Dashboard","Students","Smart Attendance","Smart Occupancy","Reports"];
  return `<aside class="sidebar"><div class="brand">EduVision</div><div class="kicker">SMART CLASSROOM</div>
  <div class="sidebar-card"><div class="small muted">SCHOOL</div><b>${esc(state.schoolName)}</b><div class="small muted" style="margin-top:5px">${esc(state.role)}</div></div>
  <nav class="nav">${pages.map(p=>`<button data-page="${p}" class="${state.page===p?"active":""}">${p}</button>`).join("")}</nav>
  <div class="actions"><button class="btn secondary full" id="logout">Log Out</button></div></aside>`;
}
async function renderSchoolApp(){
  app.innerHTML=`<div class="app-layout">${schoolNav()}<main class="main"><div id="page"></div></main></div>`;
  $$(".nav button").forEach(b=>b.onclick=()=>{state.page=b.dataset.page;renderSchoolApp()});
  $("#logout").onclick=()=>{resetLogin();go("schoolPortal")};
  if(state.page==="Dashboard") return dashboard();
  if(state.page==="Students") return studentsPage();
  if(state.page==="Teachers") return teachersPage();
  if(state.page==="Smart Attendance") return attendancePage();
  if(state.page==="Smart Occupancy") return occupancyPage();
  if(state.page==="Reports") return reportsPage();
  if(state.page==="Settings") return settingsPage();
}
async function fetchStudents(){
  if(!needDb()) return [];
  const {data,error}=await supabase.from("students").select("*").eq("school_id",state.schoolId);
  if(error){toast(error.message,"error");return []} return data||[];
}
async function fetchAttendance(){
  if(!needDb()) return [];
  const {data,error}=await supabase.from("attendance").select("*").eq("school_id",state.schoolId);
  if(error){toast(error.message,"error");return []} return data||[];
}
function activeStudents(rows){return rows.filter(x=>!["pending","declined","rejected"].includes(String(x.status||"active").toLowerCase()))}
async function dashboard(){
  const [students,att]=await Promise.all([fetchStudents(),fetchAttendance()]), active=activeStudents(students);
  const today=new Date().toISOString().slice(0,10), tr=att.filter(x=>String(x.attendance_date)===today);
  const present=tr.filter(x=>String(x.status).toLowerCase()==="present").length, late=tr.filter(x=>String(x.status).toLowerCase()==="late").length, absent=tr.filter(x=>String(x.status).toLowerCase()==="absent").length;
  const pct=active.length?Math.round(((present+late)/active.length)*1000)/10:0;
  $("#page").innerHTML=`${hero("CLASSROOM DASHBOARD",`Good ${new Date().getHours()<12?"Morning":new Date().getHours()<17?"Afternoon":"Evening"}, ${state.userName}`,state.schoolName)}
  <div class="grid four" style="margin-top:18px"><div class="metric"><div class="label">STUDENTS</div><div class="value">${active.length}</div></div><div class="metric"><div class="label">PRESENT</div><div class="value">${present}</div></div><div class="metric"><div class="label">ABSENT</div><div class="value">${absent}</div></div><div class="metric"><div class="label">ATTENDANCE</div><div class="value">${pct}%</div></div></div>
  <h2>Quick Actions</h2><div class="grid two"><section class="card"><h2>Smart Attendance</h2><p class="muted">Fast classroom attendance.</p><button class="btn full quick" data-page="Smart Attendance">Open Attendance →</button></section><section class="card"><h2>Smart Occupancy</h2><p class="muted">Live classroom occupancy.</p><button class="btn full quick" data-page="Smart Occupancy">Open Occupancy →</button></section></div>`;
  $$(".quick").forEach(b=>b.onclick=()=>{state.page=b.dataset.page;renderSchoolApp()});
}
async function studentsPage(){
  const rows=await fetchStudents(), active=activeStudents(rows), pending=rows.filter(x=>String(x.status).toLowerCase()==="pending");
  $("#page").innerHTML=`${hero("SCHOOL","Students","Student management.")}
  <div class="grid two" style="margin-top:18px"><div class="metric"><div class="label">ACTIVE</div><div class="value">${active.length}</div></div><div class="metric"><div class="label">PENDING</div><div class="value">${pending.length}</div></div></div>
  ${state.role==="Teacher"?`<section class="card" style="margin-top:18px"><h2>Register Student</h2><form class="form two" id="studentForm"><label>Student ID<input id="sid" required></label><label>Name<input id="sname" required></label><label>Class<input id="sclass" required></label><label>Roll Number<input id="sroll"></label><button class="btn" type="submit">Submit for Approval</button></form></section>`:""}
  ${state.role==="School Admin"&&pending.length?`<h2>Pending Registrations</h2>${table(pending.map(x=>({"Student ID":x.student_id,Name:x.name,Class:x.class_name,"Roll No":x.roll_no,Status:x.status})))}<div class="grid">${pending.map(x=>`<section class="card"><b>${esc(x.student_id)} • ${esc(x.name)}</b><div class="actions"><button class="btn good stuAction" data-id="${esc(x.student_id)}" data-status="Active">Approve</button><button class="btn danger stuAction" data-id="${esc(x.student_id)}" data-status="Declined">Decline</button></div></section>`).join("")}</div>`:""}
  <h2>Active Students</h2>${table(active.map(x=>({"Student ID":x.student_id,Name:x.name,Class:x.class_name,"Roll No":x.roll_no,Status:x.status||"Active"})))}`;
  if($("#studentForm")) $("#studentForm").onsubmit=async e=>{e.preventDefault();const {error}=await supabase.from("students").insert({school_id:state.schoolId,student_id:$("#sid").value.trim(),name:$("#sname").value.trim(),class_name:$("#sclass").value.trim(),roll_no:$("#sroll").value.trim(),status:"Pending"});if(error)return toast(error.message,"error");studentsPage()};
  $$(".stuAction").forEach(b=>b.onclick=async()=>{const {error}=await supabase.from("students").update({status:b.dataset.status}).eq("school_id",state.schoolId).eq("student_id",b.dataset.id);if(error)return toast(error.message,"error");studentsPage()});
}
async function teachersPage(){
  if(state.role!=="School Admin") return $("#page").innerHTML=`<div class="notice">School Admin access required.</div>`;
  const {data,error}=await supabase.from("teachers").select("*").eq("school_id",state.schoolId); if(error)return toast(error.message,"error");
  const rows=data||[];
  $("#page").innerHTML=`${hero("SCHOOL","Teachers","Teacher accounts.")}
  <section class="card" style="margin-top:18px"><h2>Create Teacher</h2><form class="form two" id="teacherForm"><label>Teacher ID<input id="tid" required></label><label>Teacher Name<input id="tname" required></label><label>Password<input id="tpass" type="password" minlength="6" required></label><button class="btn" type="submit">Create Teacher</button></form></section>
  <h2>Teacher Accounts</h2>${table(rows.map(x=>({"Teacher ID":x.teacher_id,Name:x.teacher_name,Status:x.enabled===false?"Disabled":"Enabled"})))}
  <div class="grid">${rows.map(x=>`<section class="card"><b>${esc(x.teacher_id)} • ${esc(x.teacher_name)}</b><div class="actions"><button class="btn secondary teacherToggle" data-id="${esc(x.teacher_id)}" data-enabled="${x.enabled!==false}">${x.enabled===false?"Enable":"Disable"}</button><button class="btn danger teacherDelete" data-id="${esc(x.teacher_id)}">Delete</button></div></section>`).join("")}</div>`;
  $("#teacherForm").onsubmit=async e=>{e.preventDefault();const hash=await sha256($("#tpass").value);const {error}=await supabase.from("teachers").insert({school_id:state.schoolId,teacher_id:$("#tid").value.trim(),teacher_name:$("#tname").value.trim(),password_hash:hash,enabled:true});if(error)return toast(error.message,"error");teachersPage()};
  $$(".teacherToggle").forEach(b=>b.onclick=async()=>{const {error}=await supabase.from("teachers").update({enabled:b.dataset.enabled!=="true"}).eq("school_id",state.schoolId).eq("teacher_id",b.dataset.id);if(error)return toast(error.message,"error");teachersPage()});
  $$(".teacherDelete").forEach(b=>b.onclick=async()=>{if(!confirm("Delete this teacher?"))return;const {error}=await supabase.from("teachers").delete().eq("school_id",state.schoolId).eq("teacher_id",b.dataset.id);if(error)return toast(error.message,"error");teachersPage()});
}
async function attendancePage(){
  const students=activeStudents(await fetchStudents()), att=await fetchAttendance();
  $("#page").innerHTML=`${hero("EDUVISION","Smart Attendance","Fast classroom attendance.")}
  <div class="tabs"><button class="tab active" data-at="camera">Camera</button><button class="tab" data-at="manual">Manual</button><button class="tab" data-at="records">Records</button></div><div id="attendanceBody"></div>`;
  const views={camera:()=>cameraAttendanceView(students),manual:()=>manualAttendanceView(students),records:()=>recordsAttendanceView(att)};
  $$(".tab").forEach(b=>b.onclick=()=>{$$(".tab").forEach(x=>x.classList.remove("active"));b.classList.add("active");views[b.dataset.at]()}); views.camera();
}
function cameraAttendanceView(students){
  $("#attendanceBody").innerHTML=`<section class="card"><h2>Camera Attendance</h2><p class="muted">Camera capture is ready. This Vercel edition keeps manual attendance fully working. Face identification needs your existing trained face model/data to be added to the converted project.</p>
  <video id="attendanceVideo" class="camera" autoplay playsinline muted></video><div class="actions"><button class="btn" id="startAttCam">Start Camera</button><button class="btn secondary" id="stopAttCam">Stop</button></div></section>`;
  let stream=null; $("#startAttCam").onclick=async()=>{try{stream=await navigator.mediaDevices.getUserMedia({video:true,audio:false});$("#attendanceVideo").srcObject=stream}catch(e){toast(e.message,"error")}};
  $("#stopAttCam").onclick=()=>{stream?.getTracks().forEach(t=>t.stop());$("#attendanceVideo").srcObject=null};
}
function manualAttendanceView(students){
  if(!students.length) return $("#attendanceBody").innerHTML=`<div class="notice">No active students.</div>`;
  $("#attendanceBody").innerHTML=`<section class="card"><h2>Manual Attendance</h2><form class="form two" id="manualAtt"><label>Student<select id="attStudent">${students.map(x=>`<option value="${esc(x.student_id)}">${esc(x.student_id)} • ${esc(x.name)}</option>`).join("")}</select></label><label>Status<select id="attStatus"><option>Present</option><option>Late</option><option>Absent</option></select></label><button class="btn" type="submit">Save Attendance</button></form></section>`;
  $("#manualAtt").onsubmit=async e=>{e.preventDefault();const s=students.find(x=>String(x.student_id)===$("#attStudent").value), now=new Date(), date=now.toISOString().slice(0,10), time=now.toTimeString().slice(0,8), status=$("#attStatus").value;
    const {data:existing,error:qerr}=await supabase.from("attendance").select("id").eq("school_id",state.schoolId).eq("student_id",String(s.student_id)).eq("attendance_date",date).maybeSingle();if(qerr)return toast(qerr.message,"error");
    let result;if(existing) result=await supabase.from("attendance").update({name:s.name,class_name:s.class_name,attendance_time:time,status}).eq("id",existing.id);else result=await supabase.from("attendance").insert({school_id:state.schoolId,student_id:String(s.student_id),name:s.name,class_name:s.class_name,attendance_date:date,attendance_time:time,status});
    if(result.error)return toast(result.error.message,"error");toast(`${s.name} marked ${status}`,"ok");
  };
}
function recordsAttendanceView(att){$("#attendanceBody").innerHTML=table(att.map(x=>({"Student ID":x.student_id,Name:x.name,Class:x.class_name,Date:x.attendance_date,Time:x.attendance_time,Status:x.status})))}
function occupancyPage(){
  $("#page").innerHTML=`${hero("EDUVISION","Smart Occupancy","Live classroom monitoring.")}
  <section class="card" style="margin-top:18px"><h2>Live Classroom</h2><video id="occVideo" class="camera" autoplay playsinline muted></video><div class="actions"><button class="btn" id="startOcc">Start Camera</button><button class="btn secondary" id="stopOcc">Stop</button></div><div class="notice" id="occStatus">Camera waiting.</div></section>`;
  let stream=null;$("#startOcc").onclick=async()=>{try{stream=await navigator.mediaDevices.getUserMedia({video:true,audio:false});$("#occVideo").srcObject=stream;$("#occStatus").textContent="Camera active. To restore YOLO person counting, add your current model-backed occupancy service."}catch(e){toast(e.message,"error")}};
  $("#stopOcc").onclick=()=>{stream?.getTracks().forEach(t=>t.stop());$("#occVideo").srcObject=null;$("#occStatus").textContent="Camera stopped."};
}
async function reportsPage(){
  const [students,att]=await Promise.all([fetchStudents(),fetchAttendance()]), active=activeStudents(students);
  const present=att.filter(x=>String(x.status).toLowerCase()==="present").length, late=att.filter(x=>String(x.status).toLowerCase()==="late").length, absent=att.filter(x=>String(x.status).toLowerCase()==="absent").length, pct=att.length?Math.round(((present+late)/att.length)*1000)/10:0;
  $("#page").innerHTML=`${hero("EDUVISION","Reports","Attendance overview.")}
  <div class="grid four" style="margin-top:18px"><div class="metric"><div class="label">STUDENTS</div><div class="value">${active.length}</div></div><div class="metric"><div class="label">PRESENT</div><div class="value">${present}</div></div><div class="metric"><div class="label">ABSENT</div><div class="value">${absent}</div></div><div class="metric"><div class="label">ATTENDANCE</div><div class="value">${pct}%</div></div></div><h2>Attendance Records</h2>${table(att.map(x=>({"Student ID":x.student_id,Name:x.name,Class:x.class_name,Date:x.attendance_date,Time:x.attendance_time,Status:x.status})))}`;
}
function settingsPage(){
  $("#page").innerHTML=`${hero("EDUVISION","Settings","School account.")}
  <section class="card" style="margin-top:18px"><h2>School</h2><p><b>${esc(state.schoolName)}</b></p><p class="muted">School ID • ${esc(state.schoolId)}</p><p class="muted">Role • ${esc(state.role)}</p><p class="muted">Account • ${esc(state.userName||state.userId)}</p></section>
  <section class="card" style="margin-top:18px"><h2>System</h2><div class="badge ${supabase?"good":"bad"}">${supabase?"● Database Connected":"Database not configured"}</div></section>`;
}

window.addEventListener("DOMContentLoaded",()=>{initSupabase();render()});
