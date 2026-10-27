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
   SMART ATTENDANCE GLOBALS
========================================= */

let faceModelsReady = false;
let cameraStream = null;
let attendanceTimer = null;
let attendanceBusy = false;

const markedThisSession = new Set();

const FACE_MODEL_URL =
    "https://cdn.jsdelivr.net/gh/vladmandic/face-api@1.7.12/model";


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
        .map(x =>
            x.toString(16).padStart(2, "0")
        )
        .join("");
}


function vals() {

    return Object.fromEntries(
        [...$("#form").querySelectorAll("input")]
            .map(x => [
                x.name,
                x.value
            ])
    );
}


function msg(x) {

    $("#msg").textContent = x;

}


function safe(x) {

    return String(x ?? "")
        .replace(
            /[&<>"']/g,
            c => ({
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#39;"
            }[c])
        );
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

        $("#lt").textContent =
            "School Admin Login";

        F.innerHTML =
            f("School ID", "school") +
            f("Admin ID", "id") +
            f("Password", "pw", "password") +
            "<button>Sign In</button>";


        F.querySelector("button").onclick =
            async () => {

                if (!db) {

                    return msg(
                        "Configure Supabase in config.js"
                    );

                }


                const a = vals();


                const { data } = await db
                    .from("schools")
                    .select("*")
                    .eq(
                        "school_id",
                        a.school
                    )
                    .eq(
                        "admin_id",
                        a.id
                    )
                    .maybeSingle();


                if (
                    !data ||
                    data.approval_status !==
                        "Approved" ||
                    await h(a.pw) !==
                        data.admin_password_hash
                ) {

                    return msg(
                        "Login failed or school not approved."
                    );

                }


                loginSuccess({

                    role:
                        "School Admin",

                    school:
                        data.school_id,

                    name:
                        data.school_name

                });

            };
    }



    /* TEACHER */

    if (m === "teacher") {

        $("#lt").textContent =
            "Teacher Login";


        F.innerHTML =
            f("School ID", "school") +
            f("Teacher ID", "id") +
            f(
                "Password",
                "pw",
                "password"
            ) +
            "<button>Sign In</button>";


        F.querySelector("button").onclick =
            async () => {

                if (!db) {

                    return msg(
                        "Configure Supabase in config.js"
                    );

                }


                const a = vals();


                const { data } = await db
                    .from("teachers")
                    .select("*")
                    .eq(
                        "school_id",
                        a.school
                    )
                    .eq(
                        "teacher_id",
                        a.id
                    )
                    .maybeSingle();


                if (
                    !data ||
                    !data.enabled ||
                    await h(a.pw) !==
                        data.password_hash
                ) {

                    return msg(
                        "Teacher login failed."
                    );

                }


                loginSuccess({

                    role:
                        "Teacher",

                    school:
                        data.school_id,

                    name:
                        data.teacher_name

                });

            };
    }



    /* EDUVISION ADMIN */

    if (m === "evadmin") {

        $("#lt").textContent =
            "EduVision Admin";


        F.innerHTML =
            f(
                "Admin ID",
                "admin_id"
            ) +

            f(
                "Password",
                "password",
                "password"
            ) +

            "<button>Sign In</button>";


        F.querySelector("button").onclick =
            async () => {

                const r =
                    await fetch(
                        "/api/admin-login",
                        {
                            method:
                                "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body:
                                JSON.stringify(
                                    vals()
                                )
                        }
                    );


                if (!r.ok) {

                    return msg(
                        "Incorrect login."
                    );

                }


                loginSuccess({

                    role:
                        "EduVision Admin",

                    name:
                        "EduVision Admin"

                });

            };
    }



    /* REGISTER SCHOOL */

    if (m === "register") {

        $("#lt").textContent =
            "Register School";


        F.innerHTML =
            f(
                "School Name",
                "name"
            ) +

            f(
                "School ID",
                "school"
            ) +

            f(
                "Admin ID",
                "id"
            ) +

            f(
                "Password",
                "pw",
                "password"
            ) +

            "<button>Register</button>";


        F.querySelector("button").onclick =
            async () => {

                if (!db) {

                    return msg(
                        "Configure Supabase in config.js"
                    );

                }


                const a = vals();


                const { error } =
                    await db
                        .from("schools")
                        .insert({

                            school_name:
                                a.name,

                            school_id:
                                a.school,

                            admin_id:
                                a.id,

                            admin_password_hash:
                                await h(a.pw),

                            approval_status:
                                "Pending"

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
   LOGIN SUCCESS
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


    const home =
        $("#home");

    const loginScreen =
        $("#login");

    const app =
        $("#app");


    if (home) {

        home.classList.add(
            "hidden"
        );

        home.style.display =
            "none";

    }


    if (loginScreen) {

        loginScreen.classList.add(
            "hidden"
        );

        loginScreen.style.display =
            "none";

    }


    if (app) {

        app.classList.remove(
            "hidden"
        );

        app.style.display =
            "grid";

    }


    $("#who").innerHTML = `

        <b>${safe(s.name)}</b>
        <br>

        ${safe(s.role)}

    `;


    let a;


    if (
        s.role ===
        "EduVision Admin"
    ) {

        a = [
            "Dashboard",
            "Schools"
        ];

    }

    else if (
        s.role ===
        "School Admin"
    ) {

        a = [
            "Dashboard",
            "Students",
            "Teachers",
            "Smart Attendance",
            "Smart Occupancy",
            "Reports",
            "Settings"
        ];

    }

    else {

        a = [
            "Dashboard",
            "Students",
            "Smart Attendance",
            "Smart Occupancy",
            "Reports"
        ];

    }


    $("#nav").innerHTML =
        a.map(x => `

            <button
                onclick="page('${x}')"
            >

                <span>
                    ${x}
                </span>

            </button>

        `).join("");


    page("Dashboard");

}



/* =========================================
   LOGOUT
========================================= */

function logout() {

    stopCamera();

    localStorage.removeItem(
        "evs"
    );

    window.location.reload();

}



/* =========================================
   DATABASE COUNT
========================================= */

async function cnt(
    t,
    k,
    v
) {

    let q = db
        .from(t)
        .select(
            "*",
            {
                count: "exact",
                head: true
            }
        );


    if (S.school) {

        q = q.eq(
            "school_id",
            S.school
        );

    }


    if (k) {

        q = q.eq(
            k,
            v
        );

    }


    const r =
        await q;


    return r.count || 0;

}



/* =========================================
   PAGE ROUTER
========================================= */

async function page(n) {

    stopCamera();


    $("#title").textContent =
        n;


    const P =
        $("#page");


    P.innerHTML =
        "<div class='box'>Loading…</div>";



    /* DASHBOARD */

    if (
        n === "Dashboard"
    ) {

        if (
            S.role ===
            "EduVision Admin"
        ) {

            P.innerHTML =
                stats([

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

                    [
                        "Platform",
                        "Online"
                    ],

                    [
                        "Role",
                        "Admin"
                    ]

                ]);


            return;

        }


        const d =
            new Date()
                .toISOString()
                .slice(0, 10);


        P.innerHTML =
            stats([

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


    if (
        n ===
        "Smart Attendance"
    ) {

        attendance();

        return;

    }


    if (
        n ===
        "Smart Occupancy"
    ) {

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

            <h3>
                School Settings
            </h3>

            <p class="muted">

                School ID:
                ${safe(S.school)}

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
                    ${safe(x[0])}
                </span>

                <b>
                    ${safe(x[1])}
                </b>

            </div>

        `).join("")}

    </div>

    `;

}



/* =========================================
   STUDENTS + FACE REGISTRATION
========================================= */

async function students() {

    const { data = [] } =
        await db
            .from("students")
            .select("*")
            .eq(
                "school_id",
                S.school
            )
            .order(
                "created_at",
                {
                    ascending:
                        false
                }
            );


    let registered =
        new Set();


    const faceResult =
        await db
            .from(
                "face_profiles"
            )
            .select(
                "student_id"
            )
            .eq(
                "school_id",
                S.school
            );


    if (!faceResult.error) {

        for (
            const profile
            of faceResult.data || []
        ) {

            registered.add(
                profile.student_id
            );

        }

    }


    $("#page").innerHTML = `


    ${
        S.role ===
        "School Admin"

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

            <button
                onclick="addStudent()"
            >
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

                <th>Smart Attendance</th>

            </tr>


            ${data.map(x => `

                <tr>

                    <td>
                        ${safe(
                            x.student_id
                        )}
                    </td>

                    <td>
                        ${safe(
                            x.name
                        )}
                    </td>

                    <td>
                        ${safe(
                            x.class_name
                        )}
                    </td>

                    <td>
                        ${safe(
                            x.roll_no
                        )}
                    </td>

                    <td>
                        ${safe(
                            x.status
                        )}
                    </td>

                    <td>

                    ${
                        registered.has(
                            x.student_id
                        )

                        ? `

                        <span
                            style="
                            color:#4ade80;
                            font-weight:700;
                            "
                        >
                            ✓ Face Registered
                        </span>

                        ${
                            S.role ===
                            "School Admin"

                            ? `

                            <button
                                onclick="registerFace(
                                '${safe(
                                    x.student_id
                                )}'
                                )"
                            >
                                Update
                            </button>

                            `

                            : ""
                        }

                        `

                        :

                        S.role ===
                        "School Admin"

                        ? `

                        <button
                            onclick="registerFace(
                            '${safe(
                                x.student_id
                            )}'
                            )"
                        >
                            Register Face
                        </button>

                        `

                        : `

                        <span class="muted">
                            Not Registered
                        </span>

                        `
                    }

                    </td>

                </tr>

            `).join("")}

        </table>

    </div>


    <div class="box">

        <p class="muted">

            Face registration stores a
            numerical face descriptor for
            Smart Attendance.

            Only register a student when
            appropriate school and
            parent/guardian permissions
            are in place.

        </p>

    </div>

    `;

}



/* =========================================
   ADD STUDENT
========================================= */

async function addStudent() {

    const { error } =
        await db
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
   FACE AI MODELS
========================================= */

async function loadFaceModels() {

    if (faceModelsReady) {

        return true;

    }


    const status =
        $("#faceStatus");


    if (status) {

        status.textContent =
            "Loading face recognition AI…";

    }


    try {

        await Promise.all([

            faceapi.nets
                .tinyFaceDetector
                .loadFromUri(
                    FACE_MODEL_URL
                ),

            faceapi.nets
                .faceLandmark68Net
                .loadFromUri(
                    FACE_MODEL_URL
                ),

            faceapi.nets
                .faceRecognitionNet
                .loadFromUri(
                    FACE_MODEL_URL
                )

        ]);


        faceModelsReady =
            true;


        if (status) {

            status.textContent =
                "Face recognition ready.";

        }


        return true;

    }

    catch (error) {

        console.error(
            error
        );


        if (status) {

            status.textContent =
                "Could not load face recognition models.";

        }


        return false;

    }

}



/* =========================================
   CAMERA CONTROL
========================================= */

async function openCamera(
    containerId
) {

    stopCamera();


    cameraStream =
        await navigator.mediaDevices
            .getUserMedia({

                video: {

                    facingMode:
                        "user",

                    width: {
                        ideal: 960
                    },

                    height: {
                        ideal: 540
                    }

                },

                audio:
                    false

            });


    const container =
        $("#" + containerId);


    container.innerHTML = `

        <video
            id="${containerId}Video"
            autoplay
            playsinline
            muted
            style="
            width:100%;
            max-height:520px;
            object-fit:cover;
            border-radius:14px;
            "
        ></video>

        <canvas
            id="${containerId}Canvas"
            style="
            position:absolute;
            inset:0;
            width:100%;
            height:100%;
            pointer-events:none;
            "
        ></canvas>

    `;


    container.style.position =
        "relative";


    const video =
        $("#" +
            containerId +
            "Video");


    video.srcObject =
        cameraStream;


    await video.play();


    return video;

}



function stopCamera() {

    if (attendanceTimer) {

        clearInterval(
            attendanceTimer
        );

        attendanceTimer =
            null;

    }


    attendanceBusy =
        false;


    if (cameraStream) {

        cameraStream
            .getTracks()
            .forEach(
                track =>
                    track.stop()
            );


        cameraStream =
            null;

    }

}



/* =========================================
   REGISTER FACE PAGE
========================================= */

async function registerFace(
    studentId
) {

    stopCamera();


    const { data: student } =
        await db
            .from("students")
            .select("*")
            .eq(
                "school_id",
                S.school
            )
            .eq(
                "student_id",
                studentId
            )
            .single();


    if (!student) {

        alert(
            "Student not found."
        );

        return;

    }


    $("#title").textContent =
        "Register Face";


    $("#page").innerHTML = `

    <div class="box">

        <h3>
            Register Face
        </h3>


        <p>

            <b>
                ${safe(student.name)}
            </b>

            <br>

            <span class="muted">

                ${safe(
                    student.student_id
                )}

                •

                ${safe(
                    student.class_name
                )}

            </span>

        </p>


        <p class="muted">

            Keep exactly one person
            in front of the camera.

            Look directly at the camera
            with the face clearly visible.

        </p>


        <div
            id="registerCamera"
            class="camera"
            style="
            min-height:400px;
            position:relative;
            "
        >

            Camera is off

        </div>


        <div class="tools">

            <button
                onclick="captureStudentFace(
                '${safe(studentId)}'
                )"
            >

                Start Camera & Register

            </button>


            <button
                onclick="page('Students')"
            >

                Cancel

            </button>

        </div>


        <div
            id="faceStatus"
            class="box"
        >

            Ready to register.

        </div>


        <p class="muted">

            Use face registration only
            with appropriate permission
            and consent.

        </p>

    </div>

    `;

}



/* =========================================
   CAPTURE + SAVE FACE
========================================= */

async function captureStudentFace(
    studentId
) {

    const status =
        $("#faceStatus");


    const loaded =
        await loadFaceModels();


    if (!loaded) {

        return;

    }


    try {

        status.textContent =
            "Starting camera…";


        const video =
            await openCamera(
                "registerCamera"
            );


        status.textContent =
            "Keep one face in the frame…";


        await new Promise(
            resolve =>
                setTimeout(
                    resolve,
                    1500
                )
        );


        status.textContent =
            "Scanning face…";


        const results =
            await faceapi
                .detectAllFaces(

                    video,

                    new faceapi
                        .TinyFaceDetectorOptions({

                            inputSize:
                                320,

                            scoreThreshold:
                                0.55

                        })

                )
                .withFaceLandmarks()
                .withFaceDescriptors();


        if (
            results.length === 0
        ) {

            status.innerHTML = `

                <span
                    style="color:#ff6b7a"
                >

                    ✕ No face detected.

                </span>

                <br>

                Move closer and try again.

            `;


            stopCamera();

            return;

        }


        if (
            results.length > 1
        ) {

            status.innerHTML = `

                <span
                    style="color:#ff6b7a"
                >

                    ✕ More than one face detected.

                </span>

                <br>

                Keep only one person
                in front of the camera.

            `;


            stopCamera();

            return;

        }


        const descriptor =
            Array.from(
                results[0].descriptor
            );


        const { data: student } =
            await db
                .from("students")
                .select("*")
                .eq(
                    "school_id",
                    S.school
                )
                .eq(
                    "student_id",
                    studentId
                )
                .single();


        const { error } =
            await db
                .from(
                    "face_profiles"
                )
                .upsert(

                    {

                        school_id:
                            S.school,

                        student_id:
                            studentId,

                        student_name:
                            student.name,

                        descriptor:
                            descriptor

                    },

                    {

                        onConflict:
                            "school_id,student_id"

                    }

                );


        stopCamera();


        if (error) {

            status.innerHTML = `

                <span
                    style="color:#ff6b7a"
                >

                    ✕ ${safe(
                        error.message
                    )}

                </span>

            `;


            return;

        }


        status.innerHTML = `

            <span
                style="
                color:#4ade80;
                font-weight:700;
                "
            >

                ✓ Face Registered

            </span>

            <br>

            ${safe(
                student.name
            )}

            is ready for
            Smart Attendance.

        `;

    }

    catch (error) {

        console.error(
            error
        );


        stopCamera();


        status.innerHTML = `

            <span
                style="color:#ff6b7a"
            >

                Camera failed.

            </span>

            <br>

            ${safe(
                error.message
            )}

        `;

    }

}



/* =========================================
   TEACHERS
========================================= */

async function teachers() {

    const { data = [] } =
        await db
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

        <button
            onclick="addTeacher()"
        >
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
                        ${safe(
                            x.teacher_id
                        )}
                    </td>

                    <td>
                        ${safe(
                            x.teacher_name
                        )}
                    </td>

                    <td>

                        ${
                            x.enabled
                                ? "Active"
                                : "Disabled"
                        }

                    </td>

                </tr>

            `).join("")}

        </table>

    </div>

    `;

}



/* =========================================
   ADD TEACHER
========================================= */

async function addTeacher() {

    const { error } =
        await db
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
   NORMAL CAMERA
========================================= */

async function cam(id) {

    try {

        await openCamera(id);

    }

    catch (error) {

        console.error(error);

        alert(
            "Camera permission needed"
        );

    }

}



/* =========================================
   SMART ATTENDANCE PAGE
========================================= */

async function attendance() {

    $("#page").innerHTML = `

    <div class="box">

        <h3>
            Smart Attendance
        </h3>


        <p class="muted">

            Start the camera and place
            one registered student in
            front of it.

        </p>

    </div>


    <div
        class="camera"
        id="attendanceCamera"
        style="
        min-height:430px;
        position:relative;
        overflow:hidden;
        "
    >

        Smart Attendance Camera

    </div>


    <div class="tools">

        <button
            onclick="startSmartAttendance()"
        >

            Start Automatic Attendance

        </button>


        <button
            onclick="stopSmartAttendance()"
        >

            Stop Camera

        </button>

    </div>


    <div
        id="faceStatus"
        class="box"
    >

        Camera is off.

    </div>


    <div class="box">

        <b>
            Automatic Mode
        </b>

        <p class="muted">

            🟢 Registered student:
            recognized and marked Present.

            <br><br>

            🔴 Unregistered face:
            UNKNOWN.

            <br><br>

            Multiple faces:
            asks for one person at a time.

            <br><br>

            A student will not get
            duplicate attendance for
            the same day.

        </p>

    </div>

    `;

}



/* =========================================
   BUILD FACE MATCHER
========================================= */

async function buildFaceMatcher() {

    const { data, error } =
        await db
            .from(
                "face_profiles"
            )
            .select("*")
            .eq(
                "school_id",
                S.school
            );


    if (error) {

        throw new Error(
            error.message
        );

    }


    if (
        !data ||
        data.length === 0
    ) {

        throw new Error(
            "No student faces are registered yet. Go to Students → Register Face first."
        );

    }


    const profiles =
        data.map(profile => {

            const descriptor =
                new Float32Array(
                    profile.descriptor
                );


            return new faceapi
                .LabeledFaceDescriptors(

                    profile.student_id +
                    "|" +
                    profile.student_name,

                    [
                        descriptor
                    ]

                );

        });


    return new faceapi
        .FaceMatcher(
            profiles,
            0.52
        );

}



/* =========================================
   START SMART ATTENDANCE
========================================= */

async function startSmartAttendance() {

    const status =
        $("#faceStatus");


    try {

        const loaded =
            await loadFaceModels();


        if (!loaded) {

            return;

        }


        status.textContent =
            "Loading registered students…";


        const matcher =
            await buildFaceMatcher();


        status.textContent =
            "Starting camera…";


        const video =
            await openCamera(
                "attendanceCamera"
            );


        const canvas =
            $("#attendanceCameraCanvas");


        status.textContent =
            "Scanning — one person at a time.";


        attendanceTimer =
            setInterval(

                async () => {

                    if (
                        attendanceBusy ||
                        !video ||
                        video.readyState < 2
                    ) {

                        return;

                    }


                    attendanceBusy =
                        true;


                    try {

                        const results =
                            await faceapi
                                .detectAllFaces(

                                    video,

                                    new faceapi
                                        .TinyFaceDetectorOptions({

                                            inputSize:
                                                320,

                                            scoreThreshold:
                                                0.55

                                        })

                                )
                                .withFaceLandmarks()
                                .withFaceDescriptors();


                        const ctx =
                            canvas.getContext(
                                "2d"
                            );


                        canvas.width =
                            video.videoWidth;

                        canvas.height =
                            video.videoHeight;


                        ctx.clearRect(
                            0,
                            0,
                            canvas.width,
                            canvas.height
                        );


                        if (
                            results.length === 0
                        ) {

                            status.innerHTML = `

                                <span class="muted">

                                    No face detected.

                                </span>

                            `;

                            return;

                        }


                        if (
                            results.length > 1
                        ) {

                            status.innerHTML = `

                                <span
                                    style="
                                    color:#ff6b7a;
                                    font-weight:700;
                                    "
                                >

                                    ONE PERSON AT A TIME

                                </span>

                                <br>

                                Multiple faces detected.

                            `;

                            return;

                        }


                        const detection =
                            results[0];


                        const best =
                            matcher.findBestMatch(
                                detection.descriptor
                            );


                        const known =
                            best.label !==
                            "unknown";


                        let name =
                            "UNKNOWN";


                        let studentId =
                            null;


                        if (known) {

                            const parts =
                                best.label.split(
                                    "|"
                                );


                            studentId =
                                parts[0];


                            name =
                                parts
                                    .slice(1)
                                    .join("|");

                        }


                        drawFaceBox(
                            ctx,
                            detection.detection.box,
                            name,
                            known
                        );


                        if (!known) {

                            status.innerHTML = `

                                <span
                                    style="
                                    color:#ff536c;
                                    font-size:22px;
                                    font-weight:800;
                                    "
                                >

                                    🔴 UNKNOWN

                                </span>

                                <br>

                                Face is not registered.

                            `;


                            return;

                        }


                        status.innerHTML = `

                            <span
                                style="
                                color:#4ade80;
                                font-size:20px;
                                font-weight:800;
                                "
                            >

                                🟢 ${safe(name)}

                            </span>

                            <br>

                            Recognized —
                            marking attendance…

                        `;


                        await automaticMarkAttendance(
                            studentId,
                            name
                        );

                    }

                    catch (error) {

                        console.error(
                            error
                        );

                    }

                    finally {

                        attendanceBusy =
                            false;

                    }

                },

                1100

            );

    }

    catch (error) {

        console.error(
            error
        );


        stopCamera();


        status.innerHTML = `

            <span
                style="
                color:#ff6b7a;
                font-weight:700;
                "
            >

                ${safe(
                    error.message
                )}

            </span>

        `;

    }

}



/* =========================================
   DRAW GREEN / RED FACE BOX
========================================= */

function drawFaceBox(
    ctx,
    box,
    name,
    known
) {

    const colour =
        known
            ? "#4ade80"
            : "#ff536c";


    ctx.strokeStyle =
        colour;

    ctx.lineWidth =
        5;


    ctx.strokeRect(
        box.x,
        box.y,
        box.width,
        box.height
    );


    ctx.font =
        "bold 24px Arial";


    const label =
        known
            ? name
            : "UNKNOWN";


    const width =
        ctx.measureText(
            label
        ).width + 18;


    const labelY =
        Math.max(
            0,
            box.y - 35
        );


    ctx.fillStyle =
        colour;


    ctx.fillRect(
        box.x,
        labelY,
        width,
        34
    );


    ctx.fillStyle =
        "#06101d";


    ctx.fillText(
        label,
        box.x + 9,
        labelY + 25
    );

}



/* =========================================
   AUTOMATIC ATTENDANCE SAVE
========================================= */

async function automaticMarkAttendance(
    studentId,
    studentName
) {

    const d =
        new Date();


    const date =
        d.toISOString()
            .slice(0, 10);


    const sessionKey =
        S.school +
        "|" +
        studentId +
        "|" +
        date;


    if (
        markedThisSession.has(
            sessionKey
        )
    ) {

        const status =
            $("#faceStatus");


        if (status) {

            status.innerHTML = `

                <span
                    style="
                    color:#4ade80;
                    font-size:20px;
                    font-weight:800;
                    "
                >

                    🟢 ${safe(
                        studentName
                    )}

                </span>

                <br>

                ✓ Attendance already
                recorded today.

            `;

        }


        return;

    }


    const { data: student } =
        await db
            .from("students")
            .select("*")
            .eq(
                "school_id",
                S.school
            )
            .eq(
                "student_id",
                studentId
            )
            .maybeSingle();


    if (!student) {

        return;

    }


    const row = {

        school_id:
            S.school,

        student_id:
            studentId,

        name:
            student.name,

        class_name:
            student.class_name,

        attendance_date:
            date,

        attendance_time:
            d.toLocaleTimeString(),

        status:
            "Present"

    };


    const { error } =
        await db
            .from("attendance")
            .upsert(

                row,

                {

                    onConflict:
                        "school_id,student_id,attendance_date"

                }

            );


    const status =
        $("#faceStatus");


    if (error) {

        console.error(
            error
        );


        if (status) {

            status.innerHTML = `

                <span
                    style="color:#ff6b7a"
                >

                    ${safe(
                        studentName
                    )}

                    recognized, but attendance
                    could not be saved.

                </span>

                <br>

                ${safe(
                    error.message
                )}

            `;

        }


        return;

    }


    markedThisSession.add(
        sessionKey
    );


    if (status) {

        status.innerHTML = `

            <span
                style="
                color:#4ade80;
                font-size:20px;
                font-weight:800;
                "
            >

                🟢 ${safe(
                    student.name
                )}

            </span>

            <br>

            ✓ Present automatically saved.

        `;

    }

}



/* =========================================
   STOP SMART ATTENDANCE
========================================= */

function stopSmartAttendance() {

    stopCamera();


    const status =
        $("#faceStatus");


    if (status) {

        status.textContent =
            "Camera stopped.";

    }

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

        <button
            onclick="cam('occ')"
        >

            Start Camera

        </button>

    </div>


    <div class="box">

        <b>
            Current Occupancy: —
        </b>


        <p class="muted">

            Smart Occupancy automatic
            person counting will be
            connected separately.

        </p>

    </div>

    `;

}



/* =========================================
   REPORTS
========================================= */

async function reports() {

    const { data = [] } =
        await db
            .from("attendance")
            .select("*")
            .eq(
                "school_id",
                S.school
            )
            .order(
                "attendance_date",
                {
                    ascending:
                        false
                }
            )
            .limit(200);


    $("#page").innerHTML = `

    <div class="table">

        <table>

            <tr>

                <th>Date</th>

                <th>Time</th>

                <th>Name</th>

                <th>Class</th>

                <th>Status</th>

            </tr>


            ${data.map(x => `

                <tr>

                    <td>
                        ${safe(
                            x.attendance_date
                        )}
                    </td>

                    <td>
                        ${safe(
                            x.attendance_time || ""
                        )}
                    </td>

                    <td>
                        ${safe(
                            x.name
                        )}
                    </td>

                    <td>
                        ${safe(
                            x.class_name
                        )}
                    </td>

                    <td>
                        ${safe(
                            x.status
                        )}
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

    const { data = [] } =
        await db
            .from("schools")
            .select("*")
            .order(
                "created_at",
                {
                    ascending:
                        false
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
                        ${safe(
                            x.school_id
                        )}
                    </td>

                    <td>
                        ${safe(
                            x.school_name
                        )}
                    </td>

                    <td>
                        ${safe(
                            x.approval_status
                        )}
                    </td>

                    <td>

                        <button
                            onclick="
                            school(
                            '${safe(
                                x.school_id
                            )}',
                            'Approved'
                            )
                            "
                        >

                            Approve

                        </button>


                        <button
                            onclick="
                            school(
                            '${safe(
                                x.school_id
                            )}',
                            'Rejected'
                            )
                            "
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

async function school(
    id,
    s
) {

    await db
        .from("schools")
        .update({

            approval_status:
                s,

            approved_at:
                s === "Approved"
                    ? new Date()
                        .toISOString()
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
   RESTORE SESSION
========================================= */

if (S) {

    start(S);

}

else {

    const app =
        $("#app");


    if (app) {

        app.classList.add(
            "hidden"
        );

        app.style.display =
            "none";

    }

}
