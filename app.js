const C = window.EDUVISION_CONFIG || {};
const ok =
    C.SUPABASE_URL &&
    !C.SUPABASE_URL.includes("PASTE_");

const db = ok
    ? supabase.createClient(
        C.SUPABASE_URL,
        C.SUPABASE_ANON_KEY
    )
    : null;

const $ = s => document.querySelector(s);

let S = JSON.parse(
    localStorage.getItem("evs") || "null"
);


/* =========================================
   HELPERS
========================================= */

const f = (l, n, t = "text") => `
<div class="field">
    <label>${l}</label>
    <input required name="${n}" type="${t}">
</div>
`;

async function h(s) {
    const b = await crypto.subtle.digest(
        "SHA-256",
        new TextEncoder().encode(s)
    );

    return [...new Uint8Array(b)]
        .map(x => x.toString(16).padStart(2, "0"))
        .join("");
}

function vals() {
    return Object.fromEntries(
        [...$("#form").querySelectorAll("input")]
            .map(x => [x.name, x.value])
    );
}

function msg(x) {
    $("#msg").textContent = x;
}


/* =========================================
   LOGIN / REGISTER
========================================= */

function login(m) {

    $("#home").classList.add("hidden");
    $("#login").classList.remove("hidden");

    const F = $("#form");

    $("#msg").textContent = "";


    /* SCHOOL ADMIN */

    if (m === "admin") {

        $("#lt").textContent = "School Admin Login";

        F.innerHTML =
            f("School ID", "school") +
            f("Admin ID", "id") +
            f("Password", "pw", "password") +
            "<button>Sign In</button>";

        F.querySelector("button").onclick = async () => {

            if (!db) {
                return msg(
                    "Configure Supabase in config.js"
                );
            }

            const a = vals();

            const { data } = await db
                .from("schools")
                .select("*")
                .eq("school_id", a.school)
                .eq("admin_id", a.id)
                .maybeSingle();

            if (
                !data ||
                data.approval_status !== "Approved" ||
                await h(a.pw) !== data.admin_password_hash
            ) {
                return msg(
                    "Login failed or school not approved."
                );
            }

            loginSuccess({
                role: "School Admin",
                school: data.school_id,
                name: data.school_name
            });
        };
    }


    /* TEACHER */

    if (m === "teacher") {

        $("#lt").textContent = "Teacher Login";

        F.innerHTML =
            f("School ID", "school") +
            f("Teacher ID", "id") +
            f("Password", "pw", "password") +
            "<button>Sign In</button>";

        F.querySelector("button").onclick = async () => {

            if (!db) {
                return msg(
                    "Configure Supabase in config.js"
                );
            }

            const a = vals();

            const { data } = await db
                .from("teachers")
                .select("*")
                .eq("school_id", a.school)
                .eq("teacher_id", a.id)
                .maybeSingle();

            if (
                !data ||
                !data.enabled ||
                await h(a.pw) !== data.password_hash
            ) {
                return msg("Teacher login failed.");
            }

            loginSuccess({
                role: "Teacher",
                school: data.school_id,
                name: data.teacher_name
            });
        };
    }


    /* EDUVISION ADMIN */

    if (m === "evadmin") {

        $("#lt").textContent = "EduVision Admin";

        F.innerHTML =
            f("Admin ID", "admin_id") +
            f("Password", "password", "password") +
            "<button>Sign In</button>";

        F.querySelector("button").onclick = async () => {

            const r = await fetch(
                "/api/admin-login",
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body: JSON.stringify(vals())
                }
            );

            if (!r.ok) {
                return msg("Incorrect login.");
            }

            loginSuccess({
                role: "EduVision Admin",
                name: "EduVision Admin"
            });
        };
    }


    /* REGISTER SCHOOL */

    if (m === "register") {

        $("#lt").textContent = "Register School";

        F.innerHTML =
            f("School Name", "name") +
            f("School ID", "school") +
            f("Admin ID", "id") +
            f("Password", "pw", "password") +
            "<button>Register</button>";

        F.querySelector("button").onclick = async () => {

            if (!db) {
                return msg(
                    "Configure Supabase in config.js"
                );
            }

            const a = vals();

            const { error } = await db
                .from("schools")
                .insert({
                    school_name: a.name,
                    school_id: a.school,
                    admin_id: a.id,
                    admin_password_hash:
                        await h(a.pw),
                    approval_status: "Pending"
                });

            msg(
                error
                    ? error.message
                    : "Registration submitted for approval."
            );
        };
    }
}


/* =========================================
   SUCCESSFUL LOGIN

   Save account then FORCE a clean reload.
========================================= */

function loginSuccess(s) {

    localStorage.setItem(
        "evs",
        JSON.stringify(s)
    );

    window.location.reload();
}


/* =========================================
   START DASHBOARD
========================================= */

function start(s) {

    S = s;

    /*
       IMPORTANT:
       Explicitly hide landing + login separately.
       This prevents the login screen from remaining
       above the dashboard.
    */

    const home = $("#home");
    const loginScreen = $("#login");
    const app = $("#app");

    if (home) {
        home.classList.add("hidden");
        home.style.display = "none";
    }

    if (loginScreen) {
        loginScreen.classList.add("hidden");
        loginScreen.style.display = "none";
    }

    if (app) {
        app.classList.remove("hidden");
        app.style.display = "grid";
    }


    $("#who").innerHTML = `
        <b>${s.name}</b><br>
        ${s.role}
    `;


    let a;


    if (s.role === "EduVision Admin") {

        a = [
            "Dashboard",
            "Schools"
        ];

    } else if (s.role === "School Admin") {

        a = [
            "Dashboard",
            "Students",
            "Teachers",
            "Smart Attendance",
            "Smart Occupancy",
            "Reports",
            "Settings"
        ];

    } else {

        a = [
            "Dashboard",
            "Students",
            "Smart Attendance",
            "Smart Occupancy",
            "Reports"
        ];
    }


    $("#nav").innerHTML = a
        .map(x => `
            <button onclick="page('${x}')">
                <span>${x}</span>
            </button>
        `)
        .join("");


    page("Dashboard");
}


/* =========================================
   LOGOUT
========================================= */

function logout() {

    localStorage.removeItem("evs");

    window.location.reload();
}


/* =========================================
   DATABASE COUNT
========================================= */

async function cnt(t, k, v) {

    let q = db
        .from(t)
        .select("*", {
            count: "exact",
            head: true
        });

    if (S.school) {
        q = q.eq(
            "school_id",
            S.school
        );
    }

    if (k) {
        q = q.eq(k, v);
    }

    const r = await q;

    return r.count || 0;
}


/* =========================================
   PAGE ROUTER
========================================= */

async function page(n) {

    $("#title").textContent = n;

    const P = $("#page");

    P.innerHTML =
        "<div class='box'>Loading…</div>";


    /* DASHBOARD */

    if (n === "Dashboard") {

        if (S.role === "EduVision Admin") {

            P.innerHTML = stats([
                [
                    "Pending Schools",
                    await cnt(
                        "schools",
                        "approval_status",
                        "Pending"
                    )
                ],
                [
                    "Approved Schools",
                    await cnt(
                        "schools",
                        "approval_status",
                        "Approved"
                    )
                ],
                ["Platform", "Online"],
                ["Role", "Admin"]
            ]);

            return;
        }


        const d = new Date()
            .toISOString()
            .slice(0, 10);


        P.innerHTML = stats([
            [
                "Active Students",
                await cnt(
                    "students",
                    "status",
                    "Active"
                )
            ],
            [
                "Teachers",
                await cnt(
                    "teachers",
                    "enabled",
                    true
                )
            ],
            [
                "Marked Today",
                await cnt(
                    "attendance",
                    "attendance_date",
                    d
                )
            ],
            [
                "System",
                "Online"
            ]
        ]);

        return;
    }


    if (n === "Students") {
        students();
        return;
    }

    if (n === "Teachers") {
        teachers();
        return;
    }

    if (n === "Smart Attendance") {
        attendance();
        return;
    }

    if (n === "Smart Occupancy") {
        occupancy();
        return;
    }

    if (n === "Reports") {
        reports();
        return;
    }

    if (n === "Schools") {
        schools();
        return;
    }

    if (n === "Settings") {

        P.innerHTML = `
        <div class="box">
            <h3>School Settings</h3>

            <p class="muted">
                School ID: ${S.school}
            </p>
        </div>
        `;
    }
}


/* =========================================
   DASHBOARD CARDS
========================================= */

function stats(a) {

    return `
    <div class="stats">

        ${a.map(x => `
            <div class="box">

                <span class="muted">
                    ${x[0]}
                </span>

                <b>
                    ${x[1]}
                </b>

            </div>
        `).join("")}

    </div>
    `;
}


/* =========================================
   STUDENTS
========================================= */

async function students() {

    const { data = [] } = await db
        .from("students")
        .select("*")
        .eq(
            "school_id",
            S.school
        )
        .order(
            "created_at",
            {
                ascending: false
            }
        );


    $("#page").innerHTML = `

    ${
        S.role === "School Admin"

        ? `
        <div class="tools">

            <input
                id="si"
                placeholder="Student ID"
            >

            <input
                id="sn"
                placeholder="Name"
            >

            <input
                id="sc"
                placeholder="Class"
            >

            <input
                id="sr"
                placeholder="Roll No"
            >

            <button onclick="addStudent()">
                Add Student
            </button>

        </div>
        `

        : ""
    }


    <div class="table">

        <table>

            <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Class</th>
                <th>Roll</th>
                <th>Status</th>
            </tr>


            ${data.map(x => `

                <tr>

                    <td>
                        ${x.student_id}
                    </td>

                    <td>
                        ${x.name}
                    </td>

                    <td>
                        ${x.class_name}
                    </td>

                    <td>
                        ${x.roll_no}
                    </td>

                    <td>
                        ${x.status}
                    </td>

                </tr>

            `).join("")}

        </table>

    </div>
    `;
}


async function addStudent() {

    const { error } = await db
        .from("students")
        .insert({

            school_id:
                S.school,

            student_id:
                $("#si").value,

            name:
                $("#sn").value,

            class_name:
                $("#sc").value,

            roll_no:
                $("#sr").value,

            status:
                "Active"
        });


    alert(
        error
            ? error.message
            : "Student added"
    );


    students();
}


/* =========================================
   TEACHERS
========================================= */

async function teachers() {

    const { data = [] } = await db
        .from("teachers")
        .select("*")
        .eq(
            "school_id",
            S.school
        );


    $("#page").innerHTML = `

    <div class="tools">

        <input
            id="ti"
            placeholder="Teacher ID"
        >

        <input
            id="tn"
            placeholder="Name"
        >

        <input
            id="tp"
            type="password"
            placeholder="Password"
        >

        <button onclick="addTeacher()">
            Add Teacher
        </button>

    </div>


    <div class="table">

        <table>

            <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Status</th>
            </tr>


            ${data.map(x => `

                <tr>

                    <td>
                        ${x.teacher_id}
                    </td>

                    <td>
                        ${x.teacher_name}
                    </td>

                    <td>
                        ${x.enabled
                            ? "Active"
                            : "Disabled"}
                    </td>

                </tr>

            `).join("")}

        </table>

    </div>
    `;
}


async function addTeacher() {

    const { error } = await db
        .from("teachers")
        .insert({

            school_id:
                S.school,

            teacher_id:
                $("#ti").value,

            teacher_name:
                $("#tn").value,

            password_hash:
                await h(
                    $("#tp").value
                ),

            enabled:
                true
        });


    alert(
        error
            ? error.message
            : "Teacher added"
    );


    teachers();
}


/* =========================================
   CAMERA
========================================= */

async function cam(id) {

    try {

        const s =
            await navigator.mediaDevices
                .getUserMedia({
                    video: true
                });


        $("#" + id).innerHTML =
            "<video autoplay playsinline muted></video>";


        $("#" + id + " video")
            .srcObject = s;

    } catch {

        alert(
            "Camera permission needed"
        );
    }
}


/* =========================================
   SMART ATTENDANCE
========================================= */

async function attendance() {

    const { data = [] } = await db
        .from("students")
        .select("*")
        .eq(
            "school_id",
            S.school
        )
        .eq(
            "status",
            "Active"
        );


    $("#page").innerHTML = `

    <div
        class="camera"
        id="cam"
    >
        Smart Attendance Camera
    </div>


    <div class="tools">

        <button onclick="cam('cam')">
            Start Camera
        </button>


        <select id="stu">

            ${data.map(x => `
                <option value="${x.student_id}">
                    ${x.name} — ${x.student_id}
                </option>
            `).join("")}

        </select>


        <select id="st">

            <option>
                Present
            </option>

            <option>
                Late
            </option>

            <option>
                Absent
            </option>

        </select>


        <button onclick="mark()">
            Save Attendance
        </button>

    </div>


    <div class="box">

        <p class="muted">

            Browser camera works here.
            Automatic face recognition from
            the old OpenCV model needs the
            separate AI conversion step.

        </p>

    </div>
    `;
}


/* =========================================
   SAVE ATTENDANCE
========================================= */

async function mark() {

    const id =
        $("#stu").value;


    const { data: s } = await db
        .from("students")
        .select("*")
        .eq(
            "school_id",
            S.school
        )
        .eq(
            "student_id",
            id
        )
        .single();


    const d =
        new Date();


    const row = {

        school_id:
            S.school,

        student_id:
            id,

        name:
            s.name,

        class_name:
            s.class_name,

        attendance_date:
            d.toISOString().slice(0, 10),

        attendance_time:
            d.toLocaleTimeString(),

        status:
            $("#st").value
    };


    const { error } = await db
        .from("attendance")
        .upsert(
            row,
            {
                onConflict:
                    "school_id,student_id,attendance_date"
            }
        );


    alert(
        error
            ? error.message
            : "Attendance saved"
    );
}


/* =========================================
   SMART OCCUPANCY
========================================= */

function occupancy() {

    $("#page").innerHTML = `

    <div
        class="camera"
        id="occ"
    >
        Live Classroom
    </div>


    <div class="tools">

        <button onclick="cam('occ')">
            Start Camera
        </button>

    </div>


    <div class="box">

        <b>
            Current Occupancy: —
        </b>

        <p class="muted">

            Automatic YOLO person counting
            needs the separate AI backend
            conversion.

        </p>

    </div>
    `;
}


/* =========================================
   REPORTS
========================================= */

async function reports() {

    const { data = [] } = await db
        .from("attendance")
        .select("*")
        .eq(
            "school_id",
            S.school
        )
        .order(
            "attendance_date",
            {
                ascending: false
            }
        )
        .limit(200);


    $("#page").innerHTML = `

    <div class="table">

        <table>

            <tr>
                <th>Date</th>
                <th>Name</th>
                <th>Class</th>
                <th>Status</th>
            </tr>


            ${data.map(x => `

                <tr>

                    <td>
                        ${x.attendance_date}
                    </td>

                    <td>
                        ${x.name}
                    </td>

                    <td>
                        ${x.class_name}
                    </td>

                    <td>
                        ${x.status}
                    </td>

                </tr>

            `).join("")}

        </table>

    </div>
    `;
}


/* =========================================
   EDUVISION ADMIN — SCHOOLS
========================================= */

async function schools() {

    const { data = [] } = await db
        .from("schools")
        .select("*")
        .order(
            "created_at",
            {
                ascending: false
            }
        );


    $("#page").innerHTML = `

    <div class="table">

        <table>

            <tr>
                <th>ID</th>
                <th>School</th>
                <th>Status</th>
                <th>Action</th>
            </tr>


            ${data.map(x => `

                <tr>

                    <td>
                        ${x.school_id}
                    </td>

                    <td>
                        ${x.school_name}
                    </td>

                    <td>
                        ${x.approval_status}
                    </td>

                    <td>

                        <button
                            onclick="school(
                                '${x.school_id}',
                                'Approved'
                            )"
                        >
                            Approve
                        </button>

                        <button
                            onclick="school(
                                '${x.school_id}',
                                'Rejected'
                            )"
                        >
                            Reject
                        </button>

                    </td>

                </tr>

            `).join("")}

        </table>

    </div>
    `;
}


/* =========================================
   APPROVE / REJECT SCHOOL
========================================= */

async function school(id, s) {

    await db
        .from("schools")
        .update({

            approval_status:
                s,

            approved_at:
                s === "Approved"
                    ? new Date().toISOString()
                    : null,

            approved_by:
                "EduVision Admin"

        })
        .eq(
            "school_id",
            id
        );


    schools();
}


/* =========================================
   RESTORE LOGIN AFTER REFRESH

   This is what makes:
   LOGIN → REFRESH → DASHBOARD
========================================= */

if (S) {

    start(S);

} else {

    const app = $("#app");

    if (app) {
        app.classList.add("hidden");
        app.style.display = "none";
    }
}
