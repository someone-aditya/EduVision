/* =========================================================
   EDUVISION
   COMPLETE APP.JS
========================================================= */

const C = window.EDUVISION_CONFIG || {};

const db =
    C.SUPABASE_URL &&
    C.SUPABASE_ANON_KEY &&
    window.supabase
        ? window.supabase.createClient(
            C.SUPABASE_URL,
            C.SUPABASE_ANON_KEY
        )
        : null;

const $ = s => document.querySelector(s);

let S = JSON.parse(
    localStorage.getItem("evs") || "null"
);


/* =========================================================
   GLOBAL AI / CAMERA VARIABLES
========================================================= */

let cameraStream = null;

let faceModelsReady = false;
let attendanceTimer = null;
let attendanceBusy = false;

let occupancyModel = null;
let occupancyTimer = null;
let occupancyBusy = false;

const markedThisSession = new Set();

const FACE_MODEL_URL =
    "https://cdn.jsdelivr.net/gh/vladmandic/face-api@1.7.12/model";


/* =========================================================
   HELPERS
========================================================= */

function safe(value) {
    return String(value ?? "").replace(
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


function field(label, name, type = "text") {
    return `
        <div class="field">
            <label>${label}</label>
            <input
                name="${name}"
                type="${type}"
                autocomplete="off"
                required
            >
        </div>
    `;
}


async function hash(text) {

    const data = await crypto.subtle.digest(
        "SHA-256",
        new TextEncoder().encode(text)
    );

    return [...new Uint8Array(data)]
        .map(x => x.toString(16).padStart(2, "0"))
        .join("");
}


function values() {

    const form = $("#form");

    if (!form) {
        return {};
    }

    return Object.fromEntries(
        [...form.querySelectorAll("input")]
            .map(input => [
                input.name,
                input.value.trim()
            ])
    );
}


function message(text) {

    const element = $("#msg");

    if (element) {
        element.textContent = text;
    }
}


function showDatabaseError(error) {

    console.error(error);

    const page = $("#page");

    if (!page) {
        return;
    }

    page.innerHTML = `
        <div class="box">

            <h3>
                Could not load data
            </h3>

            <p class="muted">
                ${safe(
                    error?.message ||
                    "Please check the database connection and try again."
                )}
            </p>

            <button onclick="page('Dashboard')">
                Back to Dashboard
            </button>

        </div>
    `;
}


/* =========================================================
   HOME
========================================================= */

function goHome() {

    stopCamera();

    $("#login").classList.add("hidden");
    $("#app").classList.add("hidden");

    $("#home").classList.remove("hidden");

    $("#home").style.display = "";
    $("#login").style.display = "none";
    $("#app").style.display = "none";
}


/* =========================================================
   LOGIN SCREEN
========================================================= */

function login(mode) {

    stopCamera();

    $("#home").classList.add("hidden");
    $("#home").style.display = "none";

    $("#app").classList.add("hidden");
    $("#app").style.display = "none";

    $("#login").classList.remove("hidden");
    $("#login").style.display = "flex";

    const form = $("#form");

    message("");


    /* SCHOOL ADMIN */

    if (mode === "admin") {

        $("#lt").textContent =
            "School Admin Login";

        form.innerHTML =
            field("School ID", "school") +
            field("Admin ID", "id") +
            field("Password", "pw", "password") +
            `<button id="loginButton">
                Sign In
            </button>`;

        $("#loginButton").onclick =
            schoolAdminLogin;

        return;
    }


    /* TEACHER */

    if (mode === "teacher") {

        $("#lt").textContent =
            "Teacher Login";

        form.innerHTML =
            field("School ID", "school") +
            field("Teacher ID", "id") +
            field("Password", "pw", "password") +
            `<button id="loginButton">
                Sign In
            </button>`;

        $("#loginButton").onclick =
            teacherLogin;

        return;
    }


    /* EDUVISION ADMIN */

    if (mode === "evadmin") {

        $("#lt").textContent =
            "EduVision Admin";

        form.innerHTML =
            field("Admin ID", "admin_id") +
            field(
                "Password",
                "password",
                "password"
            ) +
            `<button id="loginButton">
                Sign In
            </button>`;

        $("#loginButton").onclick =
            eduvisionAdminLogin;

        return;
    }


    /* REGISTER SCHOOL */

    if (mode === "register") {

        $("#lt").textContent =
            "Register School";

        form.innerHTML =
            field("School Name", "name") +
            field("School ID", "school") +
            field("Admin ID", "id") +
            field("Password", "pw", "password") +
            `<button id="loginButton">
                Register School
            </button>`;

        $("#loginButton").onclick =
            registerSchool;
    }
}


/* =========================================================
   SCHOOL ADMIN LOGIN
========================================================= */

async function schoolAdminLogin() {

    if (!db) {
        return message(
            "Database connection is not configured."
        );
    }

    const button = $("#loginButton");

    try {

        button.disabled = true;
        button.textContent = "Signing In...";

        message("");

        const a = values();

        if (
            !a.school ||
            !a.id ||
            !a.pw
        ) {

            message("Please fill in all fields.");

            return;
        }


        const result = await db
            .from("schools")
            .select("*")
            .eq("school_id", a.school)
            .eq("admin_id", a.id)
            .maybeSingle();


        if (result.error) {
            throw result.error;
        }


        const school = result.data;


        if (!school) {

            message(
                "School ID or Admin ID is incorrect."
            );

            return;
        }


        if (
            school.approval_status !==
            "Approved"
        ) {

            message(
                "This school has not been approved yet."
            );

            return;
        }


        const enteredPassword =
            await hash(a.pw);


        if (
            enteredPassword !==
            school.admin_password_hash
        ) {

            message("Incorrect password.");

            return;
        }


        loginSuccess({
            role: "School Admin",
            school: school.school_id,
            name: school.school_name
        });

    }

    catch (error) {

        console.error(error);

        message(
            "Login failed: " +
            (error.message || "Database error")
        );

    }

    finally {

        if (button) {
            button.disabled = false;
            button.textContent = "Sign In";
        }
    }
}


/* =========================================================
   TEACHER LOGIN
========================================================= */

async function teacherLogin() {

    if (!db) {
        return message(
            "Database connection is not configured."
        );
    }

    const button = $("#loginButton");

    try {

        button.disabled = true;
        button.textContent = "Signing In...";

        const a = values();


        if (
            !a.school ||
            !a.id ||
            !a.pw
        ) {

            message("Please fill in all fields.");

            return;
        }


        const result = await db
            .from("teachers")
            .select("*")
            .eq("school_id", a.school)
            .eq("teacher_id", a.id)
            .maybeSingle();


        if (result.error) {
            throw result.error;
        }


        const teacher = result.data;


        if (!teacher) {

            message(
                "Teacher account not found."
            );

            return;
        }


        if (!teacher.enabled) {

            message(
                "This teacher account is disabled."
            );

            return;
        }


        if (
            await hash(a.pw) !==
            teacher.password_hash
        ) {

            message("Incorrect password.");

            return;
        }


        loginSuccess({
            role: "Teacher",
            school: teacher.school_id,
            name: teacher.teacher_name
        });

    }

    catch (error) {

        console.error(error);

        message(
            "Teacher login failed: " +
            (error.message || "Database error")
        );

    }

    finally {

        if (button) {
            button.disabled = false;
            button.textContent = "Sign In";
        }
    }
}


/* =========================================================
   EDUVISION ADMIN LOGIN
========================================================= */

async function eduvisionAdminLogin() {

    const button = $("#loginButton");

    try {

        button.disabled = true;
        button.textContent = "Signing In...";

        message("");

        const a = values();


        const response = await fetch(
            "/api/admin-login",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    admin_id: a.admin_id,
                    password: a.password
                })
            }
        );


        if (!response.ok) {

            message(
                "Incorrect Admin ID or password."
            );

            return;
        }


        loginSuccess({
            role: "EduVision Admin",
            name: "EduVision Admin"
        });

    }

    catch (error) {

        console.error(error);

        message(
            "Could not connect to EduVision."
        );

    }

    finally {

        if (button) {
            button.disabled = false;
            button.textContent = "Sign In";
        }
    }
}


/* =========================================================
   REGISTER SCHOOL
========================================================= */

async function registerSchool() {

    if (!db) {
        return message(
            "Database connection is not configured."
        );
    }

    const button = $("#loginButton");

    try {

        button.disabled = true;
        button.textContent = "Submitting...";

        const a = values();


        if (
            !a.name ||
            !a.school ||
            !a.id ||
            !a.pw
        ) {

            message(
                "Please fill in all fields."
            );

            return;
        }


        const result = await db
            .from("schools")
            .insert({
                school_name: a.name,
                school_id: a.school,
                admin_id: a.id,
                admin_password_hash:
                    await hash(a.pw),
                approval_status: "Pending"
            });


        if (result.error) {
            throw result.error;
        }


        message(
            "Registration submitted. Wait for EduVision Admin approval."
        );

    }

    catch (error) {

        console.error(error);

        message(
            error.message ||
            "Registration failed."
        );

    }

    finally {

        if (button) {
            button.disabled = false;
            button.textContent =
                "Register School";
        }
    }
}


/* =========================================================
   LOGIN SUCCESS
========================================================= */

function loginSuccess(session) {

    localStorage.setItem(
        "evs",
        JSON.stringify(session)
    );

    S = session;

    start(session);
}


/* =========================================================
   START APPLICATION
========================================================= */

function start(session) {

    S = session;

    $("#home").classList.add("hidden");
    $("#login").classList.add("hidden");

    $("#home").style.display = "none";
    $("#login").style.display = "none";

    $("#app").classList.remove("hidden");
    $("#app").style.display = "grid";


    $("#who").innerHTML = `
        <b>${safe(session.name)}</b>
        <br>
        ${safe(session.role)}
    `;


    let pages = [];


    if (
        session.role ===
        "EduVision Admin"
    ) {

        pages = [
            "Dashboard",
            "Schools"
        ];

    }

    else if (
        session.role ===
        "School Admin"
    ) {

        pages = [
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

        pages = [
            "Dashboard",
            "Students",
            "Smart Attendance",
            "Smart Occupancy",
            "Reports"
        ];
    }


    $("#nav").innerHTML =
        pages.map(name => `

            <button
                onclick="page('${name}')"
            >
                <span>${name}</span>
            </button>

        `).join("");


    page("Dashboard");
}


/* =========================================================
   LOGOUT
========================================================= */

function logout() {

    stopCamera();

    localStorage.removeItem("evs");

    S = null;

    window.location.reload();
}


/* =========================================================
   DATABASE COUNT
========================================================= */

async function countRows(
    table,
    key = null,
    value = null
) {

    if (!db) {
        return 0;
    }


    let query = db
        .from(table)
        .select(
            "*",
            {
                count: "exact",
                head: true
            }
        );


    if (
        S &&
        S.school
    ) {

        query =
            query.eq(
                "school_id",
                S.school
            );
    }


    if (key) {

        query =
            query.eq(
                key,
                value
            );
    }


    const result =
        await query;


    if (result.error) {
        throw result.error;
    }


    return result.count || 0;
}


/* =========================================================
   PAGE ROUTER
========================================================= */

async function page(name) {

    stopCamera();

    $("#title").textContent =
        name;

    $("#page").innerHTML = `
        <div class="box">
            Loading...
        </div>
    `;


    try {

        if (name === "Dashboard") {

            await dashboardPage();

            return;
        }


        if (name === "Students") {

            await studentsPage();

            return;
        }


        if (name === "Teachers") {

            await teachersPage();

            return;
        }


        if (
            name ===
            "Smart Attendance"
        ) {

            attendancePage();

            return;
        }


        if (
            name ===
            "Smart Occupancy"
        ) {

            occupancyPage();

            return;
        }


        if (name === "Reports") {

            await reportsPage();

            return;
        }


        if (name === "Schools") {

            await schoolsPage();

            return;
        }


        if (name === "Settings") {

            settingsPage();

            return;
        }


        $("#page").innerHTML = `
            <div class="box">
                Page not found.
            </div>
        `;

    }

    catch (error) {

        showDatabaseError(error);
    }
}


/* =========================================================
   DASHBOARD
========================================================= */

async function dashboardPage() {

    if (
        S.role ===
        "EduVision Admin"
    ) {

        const pending =
            await countRows(
                "schools",
                "approval_status",
                "Pending"
            );

        const approved =
            await countRows(
                "schools",
                "approval_status",
                "Approved"
            );


        $("#page").innerHTML =
            stats([
                [
                    "Pending Schools",
                    pending
                ],
                [
                    "Approved Schools",
                    approved
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


    const today =
        localDate();


    const students =
        await countRows(
            "students",
            "status",
            "Active"
        );


    const teachers =
        await countRows(
            "teachers",
            "enabled",
            true
        );


    const attendance =
        await countRows(
            "attendance",
            "attendance_date",
            today
        );


    $("#page").innerHTML =
        stats([
            [
                "Active Students",
                students
            ],
            [
                "Teachers",
                teachers
            ],
            [
                "Marked Today",
                attendance
            ],
            [
                "System",
                "Online"
            ]
        ]);
}


function stats(items) {

    return `
        <div class="stats">

            ${items.map(item => `

                <div class="box">

                    <span class="muted">
                        ${safe(item[0])}
                    </span>

                    <b>
                        ${safe(item[1])}
                    </b>

                </div>

            `).join("")}

        </div>
    `;
}


/* =========================================================
   LOCAL DATE
========================================================= */

function localDate() {

    const d = new Date();

    const year =
        d.getFullYear();

    const month =
        String(
            d.getMonth() + 1
        ).padStart(2, "0");

    const day =
        String(
            d.getDate()
        ).padStart(2, "0");


    return `${year}-${month}-${day}`;
}


/* =========================================================
   STUDENTS
========================================================= */

async function studentsPage() {

    if (!db) {
        throw new Error(
            "Database is not configured."
        );
    }


    const studentsResult =
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
                    ascending: false
                }
            );


    if (studentsResult.error) {
        throw studentsResult.error;
    }


    const students =
        studentsResult.data || [];


    const facesResult =
        await db
            .from("face_profiles")
            .select("student_id")
            .eq(
                "school_id",
                S.school
            );


    const registered =
        new Set();


    if (!facesResult.error) {

        for (
            const face
            of facesResult.data || []
        ) {

            registered.add(
                face.student_id
            );
        }
    }


    $("#page").innerHTML = `

        ${
            S.role ===
            "School Admin"

            ? `

            <div class="box">

                <h3>
                    Add Student
                </h3>

                <div class="tools">

                    <input
                        id="studentId"
                        placeholder="Student ID"
                    >

                    <input
                        id="studentName"
                        placeholder="Name"
                    >

                    <input
                        id="studentClass"
                        placeholder="Class"
                    >

                    <input
                        id="studentRoll"
                        placeholder="Roll No"
                    >

                    <button
                        onclick="addStudent()"
                    >
                        Add Student
                    </button>

                </div>

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


                ${students.map(student => `

                    <tr>

                        <td>
                            ${safe(
                                student.student_id
                            )}
                        </td>

                        <td>
                            ${safe(
                                student.name
                            )}
                        </td>

                        <td>
                            ${safe(
                                student.class_name
                            )}
                        </td>

                        <td>
                            ${safe(
                                student.roll_no
                            )}
                        </td>

                        <td>
                            ${safe(
                                student.status
                            )}
                        </td>

                        <td>

                            ${
                                registered.has(
                                    student.student_id
                                )

                                ? `

                                <span
                                    style="
                                    color:#4ade80;
                                    font-weight:bold;
                                    "
                                >
                                    ✓ Registered
                                </span>

                                ${
                                    S.role ===
                                    "School Admin"

                                    ? `

                                    <button
                                        onclick="registerFace(
                                            '${safe(
                                                student.student_id
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
                                            student.student_id
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

                Smart Attendance face profiles
                should only be registered for
                consenting demo participants with
                appropriate permission.

            </p>

        </div>
    `;
}


/* =========================================================
   ADD STUDENT
========================================================= */

async function addStudent() {

    try {

        const studentId =
            $("#studentId").value.trim();

        const name =
            $("#studentName").value.trim();

        const className =
            $("#studentClass").value.trim();

        const roll =
            $("#studentRoll").value.trim();


        if (
            !studentId ||
            !name ||
            !className
        ) {

            alert(
                "Enter Student ID, Name and Class."
            );

            return;
        }


        const result =
            await db
                .from("students")
                .insert({
                    school_id: S.school,
                    student_id: studentId,
                    name: name,
                    class_name: className,
                    roll_no: roll,
                    status: "Active"
                });


        if (result.error) {
            throw result.error;
        }


        alert("Student added.");

        studentsPage();

    }

    catch (error) {

        alert(
            error.message ||
            "Could not add student."
        );
    }
}


/* =========================================================
   FACE MODEL
========================================================= */

async function loadFaceModels() {

    if (faceModelsReady) {
        return true;
    }


    if (!window.faceapi) {

        throw new Error(
            "Face recognition library did not load."
        );
    }


    const status =
        $("#faceStatus");


    if (status) {
        status.textContent =
            "Loading Smart Attendance AI...";
    }


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


    faceModelsReady = true;


    if (status) {
        status.textContent =
            "Smart Attendance ready.";
    }


    return true;
}


/* =========================================================
   CAMERA
========================================================= */

async function openCamera(
    containerId
) {

    stopCamera();


    if (
        !navigator.mediaDevices ||
        !navigator.mediaDevices.getUserMedia
    ) {

        throw new Error(
            "Camera is not supported by this browser."
        );
    }


    cameraStream =
        await navigator.mediaDevices
            .getUserMedia({

                video: {
                    facingMode: "user",

                    width: {
                        ideal: 960
                    },

                    height: {
                        ideal: 540
                    }
                },

                audio: false
            });


    const container =
        $("#" + containerId);


    if (!container) {

        throw new Error(
            "Camera container was not found."
        );
    }


    container.innerHTML = `

        <video
            id="${containerId}Video"
            autoplay
            muted
            playsinline
        ></video>

        <canvas
            id="${containerId}Canvas"
        ></canvas>

    `;


    container.style.position =
        "relative";


    const video =
        $("#" + containerId + "Video");


    video.srcObject =
        cameraStream;


    await video.play();


    return video;
}


/* =========================================================
   STOP ALL CAMERA AI
========================================================= */

function stopCamera() {

    if (attendanceTimer) {

        clearInterval(
            attendanceTimer
        );

        attendanceTimer = null;
    }


    if (occupancyTimer) {

        clearInterval(
            occupancyTimer
        );

        occupancyTimer = null;
    }


    attendanceBusy = false;
    occupancyBusy = false;


    if (cameraStream) {

        cameraStream
            .getTracks()
            .forEach(
                track => track.stop()
            );

        cameraStream = null;
    }
}


/* =========================================================
   REGISTER FACE
========================================================= */

async function registerFace(
    studentId
) {

    stopCamera();


    try {

        const result =
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


        if (result.error) {
            throw result.error;
        }


        const student =
            result.data;


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
                    Register Smart Attendance Profile
                </h3>

                <p>
                    <b>
                        ${safe(student.name)}
                    </b>

                    <span class="muted">
                        ${safe(student.student_id)}
                        •
                        ${safe(student.class_name)}
                    </span>
                </p>


                <p class="muted">
                    Use a consenting demo participant.
                    Keep exactly one face clearly visible.
                </p>


                <div
                    id="registerCamera"
                    class="camera"
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
                    Ready.
                </div>

            </div>
        `;

    }

    catch (error) {

        showDatabaseError(error);
    }
}


/* =========================================================
   CAPTURE FACE
========================================================= */

async function captureStudentFace(
    studentId
) {

    const status =
        $("#faceStatus");


    try {

        await loadFaceModels();


        status.textContent =
            "Starting camera...";


        const video =
            await openCamera(
                "registerCamera"
            );


        status.textContent =
            "Look at the camera...";


        await new Promise(
            resolve =>
                setTimeout(
                    resolve,
                    1500
                )
        );


        const detections =
            await faceapi
                .detectAllFaces(
                    video,

                    new faceapi
                        .TinyFaceDetectorOptions({
                            inputSize: 320,
                            scoreThreshold: 0.5
                        })
                )
                .withFaceLandmarks()
                .withFaceDescriptors();


        if (
            detections.length === 0
        ) {

            status.innerHTML = `
                <span style="color:#ff6b7a">
                    No face detected.
                </span>
            `;

            stopCamera();

            return;
        }


        if (
            detections.length > 1
        ) {

            status.innerHTML = `
                <span style="color:#ff6b7a">
                    More than one face detected.
                    Keep one person at a time.
                </span>
            `;

            stopCamera();

            return;
        }


        const studentResult =
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


        if (studentResult.error) {
            throw studentResult.error;
        }


        const student =
            studentResult.data;


        if (!student) {

            throw new Error(
                "Student was not found."
            );
        }


        const descriptor =
            Array.from(
                detections[0].descriptor
            );


        const saveResult =
            await db
                .from("face_profiles")
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


        if (saveResult.error) {
            throw saveResult.error;
        }


        stopCamera();


        status.innerHTML = `

            <span
                style="
                color:#4ade80;
                font-weight:bold;
                "
            >
                ✓ Face Registered
            </span>

            <br>

            ${safe(student.name)}
            is ready for Smart Attendance.
        `;

    }

    catch (error) {

        console.error(error);

        stopCamera();


        if (status) {

            status.innerHTML = `
                <span style="color:#ff6b7a">
                    ${safe(
                        error.message ||
                        "Face registration failed."
                    )}
                </span>
            `;
        }
    }
}


/* =========================================================
   TEACHERS
========================================================= */

async function teachersPage() {

    if (
        S.role !==
        "School Admin"
    ) {

        $("#page").innerHTML = `
            <div class="box">
                School Admin access required.
            </div>
        `;

        return;
    }


    const result =
        await db
            .from("teachers")
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


    if (result.error) {
        throw result.error;
    }


    const teachers =
        result.data || [];


    $("#page").innerHTML = `

        <div class="box">

            <h3>
                Add Teacher
            </h3>

            <div class="tools">

                <input
                    id="teacherId"
                    placeholder="Teacher ID"
                >

                <input
                    id="teacherName"
                    placeholder="Teacher Name"
                >

                <input
                    id="teacherPassword"
                    type="password"
                    placeholder="Password"
                >

                <button
                    onclick="addTeacher()"
                >
                    Add Teacher
                </button>

            </div>

        </div>


        <div class="table">

            <table>

                <tr>
                    <th>Teacher ID</th>
                    <th>Name</th>
                    <th>Status</th>
                </tr>


                ${teachers.map(teacher => `

                    <tr>

                        <td>
                            ${safe(
                                teacher.teacher_id
                            )}
                        </td>

                        <td>
                            ${safe(
                                teacher.teacher_name
                            )}
                        </td>

                        <td>
                            ${
                                teacher.enabled
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


/* =========================================================
   ADD TEACHER
========================================================= */

async function addTeacher() {

    try {

        const id =
            $("#teacherId").value.trim();

        const name =
            $("#teacherName").value.trim();

        const password =
            $("#teacherPassword").value;


        if (
            !id ||
            !name ||
            !password
        ) {

            alert(
                "Fill in all teacher fields."
            );

            return;
        }


        const result =
            await db
                .from("teachers")
                .insert({
                    school_id:
                        S.school,

                    teacher_id:
                        id,

                    teacher_name:
                        name,

                    password_hash:
                        await hash(password),

                    enabled:
                        true
                });


        if (result.error) {
            throw result.error;
        }


        alert("Teacher added.");

        teachersPage();

    }

    catch (error) {

        alert(
            error.message ||
            "Could not add teacher."
        );
    }
}


/* =========================================================
   SMART ATTENDANCE PAGE
========================================================= */

function attendancePage() {

    $("#page").innerHTML = `

        <div class="box">

            <h3>
                Smart Attendance
            </h3>

            <p class="muted">
                Start the camera and place one
                registered demo participant in
                front of it.
            </p>

        </div>


        <div
            id="attendanceCamera"
            class="camera"
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

                🟢 Registered profile:
                recognized and marked Present.

                <br><br>

                🔴 Unregistered face:
                UNKNOWN.

                <br><br>

                Multiple faces:
                one person at a time.

                <br><br>

                Attendance is not duplicated
                for the same person on the
                same day.

            </p>

        </div>
    `;
}


/* =========================================================
   FACE MATCHER
========================================================= */

async function buildFaceMatcher() {

    const result =
        await db
            .from("face_profiles")
            .select("*")
            .eq(
                "school_id",
                S.school
            );


    if (result.error) {
        throw result.error;
    }


    const profiles =
        result.data || [];


    if (
        profiles.length === 0
    ) {

        throw new Error(
            "No face profiles are registered. Go to Students → Register Face first."
        );
    }


    const labels =
        profiles.map(profile => {

            const descriptor =
                new Float32Array(
                    profile.descriptor
                );


            return new faceapi
                .LabeledFaceDescriptors(

                    profile.student_id +
                    "|" +
                    profile.student_name,

                    [descriptor]
                );
        });


    return new faceapi.FaceMatcher(
        labels,
        0.52
    );
}


/* =========================================================
   START SMART ATTENDANCE
========================================================= */

async function startSmartAttendance() {

    const status =
        $("#faceStatus");


    try {

        stopCamera();


        status.textContent =
            "Loading Smart Attendance...";


        await loadFaceModels();


        const matcher =
            await buildFaceMatcher();


        status.textContent =
            "Starting camera...";


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


                    attendanceBusy = true;


                    try {

                        const detections =
                            await faceapi
                                .detectAllFaces(

                                    video,

                                    new faceapi
                                        .TinyFaceDetectorOptions({
                                            inputSize: 320,
                                            scoreThreshold: 0.5
                                        })
                                )
                                .withFaceLandmarks()
                                .withFaceDescriptors();


                        prepareCanvas(
                            canvas,
                            video
                        );


                        const ctx =
                            canvas.getContext(
                                "2d"
                            );


                        ctx.clearRect(
                            0,
                            0,
                            canvas.width,
                            canvas.height
                        );


                        if (
                            detections.length === 0
                        ) {

                            status.innerHTML = `
                                <span class="muted">
                                    No face detected.
                                </span>
                            `;

                            return;
                        }


                        if (
                            detections.length > 1
                        ) {

                            status.innerHTML = `
                                <span
                                    style="
                                    color:#ff6b7a;
                                    font-weight:bold;
                                    "
                                >
                                    ONE PERSON AT A TIME
                                </span>
                            `;

                            return;
                        }


                        const detection =
                            detections[0];


                        const best =
                            matcher.findBestMatch(
                                detection.descriptor
                            );


                        const known =
                            best.label !==
                            "unknown";


                        if (!known) {

                            drawDetectionBox(
                                ctx,
                                detection.detection.box,
                                "UNKNOWN",
                                "#ff536c"
                            );


                            status.innerHTML = `
                                <span
                                    style="
                                    color:#ff536c;
                                    font-size:20px;
                                    font-weight:bold;
                                    "
                                >
                                    🔴 UNKNOWN
                                </span>
                            `;

                            return;
                        }


                        const parts =
                            best.label.split("|");


                        const studentId =
                            parts.shift();


                        const name =
                            parts.join("|");


                        drawDetectionBox(
                            ctx,
                            detection.detection.box,
                            name,
                            "#4ade80"
                        );


                        status.innerHTML = `
                            <span
                                style="
                                color:#4ade80;
                                font-size:20px;
                                font-weight:bold;
                                "
                            >
                                🟢 ${safe(name)}
                            </span>

                            <br>

                            Recognized.
                        `;


                        await saveAutomaticAttendance(
                            studentId,
                            name
                        );

                    }

                    catch (error) {

                        console.error(error);

                    }

                    finally {

                        attendanceBusy =
                            false;
                    }

                },

                1200
            );

    }

    catch (error) {

        console.error(error);

        stopCamera();


        status.innerHTML = `
            <span
                style="
                color:#ff6b7a;
                font-weight:bold;
                "
            >
                ${safe(
                    error.message ||
                    "Smart Attendance failed."
                )}
            </span>
        `;
    }
}


/* =========================================================
   CANVAS
========================================================= */

function prepareCanvas(
    canvas,
    video
) {

    if (
        canvas.width !==
        video.videoWidth
    ) {
        canvas.width =
            video.videoWidth;
    }


    if (
        canvas.height !==
        video.videoHeight
    ) {
        canvas.height =
            video.videoHeight;
    }
}


function drawDetectionBox(
    ctx,
    box,
    label,
    colour
) {

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
        "bold 22px Arial";


    const width =
        ctx.measureText(
            label
        ).width + 20;


    const y =
        Math.max(
            0,
            box.y - 34
        );


    ctx.fillStyle =
        colour;


    ctx.fillRect(
        box.x,
        y,
        width,
        34
    );


    ctx.fillStyle =
        "#06101d";


    ctx.fillText(
        label,
        box.x + 10,
        y + 24
    );
}


/* =========================================================
   AUTOMATIC ATTENDANCE SAVE
========================================================= */

async function saveAutomaticAttendance(
    studentId,
    studentName
) {

    const date =
        localDate();


    const key =
        `${S.school}|${studentId}|${date}`;


    const status =
        $("#faceStatus");


    if (
        markedThisSession.has(key)
    ) {

        if (status) {

            status.innerHTML = `
                <span
                    style="
                    color:#4ade80;
                    font-size:20px;
                    font-weight:bold;
                    "
                >
                    🟢 ${safe(studentName)}
                </span>

                <br>

                ✓ Attendance already recorded today.
            `;
        }

        return;
    }


    const existing =
        await db
            .from("attendance")
            .select("id")
            .eq(
                "school_id",
                S.school
            )
            .eq(
                "student_id",
                studentId
            )
            .eq(
                "attendance_date",
                date
            )
            .maybeSingle();


    if (existing.error) {
        throw existing.error;
    }


    if (existing.data) {

        markedThisSession.add(key);


        if (status) {

            status.innerHTML = `
                <span
                    style="
                    color:#4ade80;
                    font-size:20px;
                    font-weight:bold;
                    "
                >
                    🟢 ${safe(studentName)}
                </span>

                <br>

                ✓ Attendance already recorded today.
            `;
        }

        return;
    }


    const studentResult =
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


    if (studentResult.error) {
        throw studentResult.error;
    }


    const student =
        studentResult.data;


    if (!student) {
        return;
    }


    const now =
        new Date();


    const save =
        await db
            .from("attendance")
            .insert({
                school_id:
                    S.school,

                student_id:
                    student.student_id,

                name:
                    student.name,

                class_name:
                    student.class_name,

                attendance_date:
                    date,

                attendance_time:
                    now.toLocaleTimeString(),

                status:
                    "Present"
            });


    if (save.error) {

        console.error(
            save.error
        );

        return;
    }


    markedThisSession.add(key);


    if (status) {

        status.innerHTML = `
            <span
                style="
                color:#4ade80;
                font-size:20px;
                font-weight:bold;
                "
            >
                🟢 ${safe(student.name)}
            </span>

            <br>

            ✓ Present automatically saved.
        `;
    }
}


/* =========================================================
   STOP ATTENDANCE
========================================================= */

function stopSmartAttendance() {

    stopCamera();


    const status =
        $("#faceStatus");


    if (status) {
        status.textContent =
            "Camera stopped.";
    }
}


/* =========================================================
   SMART OCCUPANCY PAGE
========================================================= */

function occupancyPage() {

    $("#page").innerHTML = `

        <div class="box">

            <h3>
                Smart Occupancy
            </h3>

            <p class="muted">
                Automatically detects people
                visible in the classroom camera
                and shows the live occupancy.
            </p>

        </div>


        <div
            id="occupancyCamera"
            class="camera"
        >
            Live Classroom
        </div>


        <div class="tools">

            <button
                onclick="startSmartOccupancy()"
            >
                Start Smart Occupancy
            </button>


            <button
                onclick="stopSmartOccupancy()"
            >
                Stop Camera
            </button>

        </div>


        <div class="stats">

            <div class="box">

                <span class="muted">
                    Current Occupancy
                </span>

                <b id="occupancyCount">
                    0
                </b>

            </div>


            <div class="box">

                <span class="muted">
                    Detection
                </span>

                <b id="occupancyState">
                    Off
                </b>

            </div>

        </div>


        <div
            id="occupancyStatus"
            class="box"
            style="margin-top:15px"
        >
            Camera is off.
        </div>
    `;
}


/* =========================================================
   LOAD OCCUPANCY AI
========================================================= */

async function loadOccupancyModel() {

    if (occupancyModel) {
        return occupancyModel;
    }


    if (
        !window.cocoSsd
    ) {

        throw new Error(
            "Smart Occupancy AI library did not load."
        );
    }


    const status =
        $("#occupancyStatus");


    if (status) {

        status.textContent =
            "Loading person detection AI...";
    }


    occupancyModel =
        await cocoSsd.load({
            base: "lite_mobilenet_v2"
        });


    return occupancyModel;
}


/* =========================================================
   START SMART OCCUPANCY
========================================================= */

async function startSmartOccupancy() {

    const status =
        $("#occupancyStatus");


    try {

        stopCamera();


        if (status) {

            status.textContent =
                "Loading Smart Occupancy...";
        }


        const model =
            await loadOccupancyModel();


        if (status) {

            status.textContent =
                "Starting camera...";
        }


        const video =
            await openCamera(
                "occupancyCamera"
            );


        const canvas =
            $("#occupancyCameraCanvas");


        $("#occupancyState").textContent =
            "Active";


        status.textContent =
            "Detecting people...";


        occupancyTimer =
            setInterval(
                async () => {

                    if (
                        occupancyBusy ||
                        !video ||
                        video.readyState < 2
                    ) {
                        return;
                    }


                    occupancyBusy = true;


                    try {

                        const predictions =
                            await model.detect(
                                video
                            );


                        const people =
                            predictions.filter(
                                prediction =>
                                    prediction.class ===
                                        "person" &&
                                    prediction.score >=
                                        0.50
                            );


                        const count =
                            people.length;


                        const countElement =
                            $("#occupancyCount");


                        if (countElement) {
                            countElement.textContent =
                                count;
                        }


                        prepareCanvas(
                            canvas,
                            video
                        );


                        const ctx =
                            canvas.getContext(
                                "2d"
                            );


                        ctx.clearRect(
                            0,
                            0,
                            canvas.width,
                            canvas.height
                        );


                        people.forEach(
                            (
                                person,
                                index
                            ) => {

                                const [
                                    x,
                                    y,
                                    width,
                                    height
                                ] =
                                    person.bbox;


                                drawOccupancyBox(
                                    ctx,
                                    x,
                                    y,
                                    width,
                                    height,
                                    index + 1,
                                    person.score
                                );
                            }
                        );


                        if (status) {

                            status.innerHTML = `

                                <span
                                    style="
                                    color:#4ade80;
                                    font-weight:bold;
                                    "
                                >
                                    ● Live Detection
                                </span>

                                <br>

                                ${count}
                                ${
                                    count === 1
                                        ? "person"
                                        : "people"
                                }
                                detected.

                            `;
                        }

                    }

                    catch (error) {

                        console.error(
                            error
                        );

                    }

                    finally {

                        occupancyBusy =
                            false;
                    }

                },

                700
            );

    }

    catch (error) {

        console.error(error);

        stopCamera();


        if (
            $("#occupancyState")
        ) {

            $("#occupancyState")
                .textContent =
                "Error";
        }


        if (status) {

            status.innerHTML = `

                <span
                    style="
                    color:#ff6b7a;
                    font-weight:bold;
                    "
                >
                    ${safe(
                        error.message ||
                        "Smart Occupancy could not start."
                    )}
                </span>

            `;
        }
    }
}


/* =========================================================
   DRAW OCCUPANCY BOX
========================================================= */

function drawOccupancyBox(
    ctx,
    x,
    y,
    width,
    height,
    number,
    score
) {

    const colour =
        "#4ade80";


    ctx.strokeStyle =
        colour;

    ctx.lineWidth =
        4;


    ctx.strokeRect(
        x,
        y,
        width,
        height
    );


    const confidence =
        Math.round(
            score * 100
        );


    const label =
        `Person ${number} • ${confidence}%`;


    ctx.font =
        "bold 18px Arial";


    const labelWidth =
        ctx.measureText(
            label
        ).width + 18;


    const labelY =
        Math.max(
            0,
            y - 30
        );


    ctx.fillStyle =
        colour;


    ctx.fillRect(
        x,
        labelY,
        labelWidth,
        30
    );


    ctx.fillStyle =
        "#06101d";


    ctx.fillText(
        label,
        x + 9,
        labelY + 21
    );
}


/* =========================================================
   STOP OCCUPANCY
========================================================= */

function stopSmartOccupancy() {

    stopCamera();


    const state =
        $("#occupancyState");

    const status =
        $("#occupancyStatus");


    if (state) {
        state.textContent =
            "Off";
    }


    if (status) {
        status.textContent =
            "Camera stopped.";
    }
}


/* =========================================================
   REPORTS
========================================================= */

async function reportsPage() {

    const result =
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
                    ascending: false
                }
            )
            .limit(200);


    if (result.error) {
        throw result.error;
    }


    const records =
        result.data || [];


    $("#page").innerHTML = `

        <div class="box">

            <h3>
                Attendance Reports
            </h3>

            <p class="muted">
                Recent attendance records.
            </p>

        </div>


        <div class="table">

            <table>

                <tr>
                    <th>Date</th>
                    <th>Time</th>
                    <th>Student</th>
                    <th>Class</th>
                    <th>Status</th>
                </tr>


                ${records.map(record => `

                    <tr>

                        <td>
                            ${safe(
                                record.attendance_date
                            )}
                        </td>

                        <td>
                            ${safe(
                                record.attendance_time || ""
                            )}
                        </td>

                        <td>
                            ${safe(
                                record.name
                            )}
                        </td>

                        <td>
                            ${safe(
                                record.class_name
                            )}
                        </td>

                        <td>
                            ${safe(
                                record.status
                            )}
                        </td>

                    </tr>

                `).join("")}

            </table>

        </div>
    `;
}


/* =========================================================
   SETTINGS
========================================================= */

function settingsPage() {

    $("#page").innerHTML = `

        <div class="box">

            <h3>
                School Settings
            </h3>

            <p class="muted">
                School ID
            </p>

            <b>
                ${safe(S.school)}
            </b>

        </div>


        <div
            class="box"
            style="margin-top:15px"
        >

            <h3>
                EduVision
            </h3>

            <p class="muted">
                Smart classroom attendance,
                occupancy monitoring and
                classroom management.
            </p>

        </div>
    `;
}


/* =========================================================
   EDUVISION ADMIN SCHOOLS
========================================================= */

async function schoolsPage() {

    if (!db) {

        throw new Error(
            "Supabase is not configured."
        );
    }


    const result =
        await db
            .from("schools")
            .select("*")
            .order(
                "created_at",
                {
                    ascending: false
                }
            );


    if (result.error) {
        throw result.error;
    }


    const schools =
        result.data || [];


    $("#page").innerHTML = `

        <div class="box">

            <h3>
                School Registrations
            </h3>

            <p class="muted">
                Review and manage schools
                requesting access to EduVision.
            </p>

        </div>


        <div class="table">

            <table>

                <tr>
                    <th>School ID</th>
                    <th>School</th>
                    <th>Admin ID</th>
                    <th>Status</th>
                    <th>Action</th>
                </tr>


                ${schools.length

                    ? schools.map(school => `

                        <tr>

                            <td>
                                ${safe(
                                    school.school_id
                                )}
                            </td>

                            <td>
                                ${safe(
                                    school.school_name
                                )}
                            </td>

                            <td>
                                ${safe(
                                    school.admin_id
                                )}
                            </td>

                            <td>
                                ${safe(
                                    school.approval_status
                                )}
                            </td>

                            <td>

                                <button
                                    onclick="setSchoolStatus(
                                        '${safe(
                                            school.school_id
                                        )}',
                                        'Approved'
                                    )"
                                >
                                    Approve
                                </button>

                                <button
                                    onclick="setSchoolStatus(
                                        '${safe(
                                            school.school_id
                                        )}',
                                        'Rejected'
                                    )"
                                >
                                    Reject
                                </button>

                            </td>

                        </tr>

                    `).join("")

                    : `

                    <tr>
                        <td colspan="5">
                            No schools found.
                        </td>
                    </tr>

                    `
                }

            </table>

        </div>
    `;
}


/* =========================================================
   APPROVE / REJECT SCHOOL
========================================================= */

async function setSchoolStatus(
    schoolId,
    status
) {

    try {

        const result =
            await db
                .from("schools")
                .update({

                    approval_status:
                        status,

                    approved_at:
                        status ===
                        "Approved"

                            ? new Date()
                                .toISOString()

                            : null,

                    approved_by:
                        "EduVision Admin"
                })
                .eq(
                    "school_id",
                    schoolId
                );


        if (result.error) {
            throw result.error;
        }


        await schoolsPage();

    }

    catch (error) {

        alert(
            error.message ||
            "Could not update school."
        );
    }
}


/* =========================================================
   STARTUP
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        if (S) {

            start(S);

        }

        else {

            $("#app").classList.add(
                "hidden"
            );

            $("#login").classList.add(
                "hidden"
            );

            $("#home").classList.remove(
                "hidden"
            );
        }
    }
);
