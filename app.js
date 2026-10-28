const C = window.EDUVISION_CONFIG || {};

const ok =
    C.SUPABASE_URL &&
    C.SUPABASE_ANON_KEY &&
    !C.SUPABASE_URL.includes("PASTE_");

const db =
    ok && window.supabase
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
   GLOBAL VARIABLES
========================================================= */

let faceModelsReady = false;
let cameraStream = null;

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

    return String(value ?? "")
        .replace(
            /[&<>"']/g,
            char => ({
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#39;"
            }[char])
        );
}


function field(
    label,
    name,
    type = "text"
) {

    return `
        <div class="field">

            <label>
                ${safe(label)}
            </label>

            <input
                required
                name="${safe(name)}"
                type="${safe(type)}"
                autocomplete="off"
            >

        </div>
    `;
}


async function hash(text) {

    const data =
        await crypto.subtle.digest(
            "SHA-256",
            new TextEncoder().encode(text)
        );

    return [
        ...new Uint8Array(data)
    ]
        .map(
            value =>
                value
                    .toString(16)
                    .padStart(2, "0")
        )
        .join("");
}


function values() {

    const form = $("#form");

    if (!form) {
        return {};
    }

    return Object.fromEntries(
        [
            ...form.querySelectorAll("input")
        ].map(input => [
            input.name,
            input.value.trim()
        ])
    );
}


function message(text = "") {

    const element = $("#msg");

    if (element) {
        element.textContent = text;
    }
}


function localDate(
    date = new Date()
) {

    const year =
        date.getFullYear();

    const month =
        String(
            date.getMonth() + 1
        ).padStart(2, "0");

    const day =
        String(
            date.getDate()
        ).padStart(2, "0");

    return `${year}-${month}-${day}`;
}


function stats(rows = []) {

    return `

        <div class="stats">

            ${rows.map(
                ([label, value]) => `

                    <div class="box">

                        <span class="muted">
                            ${safe(label)}
                        </span>

                        <b>
                            ${safe(value)}
                        </b>

                    </div>

                `
            ).join("")}

        </div>

    `;
}


/* =========================================================
   SCREEN CONTROL
========================================================= */

function showView(name) {

    const views = {

        home:
            $("#home"),

        selection:
            $("#selection"),

        login:
            $("#login"),

        app:
            $("#app")
    };


    Object.entries(views)
        .forEach(
            ([key, element]) => {

                if (!element) {
                    return;
                }


                if (key === name) {

                    element.classList.remove(
                        "hidden"
                    );

                    element.style.display =
                        key === "app"
                            ? "grid"
                            : "flex";

                }

                else {

                    element.classList.add(
                        "hidden"
                    );

                    element.style.display =
                        "none";
                }
            }
        );
}


function showSelection() {

    stopCamera();

    showView(
        "selection"
    );
}


function goHome() {

    stopCamera();

    showView(
        "home"
    );
}


/* =========================================================
   TOAST NOTIFICATIONS
========================================================= */

function initUiLayer() {

    if (
        document.getElementById(
            "toastContainer"
        )
    ) {
        return;
    }


    const container =
        document.createElement(
            "div"
        );


    container.id =
        "toastContainer";

    container.className =
        "toast-container";

    container.setAttribute(
        "aria-live",
        "polite"
    );


    document.body.appendChild(
        container
    );
}


function showToast(
    text,
    type = "success"
) {

    if (!text) {
        return;
    }


    initUiLayer();


    const toast =
        document.createElement(
            "div"
        );


    toast.className =
        `toast ${type}`;

    toast.textContent =
        text;


    document
        .getElementById(
            "toastContainer"
        )
        .appendChild(
            toast
        );


    requestAnimationFrame(
        () =>
            toast.classList.add(
                "show"
            )
    );


    setTimeout(
        () => {

            toast.classList.remove(
                "show"
            );


            setTimeout(
                () =>
                    toast.remove(),
                220
            );

        },

        2800
    );
}


/* =========================================================
   LOADING / EMPTY UI
========================================================= */

function renderLoading(
    label = "Loading data"
) {

    return `

        <div class="loading-shell">

            <div class="loading-label">
                ${safe(label)}
            </div>

            <div class="loading-skeleton">

                <div class="loading-line"></div>

                <div class="loading-line short"></div>

                <div class="loading-line"></div>

                <div class="loading-line short"></div>

            </div>

        </div>

    `;
}


function emptyState(
    title,
    description
) {

    return `

        <div class="empty-state">

            <div class="empty-state-icon">
                ○
            </div>

            <h4>
                ${safe(title)}
            </h4>

            <p>
                ${safe(description)}
            </p>

        </div>

    `;
}


/* =========================================================
   SEARCH
========================================================= */

function renderSearchBar(
    id,
    placeholder
) {

    return `

        <div class="tools search-bar">

            <input
                id="${safe(id)}"
                class="table-search"
                type="search"
                placeholder="${safe(placeholder)}"
            >

        </div>

    `;
}


function bindSimpleSearch(
    inputId,
    tableSelector
) {

    const input =
        document.getElementById(
            inputId
        );

    const table =
        document.querySelector(
            tableSelector
        );


    if (
        !input ||
        !table
    ) {
        return;
    }


    input.addEventListener(
        "input",

        () => {

            const query =
                input.value
                    .trim()
                    .toLowerCase();


            table
                .querySelectorAll(
                    "tr[data-search-item]"
                )
                .forEach(
                    row => {

                        const text =
                            row.textContent
                                .toLowerCase();


                        row.style.display =
                            !query ||
                            text.includes(query)

                                ? ""

                                : "none";
                    }
                );
        }
    );
}


/* =========================================================
   CSV EXPORT
========================================================= */

function exportCsvRows(
    rows,
    filename = "attendance.csv"
) {

    if (
        !Array.isArray(rows) ||
        rows.length === 0
    ) {

        showToast(
            "No data to export.",
            "error"
        );

        return;
    }


    const headers =
        Object.keys(
            rows[0]
        );


    const csv = [

        headers.join(","),

        ...rows.map(
            row =>

                headers
                    .map(
                        header => {

                            const value =
                                String(
                                    row[header] ??
                                    ""
                                )
                                    .replace(
                                        /"/g,
                                        '""'
                                    );


                            return `"${value}"`;
                        }
                    )
                    .join(",")
        )

    ].join("\n");


    const blob =
        new Blob(
            [csv],
            {
                type:
                    "text/csv;charset=utf-8"
            }
        );


    const url =
        URL.createObjectURL(
            blob
        );


    const link =
        document.createElement(
            "a"
        );


    link.href =
        url;

    link.download =
        filename;


    document.body.appendChild(
        link
    );


    link.click();

    link.remove();


    URL.revokeObjectURL(
        url
    );


    showToast(
        "CSV export started.",
        "success"
    );
}


/* =========================================================
   DATABASE ERROR
========================================================= */

function showDatabaseError(
    error
) {

    console.error(
        error
    );


    const pageElement =
        $("#page");


    if (!pageElement) {
        return;
    }


    pageElement.innerHTML = `

        <div class="box">

            <div class="inline-status error">

                <span class="inline-status-icon">
                    !
                </span>

                <span>
                    Could not load this page.
                </span>

            </div>


            <h3>
                Database Error
            </h3>


            <p class="muted">

                ${safe(
                    error?.message ||
                    "Please check the database connection."
                )}

            </p>


            <button
                class="no-zoom"
                onclick="page('Dashboard')"
            >
                Back to Dashboard
            </button>

        </div>

    `;
}


/* =========================================================
   LOGIN SCREEN
========================================================= */

function login(mode) {

    stopCamera();

    showView(
        "login"
    );


    const form =
        $("#form");


    message("");


    /* -------------------------
       SCHOOL ADMIN
    ------------------------- */

    if (
        mode === "admin"
    ) {

        $("#lt").textContent =
            "School Admin Login";


        form.innerHTML =

            field(
                "School ID",
                "school"
            ) +

            field(
                "Admin ID",
                "id"
            ) +

            field(
                "Password",
                "pw",
                "password"
            ) +

            `

            <button
                id="loginButton"
                type="button"
            >
                Sign In
            </button>

            `;


        $("#loginButton")
            .onclick =
            schoolAdminLogin;


        return;
    }


    /* -------------------------
       TEACHER
    ------------------------- */

    if (
        mode === "teacher"
    ) {

        $("#lt").textContent =
            "Teacher Login";


        form.innerHTML =

            field(
                "School ID",
                "school"
            ) +

            field(
                "Teacher ID",
                "id"
            ) +

            field(
                "Password",
                "pw",
                "password"
            ) +

            `

            <button
                id="loginButton"
                type="button"
            >
                Sign In
            </button>

            `;


        $("#loginButton")
            .onclick =
            teacherLogin;


        return;
    }


    /* -------------------------
       EDUVISION ADMIN
    ------------------------- */

    if (
        mode === "evadmin"
    ) {

        $("#lt").textContent =
            "EduVision Admin";


        form.innerHTML =

            field(
                "Admin ID",
                "admin_id"
            ) +

            field(
                "Password",
                "password",
                "password"
            ) +

            `

            <button
                id="loginButton"
                type="button"
            >
                Sign In
            </button>

            `;


        $("#loginButton")
            .onclick =
            eduvisionAdminLogin;


        return;
    }


    /* -------------------------
       REGISTER SCHOOL
    ------------------------- */

    if (
        mode === "register"
    ) {

        $("#lt").textContent =
            "Register School";


        form.innerHTML =

            field(
                "School Name",
                "name"
            ) +

            field(
                "School ID",
                "school"
            ) +

            field(
                "Admin ID",
                "id"
            ) +

            field(
                "Password",
                "pw",
                "password"
            ) +

            `

            <button
                id="loginButton"
                type="button"
            >
                Register School
            </button>

            `;


        $("#loginButton")
            .onclick =
            registerSchool;
    }
}


/* =========================================================
   SCHOOL ADMIN LOGIN
========================================================= */

async function schoolAdminLogin() {

    if (!db) {

        message(
            "Database connection is not configured."
        );

        return;
    }


    const button =
        $("#loginButton");


    try {

        button.disabled =
            true;

        button.textContent =
            "Signing In...";


        message("");


        const input =
            values();


        if (
            !input.school ||
            !input.id ||
            !input.pw
        ) {

            message(
                "Please fill in all fields."
            );

            return;
        }


        const {
            data,
            error
        } =
            await db
                .from(
                    "schools"
                )
                .select("*")
                .eq(
                    "school_id",
                    input.school
                )
                .eq(
                    "admin_id",
                    input.id
                )
                .maybeSingle();


        if (error) {
            throw error;
        }


        if (!data) {

            message(
                "School ID or Admin ID is incorrect."
            );

            return;
        }


        if (
            data.approval_status !==
            "Approved"
        ) {

            message(
                "This school has not been approved yet."
            );

            return;
        }


        const password =
            await hash(
                input.pw
            );


        if (
            password !==
            data.admin_password_hash
        ) {

            message(
                "Incorrect password."
            );

            return;
        }


        loginSuccess({

            role:
                "School Admin",

            school:
                data.school_id,

            name:
                data.school_name
        });

    }

    catch (error) {

        console.error(
            error
        );


        message(
            "Login failed: " +
            (
                error?.message ||
                "Database error"
            )
        );

    }

    finally {

        if (button) {

            button.disabled =
                false;

            button.textContent =
                "Sign In";
        }
    }
}


/* =========================================================
   TEACHER LOGIN
========================================================= */

async function teacherLogin() {

    if (!db) {

        message(
            "Database connection is not configured."
        );

        return;
    }


    const button =
        $("#loginButton");


    try {

        button.disabled =
            true;

        button.textContent =
            "Signing In...";


        message("");


        const input =
            values();


        if (
            !input.school ||
            !input.id ||
            !input.pw
        ) {

            message(
                "Please fill in all fields."
            );

            return;
        }


        const {
            data,
            error
        } =
            await db
                .from(
                    "teachers"
                )
                .select("*")
                .eq(
                    "school_id",
                    input.school
                )
                .eq(
                    "teacher_id",
                    input.id
                )
                .maybeSingle();


        if (error) {
            throw error;
        }


        if (!data) {

            message(
                "Teacher account not found."
            );

            return;
        }


        if (
            data.enabled === false
        ) {

            message(
                "This teacher account is disabled."
            );

            return;
        }


        if (
            await hash(
                input.pw
            ) !==
            data.password_hash
        ) {

            message(
                "Incorrect password."
            );

            return;
        }


        loginSuccess({

            role:
                "Teacher",

            school:
                data.school_id,

            name:
                data.teacher_name
        });

    }

    catch (error) {

        console.error(
            error
        );


        message(
            "Teacher login failed: " +
            (
                error?.message ||
                "Database error"
            )
        );

    }

    finally {

        if (button) {

            button.disabled =
                false;

            button.textContent =
                "Sign In";
        }
    }
}


/* =========================================================
   EDUVISION ADMIN LOGIN
========================================================= */

async function eduvisionAdminLogin() {

    const button =
        $("#loginButton");


    try {

        button.disabled =
            true;

        button.textContent =
            "Signing In...";


        message("");


        const input =
            values();


        if (
            !input.admin_id ||
            !input.password
        ) {

            message(
                "Please fill in all fields."
            );

            return;
        }


        const response =
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
                        JSON.stringify({

                            admin_id:
                                input.admin_id,

                            password:
                                input.password
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

            role:
                "EduVision Admin",

            name:
                "EduVision Admin"
        });

    }

    catch (error) {

        console.error(
            error
        );


        message(
            "Could not connect to EduVision."
        );

    }

    finally {

        if (button) {

            button.disabled =
                false;

            button.textContent =
                "Sign In";
        }
    }
}


/* =========================================================
   REGISTER SCHOOL
========================================================= */

async function registerSchool() {

    if (!db) {

        message(
            "Database connection is not configured."
        );

        return;
    }


    const button =
        $("#loginButton");


    try {

        button.disabled =
            true;

        button.textContent =
            "Submitting...";


        message("");


        const input =
            values();


        if (
            !input.name ||
            !input.school ||
            !input.id ||
            !input.pw
        ) {

            message(
                "Please fill in all fields."
            );

            return;
        }


        const duplicate =
            await db
                .from(
                    "schools"
                )
                .select(
                    "school_id"
                )
                .eq(
                    "school_id",
                    input.school
                )
                .maybeSingle();


        if (
            duplicate.error
        ) {
            throw duplicate.error;
        }


        if (
            duplicate.data
        ) {

            message(
                "That School ID is already registered."
            );

            return;
        }


        const result =
            await db
                .from(
                    "schools"
                )
                .insert({

                    school_name:
                        input.name,

                    school_id:
                        input.school,

                    admin_id:
                        input.id,

                    admin_password_hash:
                        await hash(
                            input.pw
                        ),

                    approval_status:
                        "Pending"
                });


        if (
            result.error
        ) {
            throw result.error;
        }


        message(
            "Registration submitted. Wait for EduVision Admin approval."
        );


        showToast(
            "School registration submitted.",
            "success"
        );

    }

    catch (error) {

        console.error(
            error
        );


        message(
            error?.message ||
            "Registration failed."
        );

    }

    finally {

        if (button) {

            button.disabled =
                false;

            button.textContent =
                "Register School";
        }
    }
}


/* =========================================================
   LOGIN SUCCESS
========================================================= */

function loginSuccess(
    session
) {

    S =
        session;


    localStorage.setItem(
        "evs",
        JSON.stringify(
            session
        )
    );


    showToast(
        `Welcome, ${session.name}.`,
        "success"
    );


    start(
        session
    );
}


/* =========================================================
   START APP
========================================================= */

function start(
    session
) {

    S =
        session;


    showView(
        "app"
    );


    const who =
        $("#who");


    who.innerHTML = `

        <b>
            ${safe(
                session.name
            )}
        </b>

        <br>

        ${safe(
            session.role
        )}

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


    else if (
        session.role ===
        "Teacher"
    ) {

        pages = [

            "Dashboard",

            "Students",

            "Smart Attendance",

            "Smart Occupancy",

            "Reports"
        ];
    }


    $("#nav").innerHTML =

        pages.map(
            name => `

                <button
                    class="nav-button"
                    data-page="${safe(name)}"
                    onclick="page('${safe(name)}')"
                >

                    <span>
                        ${safe(name)}
                    </span>

                </button>

            `
        ).join("");


    page(
        "Dashboard"
    );
}


/* =========================================================
   LOGOUT
========================================================= */

function logout() {

    stopCamera();


    localStorage.removeItem(
        "evs"
    );


    S =
        null;


    showView(
        "home"
    );


    showToast(
        "Logged out.",
        "info"
    );
}


/* =========================================================
   ACTIVE NAVIGATION
========================================================= */

function setActiveNav(
    name
) {

    document
        .querySelectorAll(
            "#nav .nav-button"
        )
        .forEach(
            button => {

                const active =
                    button.dataset.page ===
                    name;


                button.classList.toggle(
                    "active",
                    active
                );


                if (active) {

                    button.setAttribute(
                        "aria-current",
                        "page"
                    );

                }

                else {

                    button.removeAttribute(
                        "aria-current"
                    );
                }
            }
        );
}


/* =========================================================
   PAGE ROUTER
========================================================= */

async function page(
    name
) {

    stopCamera();


    setActiveNav(
        name
    );


    $("#title").textContent =
        name;


    $("#page").innerHTML =
        renderLoading(
            `Loading ${name}`
        );


    try {

        if (
            name === "Dashboard"
        ) {

            await dashboardPage();

            return;
        }


        if (
            name === "Students"
        ) {

            await studentsPage();

            return;
        }


        if (
            name === "Teachers"
        ) {

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


        if (
            name === "Reports"
        ) {

            await reportsPage();

            return;
        }


        if (
            name === "Schools"
        ) {

            await schoolsPage();

            return;
        }


        if (
            name === "Settings"
        ) {

            settingsPage();

            return;
        }


        $("#page").innerHTML = `

            <div class="box">

                ${emptyState(
                    "Page not found",
                    "This page is not available."
                )}

            </div>

        `;

    }

    catch (error) {

        showDatabaseError(
            error
        );
    }
}
/* =========================================================
   DASHBOARD
========================================================= */

async function dashboardPage() {

    if (!db) {

        throw new Error(
            "Database connection is not available."
        );
    }


    /* =====================================================
       EDUVISION ADMIN DASHBOARD
    ===================================================== */

    if (
        S.role ===
        "EduVision Admin"
    ) {

        const {
            data,
            error
        } =
            await db
                .from("schools")
                .select(
                    "school_id, school_name, approval_status, created_at"
                );


        if (error) {
            throw error;
        }


        const schools =
            Array.isArray(data)
                ? data
                : [];


        const pending =
            schools.filter(
                school =>
                    school.approval_status ===
                    "Pending"
            ).length;


        const approved =
            schools.filter(
                school =>
                    school.approval_status ===
                    "Approved"
            ).length;


        const rejected =
            schools.filter(
                school =>
                    school.approval_status ===
                    "Rejected"
            ).length;


        const recent =
            [...schools]
                .sort(
                    (a, b) =>
                        new Date(
                            b.created_at || 0
                        ) -
                        new Date(
                            a.created_at || 0
                        )
                )
                .slice(
                    0,
                    5
                );


        $("#page").innerHTML = `

            ${stats([

                [
                    "Pending Schools",
                    pending
                ],

                [
                    "Approved Schools",
                    approved
                ],

                [
                    "Total Schools",
                    schools.length
                ],

                [
                    "System",
                    "Online"
                ]

            ])}


            <div
                class="box"
                style="margin-top:18px"
            >

                <h3>
                    EduVision Overview
                </h3>


                <p class="muted">
                    Review school registrations
                    and manage access to EduVision.
                </p>


                <div class="tools">

                    <button
                        class="no-zoom"
                        onclick="page('Schools')"
                    >
                        Manage Schools
                    </button>

                </div>

            </div>


            <div
                class="box"
                style="margin-top:18px"
            >

                <h3>
                    Recent Registrations
                </h3>


                ${
                    recent.length

                        ? `

                        <div class="table">

                            <table>

                                <thead>

                                    <tr>

                                        <th>
                                            School
                                        </th>

                                        <th>
                                            School ID
                                        </th>

                                        <th>
                                            Status
                                        </th>

                                    </tr>

                                </thead>


                                <tbody>

                                    ${recent.map(
                                        school => `

                                            <tr>

                                                <td>
                                                    ${safe(
                                                        school.school_name
                                                    )}
                                                </td>

                                                <td>
                                                    ${safe(
                                                        school.school_id
                                                    )}
                                                </td>

                                                <td>
                                                    ${safe(
                                                        school.approval_status
                                                    )}
                                                </td>

                                            </tr>

                                        `
                                    ).join("")}

                                </tbody>

                            </table>

                        </div>

                        `

                        :

                        emptyState(
                            "No schools yet",
                            "School registrations will appear here."
                        )
                }

            </div>


            ${
                rejected > 0

                    ? `

                    <div
                        class="inline-status info"
                        style="margin-top:18px"
                    >

                        <span
                            class="inline-status-icon"
                        >
                            i
                        </span>

                        <span>
                            ${safe(rejected)}
                            rejected school
                            ${
                                rejected === 1
                                    ? "registration"
                                    : "registrations"
                            }.
                        </span>

                    </div>

                    `

                    : ""
            }

        `;


        return;
    }


    /* =====================================================
       SCHOOL ADMIN / TEACHER DASHBOARD
    ===================================================== */

    if (
        !S.school
    ) {

        throw new Error(
            "School information is missing from this session."
        );
    }


    const today =
        localDate();


    const [
        studentsResult,
        teachersResult,
        attendanceResult
    ] =
        await Promise.all([

            db
                .from("students")
                .select(
                    "*",
                    {
                        count: "exact",
                        head: true
                    }
                )
                .eq(
                    "school_id",
                    S.school
                )
                .eq(
                    "status",
                    "Active"
                ),


            db
                .from("teachers")
                .select(
                    "*",
                    {
                        count: "exact",
                        head: true
                    }
                )
                .eq(
                    "school_id",
                    S.school
                )
                .eq(
                    "enabled",
                    true
                ),


            db
                .from("attendance")
                .select(
                    "*",
                    {
                        count: "exact",
                        head: true
                    }
                )
                .eq(
                    "school_id",
                    S.school
                )
                .eq(
                    "attendance_date",
                    today
                )

        ]);


    if (
        studentsResult.error
    ) {
        throw studentsResult.error;
    }


    if (
        teachersResult.error
    ) {
        throw teachersResult.error;
    }


    if (
        attendanceResult.error
    ) {
        throw attendanceResult.error;
    }


    const studentCount =
        studentsResult.count || 0;


    const teacherCount =
        teachersResult.count || 0;


    const markedToday =
        attendanceResult.count || 0;


    let attendancePercent =
        0;


    if (
        studentCount > 0
    ) {

        attendancePercent =
            Math.min(
                100,
                Math.round(
                    (
                        markedToday /
                        studentCount
                    ) * 100
                )
            );
    }


    $("#page").innerHTML = `

        ${stats([

            [
                "Active Students",
                studentCount
            ],

            [
                "Teachers",
                teacherCount
            ],

            [
                "Marked Today",
                markedToday
            ],

            [
                "System",
                "Online"
            ]

        ])}


        <div
            class="box"
            style="margin-top:18px"
        >

            <h3>
                Today's Attendance
            </h3>


            <p class="muted">
                ${safe(markedToday)}
                of
                ${safe(studentCount)}
                active students have attendance
                recorded today.
            </p>


            <div class="progress-block">

                <div class="progress-header">

                    <span>
                        Attendance progress
                    </span>

                    <b>
                        ${safe(attendancePercent)}%
                    </b>

                </div>


                <div class="progress-track">

                    <div
                        class="progress-fill"
                        style="
                            width:
                            ${safe(attendancePercent)}%
                        "
                    ></div>

                </div>

            </div>


            <div class="tools">

                <button
                    class="no-zoom"
                    onclick="page('Smart Attendance')"
                >
                    Open Smart Attendance
                </button>


                <button
                    class="no-zoom"
                    onclick="page('Reports')"
                >
                    View Reports
                </button>

            </div>

        </div>


        <div
            class="box"
            style="margin-top:18px"
        >

            <h3>
                Classroom Tools
            </h3>


            <p class="muted">
                EduVision helps reduce time spent
                on routine classroom management.
            </p>


            <div class="tools">

                <button
                    class="no-zoom"
                    onclick="page('Students')"
                >
                    Students
                </button>


                <button
                    class="no-zoom"
                    onclick="page('Smart Occupancy')"
                >
                    Live Classroom
                </button>

            </div>

        </div>

    `;
}


/* =========================================================
   STUDENTS PAGE
========================================================= */

async function studentsPage() {

    if (!db) {

        throw new Error(
            "Database is not configured."
        );
    }


    if (
        !S ||
        !S.school
    ) {

        throw new Error(
            "School information is missing."
        );
    }


    const [
        studentsResult,
        facesResult
    ] =
        await Promise.all([

            db
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
                ),


            db
                .from("face_profiles")
                .select(
                    "student_id"
                )
                .eq(
                    "school_id",
                    S.school
                )

        ]);


    if (
        studentsResult.error
    ) {
        throw studentsResult.error;
    }


    const students =
        Array.isArray(
            studentsResult.data
        )

            ? studentsResult.data

            : [];


    const registered =
        new Set();


    if (
        !facesResult.error &&
        Array.isArray(
            facesResult.data
        )
    ) {

        facesResult.data
            .forEach(
                face => {

                    if (
                        face.student_id
                    ) {

                        registered.add(
                            String(
                                face.student_id
                            )
                        );
                    }
                }
            );
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


                    <p class="muted">
                        Add a student to your
                        EduVision school.
                    </p>


                    <div class="tools">

                        <input
                            id="studentId"
                            placeholder="Student ID"
                            autocomplete="off"
                        >


                        <input
                            id="studentName"
                            placeholder="Student Name"
                            autocomplete="off"
                        >


                        <input
                            id="studentClass"
                            placeholder="Class"
                            autocomplete="off"
                        >


                        <input
                            id="studentRoll"
                            placeholder="Roll No"
                            autocomplete="off"
                        >


                        <button
                            class="no-zoom"
                            onclick="addStudent()"
                        >
                            Add Student
                        </button>

                    </div>

                </div>

                `

                : ""
        }


        <div
            class="box"
            style="margin-top:18px"
        >

            <div
                style="
                    display:flex;
                    justify-content:space-between;
                    gap:12px;
                    align-items:center;
                    flex-wrap:wrap;
                "
            >

                <div>

                    <h3
                        style="
                            margin-bottom:4px;
                        "
                    >
                        Students
                    </h3>

                    <span class="muted">
                        ${safe(students.length)}
                        registered
                    </span>

                </div>

            </div>


            ${renderSearchBar(
                "studentSearch",
                "Search students..."
            )}


            ${
                students.length

                    ? `

                    <div
                        class="table"
                        id="studentsTable"
                    >

                        <table>

                            <thead>

                                <tr>

                                    <th>
                                        ID
                                    </th>

                                    <th>
                                        Name
                                    </th>

                                    <th>
                                        Class
                                    </th>

                                    <th>
                                        Roll
                                    </th>

                                    <th>
                                        Status
                                    </th>

                                    <th>
                                        Smart Attendance
                                    </th>
                                    <th>
                                         Action
                                    </th>

                                </tr>

                            </thead>


                            <tbody>

                                ${students.map(
                                    student => {

                                        const hasFace =
                                            registered.has(
                                                String(
                                                    student.student_id
                                                )
                                            );


                                        return `

                                            <tr
                                                data-search-item
                                            >

                                                <td>
                                                    ${safe(
                                                        student.student_id
                                                    )}
                                                </td>


                                                <td>
                                                    <b>
                                                        ${safe(
                                                            student.name
                                                        )}
                                                    </b>
                                                </td>


                                                <td>
                                                    ${safe(
                                                        student.class_name
                                                    )}
                                                </td>


                                                <td>
                                                    ${safe(
                                                        student.roll_no ||
                                                        "-"
                                                    )}
                                                </td>


                                                <td>

                                                    ${
                                                        student.status ===
                                                        "Active"

                                                            ? `

                                                            <span
                                                                style="
                                                                    color:#5ad4a4;
                                                                    font-weight:700;
                                                                "
                                                            >
                                                                Active
                                                            </span>

                                                            `

                                                            : safe(
                                                                student.status
                                                            )
                                                    }

                                                </td>


                                                <td>

                                                    ${
                                                        hasFace

                                                            ? `

                                                            <span
                                                                style="
                                                                    color:#5ad4a4;
                                                                    font-weight:700;
                                                                    margin-right:8px;
                                                                "
                                                            >
                                                                ✓ Registered
                                                            </span>


                                                            ${
                                                                S.role ===
                                                                "School Admin"

                                                                    ? `

                                                                    <button
                                                                        class="small-button no-zoom"
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
                                                                    class="small-button no-zoom"
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

                                        `;
                                    }
                                ).join("")}

                            </tbody>

                        </table>

                    </div>

                    `

                    :

                    emptyState(
                        "No students yet",
                        S.role === "School Admin"
                            ? "Add your first student using the form above."
                            : "No students have been added to this school."
                    )
            }

        </div>


        <div
            class="inline-status info"
            style="margin-top:18px"
        >

            <span
                class="inline-status-icon"
            >
                i
            </span>

            <span>
                Smart Attendance face profiles
                should only be registered with
                appropriate permission and consent.
            </span>

        </div>

    `;


    bindSimpleSearch(
        "studentSearch",
        "#studentsTable"
    );
}


/* =========================================================
   ADD STUDENT
========================================================= */

async function addStudent() {

    if (
        S.role !==
        "School Admin"
    ) {

        showToast(
            "School Admin access required.",
            "error"
        );

        return;
    }


    const studentIdElement =
        $("#studentId");

    const studentNameElement =
        $("#studentName");

    const studentClassElement =
        $("#studentClass");

    const studentRollElement =
        $("#studentRoll");


    if (
        !studentIdElement ||
        !studentNameElement ||
        !studentClassElement
    ) {

        return;
    }


    const studentId =
        studentIdElement
            .value
            .trim();


    const name =
        studentNameElement
            .value
            .trim();


    const className =
        studentClassElement
            .value
            .trim();


    const roll =
        studentRollElement
            ? studentRollElement
                .value
                .trim()

            : "";


    if (
        !studentId ||
        !name ||
        !className
    ) {

        showToast(
            "Enter Student ID, Name and Class.",
            "error"
        );

        return;
    }


    try {

        const existing =
            await db
                .from("students")
                .select(
                    "student_id"
                )
                .eq(
                    "school_id",
                    S.school
                )
                .eq(
                    "student_id",
                    studentId
                )
                .maybeSingle();


        if (
            existing.error
        ) {
            throw existing.error;
        }


        if (
            existing.data
        ) {

            showToast(
                "That Student ID already exists.",
                "error"
            );

            return;
        }


        const result =
            await db
                .from("students")
                .insert({

                    school_id:
                        S.school,

                    student_id:
                        studentId,

                    name:
                        name,

                    class_name:
                        className,

                    roll_no:
                        roll,

                    status:
                        "Active"
                });


        if (
            result.error
        ) {
            throw result.error;
        }


        showToast(
            `${name} added successfully.`,
            "success"
        );


        await studentsPage();

    }

    catch (error) {

        console.error(
            error
        );


        showToast(
            error?.message ||
            "Could not add student.",
            "error"
        );
    }
}


/* =========================================================
   FACE MODEL
========================================================= */

async function loadFaceModels() {

    if (
        faceModelsReady
    ) {

        return true;
    }


    if (
        !window.faceapi
    ) {

        throw new Error(
            "Smart Attendance library did not load."
        );
    }


    const status =
        $("#faceStatus");


    if (status) {

        status.innerHTML = `

            <div class="inline-status info">

                <span
                    class="inline-status-icon"
                >
                    AI
                </span>

                <span>
                    Loading Smart Attendance...
                </span>

            </div>

        `;
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


    faceModelsReady =
        true;


    if (status) {

        status.innerHTML = `

            <div class="inline-status success">

                <span
                    class="inline-status-icon"
                >
                    ✓
                </span>

                <span>
                    Smart Attendance ready.
                </span>

            </div>

        `;
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
        !navigator.mediaDevices
            .getUserMedia
    ) {

        throw new Error(
            "Camera access is not supported by this browser."
        );
    }


    const container =
        document.getElementById(
            containerId
        );


    if (!container) {

        throw new Error(
            "Camera area could not be found."
        );
    }


    cameraStream =
        await navigator.mediaDevices
            .getUserMedia({

                video: {

                    facingMode:
                        "user",

                    width: {
                        ideal:
                            960
                    },

                    height: {
                        ideal:
                            540
                    }
                },

                audio:
                    false
            });


    container.innerHTML = `

        <video
            id="${safe(containerId)}Video"
            autoplay
            muted
            playsinline
        ></video>

        <canvas
            id="${safe(containerId)}Canvas"
        ></canvas>

    `;


    container.style.position =
        "relative";


    const video =
        document.getElementById(
            containerId +
            "Video"
        );


    if (!video) {

        throw new Error(
            "Camera video could not be created."
        );
    }


    video.srcObject =
        cameraStream;


    await video.play();


    return video;
}


/* =========================================================
   STOP CAMERA / AI
========================================================= */

function stopCamera() {

    if (
        attendanceTimer
    ) {

        clearInterval(
            attendanceTimer
        );

        attendanceTimer =
            null;
    }


    if (
        occupancyTimer
    ) {

        clearInterval(
            occupancyTimer
        );

        occupancyTimer =
            null;
    }


    attendanceBusy =
        false;

    occupancyBusy =
        false;


    if (
        cameraStream
    ) {

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


/* =========================================================
   REGISTER FACE PAGE
========================================================= */

async function registerFace(
    studentId
) {

    stopCamera();


    if (
        S.role !==
        "School Admin"
    ) {

        showToast(
            "School Admin access required.",
            "error"
        );

        return;
    }


    try {

        const {
            data,
            error
        } =
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


        if (error) {
            throw error;
        }


        if (!data) {

            showToast(
                "Student not found.",
                "error"
            );

            return;
        }


        const student =
            data;


        $("#title").textContent =
            "Register Face";


        setActiveNav(
            "Students"
        );


        $("#page").innerHTML = `

            <div class="box">

                <h3>
                    Register Smart Attendance Profile
                </h3>


                <p>

                    <b>
                        ${safe(
                            student.name
                        )}
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


                <div class="inline-status info">

                    <span
                        class="inline-status-icon"
                    >
                        i
                    </span>

                    <span>
                        Register only a consenting
                        participant with appropriate
                        school or guardian permission.
                        Camera frames are used to
                        calculate the recognition
                        profile.
                    </span>

                </div>


                <label
                    class="consent-row"
                >

                    <input
                        id="faceConsent"
                        type="checkbox"
                    >

                    <span>
                        Appropriate permission has
                        been obtained for this
                        Smart Attendance profile.
                    </span>

                </label>


                <div
                    id="registerCamera"
                    class="camera"
                >
                    Camera is off
                </div>


                <div class="tools">

                    <button
                        class="no-zoom"
                        onclick="captureStudentFace(
                            '${safe(
                                student.student_id
                            )}'
                        )"
                    >
                        Start Camera & Register
                    </button>


                    <button
                        class="no-zoom"
                        onclick="page('Students')"
                    >
                        Cancel
                    </button>

                </div>


                <div
                    id="faceStatus"
                >

                    <div class="inline-status info">

                        <span
                            class="inline-status-icon"
                        >
                            i
                        </span>

                        <span>
                            Ready to register.
                        </span>

                    </div>

                </div>

            </div>

        `;

    }

    catch (error) {

        showDatabaseError(
            error
        );
    }
}


/* =========================================================
   CAPTURE STUDENT FACE
========================================================= */

async function captureStudentFace(
    studentId
) {

    const status =
        $("#faceStatus");


    const consent =
        $("#faceConsent");


    if (
        !consent ||
        !consent.checked
    ) {

        showToast(
            "Confirm permission before registering the face profile.",
            "error"
        );

        return;
    }


    try {

        await loadFaceModels();


        if (status) {

            status.innerHTML = `

                <div class="inline-status info">

                    <span
                        class="inline-status-icon"
                    >
                        •
                    </span>

                    <span>
                        Starting camera...
                    </span>

                </div>

            `;
        }


        const video =
            await openCamera(
                "registerCamera"
            );


        if (status) {

            status.innerHTML = `

                <div class="inline-status info">

                    <span
                        class="inline-status-icon"
                    >
                        •
                    </span>

                    <span>
                        Keep exactly one face visible
                        and look toward the camera.
                    </span>

                </div>

            `;
        }


        await new Promise(
            resolve =>
                setTimeout(
                    resolve,
                    1600
                )
        );


        const descriptors =
            [];


        /*
            Take several samples instead of
            relying on one single camera frame.
        */

        for (
            let attempt = 0;
            attempt < 5;
            attempt++
        ) {

            const detections =
                await faceapi
                    .detectAllFaces(

                        video,

                        new faceapi
                            .TinyFaceDetectorOptions({

                                inputSize:
                                    320,

                                scoreThreshold:
                                    0.5
                            })
                    )
                    .withFaceLandmarks()
                    .withFaceDescriptors();


            if (
                detections.length > 1
            ) {

                stopCamera();


                throw new Error(
                    "More than one face detected. Keep one person at a time."
                );
            }


            if (
                detections.length === 1
            ) {

                descriptors.push(
                    Array.from(
                        detections[0]
                            .descriptor
                    )
                );
            }


            if (
                status
            ) {

                status.innerHTML = `

                    <div class="inline-status info">

                        <span
                            class="inline-status-icon"
                        >
                            ${safe(
                                descriptors.length
                            )}
                        </span>

                        <span>
                            Capturing face profile...
                            ${safe(
                                descriptors.length
                            )}
                            sample(s) captured.
                        </span>

                    </div>

                `;
            }


            await new Promise(
                resolve =>
                    setTimeout(
                        resolve,
                        300
                    )
            );
        }


        if (
            descriptors.length === 0
        ) {

            stopCamera();


            throw new Error(
                "No clear face was detected. Face the camera and try again."
            );
        }


        /*
            Average the captured descriptors.
        */

        const length =
            descriptors[0].length;


        const average =
            new Array(
                length
            ).fill(0);


        descriptors.forEach(
            descriptor => {

                descriptor.forEach(
                    (
                        value,
                        index
                    ) => {

                        average[index] +=
                            value;
                    }
                );
            }
        );


        for (
            let index = 0;
            index < average.length;
            index++
        ) {

            average[index] /=
                descriptors.length;
        }


        const studentResult =
            await db
                .from("students")
                .select(
                    "student_id,name,class_name"
                )
                .eq(
                    "school_id",
                    S.school
                )
                .eq(
                    "student_id",
                    studentId
                )
                .maybeSingle();


        if (
            studentResult.error
        ) {
            throw studentResult.error;
        }


        const student =
            studentResult.data;


        if (!student) {

            throw new Error(
                "Student was not found."
            );
        }


        const saveResult =
            await db
                .from("face_profiles")
                .upsert(

                    {

                        school_id:
                            S.school,

                        student_id:
                            student.student_id,

                        student_name:
                            student.name,

                        descriptor:
                            average
                    },

                    {
                        onConflict:
                            "school_id,student_id"
                    }
                );


        if (
            saveResult.error
        ) {
            throw saveResult.error;
        }


        stopCamera();


        if (status) {

            status.innerHTML = `

                <div class="inline-status success">

                    <span
                        class="inline-status-icon"
                    >
                        ✓
                    </span>

                    <span>

                        <b>
                            ${safe(
                                student.name
                            )}
                        </b>

                        is ready for
                        Smart Attendance.

                    </span>

                </div>

            `;
        }


        showToast(
            "Smart Attendance profile registered.",
            "success"
        );

    }

    catch (error) {

        console.error(
            error
        );


        stopCamera();


        if (status) {

            status.innerHTML = `

                <div class="inline-status error">

                    <span
                        class="inline-status-icon"
                    >
                        !
                    </span>

                    <span>
                        ${safe(
                            error?.message ||
                            "Face registration failed."
                        )}
                    </span>

                </div>

            `;
        }


        showToast(
            error?.message ||
            "Face registration failed.",
            "error"
        );
    }
}
/* =========================================================
   TEACHERS PAGE
========================================================= */

async function teachersPage() {

    if (
        S.role !==
        "School Admin"
    ) {

        $("#page").innerHTML = `

            <div class="box">

                ${emptyState(
                    "Access Restricted",
                    "Only the School Admin can manage teacher accounts."
                )}

            </div>

        `;

        return;
    }


    if (!db) {

        throw new Error(
            "Database is not configured."
        );
    }


    const {
        data,
        error
    } =
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


    if (error) {
        throw error;
    }


    const teachers =
        Array.isArray(data)
            ? data
            : [];


    $("#page").innerHTML = `

        <div class="box">

            <h3>
                Add Teacher
            </h3>

            <p class="muted">
                Create a teacher account for
                this school.
            </p>


            <div class="tools">

                <input
                    id="teacherId"
                    placeholder="Teacher ID"
                    autocomplete="off"
                >


                <input
                    id="teacherName"
                    placeholder="Teacher Name"
                    autocomplete="off"
                >


                <input
                    id="teacherPassword"
                    type="password"
                    placeholder="Password"
                    autocomplete="new-password"
                >


                <button
                    class="no-zoom"
                    onclick="addTeacher()"
                >
                    Add Teacher
                </button>

            </div>

        </div>


        <div
            class="box"
            style="margin-top:18px"
        >

            <div
                style="
                    display:flex;
                    align-items:center;
                    justify-content:space-between;
                    gap:12px;
                    flex-wrap:wrap;
                "
            >

                <div>

                    <h3
                        style="margin-bottom:4px"
                    >
                        Teacher Directory
                    </h3>

                    <span class="muted">
                        ${safe(teachers.length)}
                        teacher
                        ${
                            teachers.length === 1
                                ? ""
                                : "s"
                        }
                    </span>

                </div>

            </div>


            ${renderSearchBar(
                "teacherSearch",
                "Search teachers..."
            )}


            ${
                teachers.length

                    ? `

                    <div
                        class="table"
                        id="teachersTable"
                    >

                        <table>

                            <thead>

                                <tr>

                                    <th>
                                        Teacher ID
                                    </th>

                                    <th>
                                        Name
                                    </th>

                                    <th>
                                        Status
                                    </th>

                                    <th>
                                        Action
                                    </th>

                                </tr>

                            </thead>


                            <tbody>

                                ${teachers.map(
                                    teacher => `

                                        <tr
                                            data-search-item
                                        >

                                            <td>
                                                ${safe(
                                                    teacher.teacher_id
                                                )}
                                            </td>


                                            <td>
                                                <b>
                                                    ${safe(
                                                        teacher.teacher_name
                                                    )}
                                                </b>
                                            </td>


                                            <td>

                                                ${
                                                    teacher.enabled !== false

                                                        ? `

                                                        <span
                                                            style="
                                                                color:#5ad4a4;
                                                                font-weight:700;
                                                            "
                                                        >
                                                            ● Active
                                                        </span>

                                                        `

                                                        : `

                                                        <span
                                                            style="
                                                                color:#ff7d8d;
                                                                font-weight:700;
                                                            "
                                                        >
                                                            ● Disabled
                                                        </span>

                                                        `
                                                }

                                            </td>


                                            <td>

                                                <button
                                                    class="small-button no-zoom"
                                                    onclick="toggleTeacher(
                                                        '${safe(
                                                            teacher.teacher_id
                                                        )}',
                                                        ${
                                                            teacher.enabled !==
                                                            false
                                                        }
                                                    )"
                                                >

                                                    ${
                                                        teacher.enabled !== false
                                                            ? "Disable"
                                                            : "Enable"
                                                    }

                                                </button>

                                            </td>

                                        </tr>

                                    `
                                ).join("")}

                            </tbody>

                        </table>

                    </div>

                    `

                    :

                    emptyState(
                        "No teachers yet",
                        "Add your first teacher using the form above."
                    )
            }

        </div>

    `;


    bindSimpleSearch(
        "teacherSearch",
        "#teachersTable"
    );
}


/* =========================================================
   ADD TEACHER
========================================================= */

async function addTeacher() {

    if (
        S.role !==
        "School Admin"
    ) {

        showToast(
            "School Admin access required.",
            "error"
        );

        return;
    }


    const teacherId =
        $("#teacherId")
            ?.value
            .trim();


    const teacherName =
        $("#teacherName")
            ?.value
            .trim();


    const password =
        $("#teacherPassword")
            ?.value || "";


    if (
        !teacherId ||
        !teacherName ||
        !password
    ) {

        showToast(
            "Fill in all teacher fields.",
            "error"
        );

        return;
    }


    try {

        const existing =
            await db
                .from("teachers")
                .select(
                    "teacher_id"
                )
                .eq(
                    "school_id",
                    S.school
                )
                .eq(
                    "teacher_id",
                    teacherId
                )
                .maybeSingle();


        if (
            existing.error
        ) {
            throw existing.error;
        }


        if (
            existing.data
        ) {

            showToast(
                "That Teacher ID already exists.",
                "error"
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
                        teacherId,

                    teacher_name:
                        teacherName,

                    password_hash:
                        await hash(
                            password
                        ),

                    enabled:
                        true
                });


        if (
            result.error
        ) {
            throw result.error;
        }


        showToast(
            `${teacherName} added successfully.`,
            "success"
        );


        await teachersPage();

    }

    catch (error) {

        console.error(
            error
        );


        showToast(
            error?.message ||
            "Could not add teacher.",
            "error"
        );
    }
}


/* =========================================================
   ENABLE / DISABLE TEACHER
========================================================= */

async function toggleTeacher(
    teacherId,
    currentlyEnabled
) {

    if (
        S.role !==
        "School Admin"
    ) {
        return;
    }


    try {

        const result =
            await db
                .from("teachers")
                .update({

                    enabled:
                        !currentlyEnabled

                })
                .eq(
                    "school_id",
                    S.school
                )
                .eq(
                    "teacher_id",
                    teacherId
                );


        if (
            result.error
        ) {
            throw result.error;
        }


        showToast(
            currentlyEnabled
                ? "Teacher disabled."
                : "Teacher enabled.",
            "success"
        );


        await teachersPage();

    }

    catch (error) {

        console.error(
            error
        );


        showToast(
            error?.message ||
            "Could not update teacher.",
            "error"
        );
    }
}


/* =========================================================
   SMART ATTENDANCE PAGE
========================================================= */

function attendancePage() {

    $("#page").innerHTML = `

        <div class="box">

            <div
                style="
                    display:flex;
                    justify-content:space-between;
                    gap:15px;
                    align-items:center;
                    flex-wrap:wrap;
                "
            >

                <div>

                    <h3>
                        Smart Attendance
                    </h3>

                    <p class="muted">
                        Fast classroom attendance
                        using registered Smart
                        Attendance profiles.
                    </p>

                </div>


                <span
                    style="
                        color:#5ad4a4;
                        font-weight:700;
                    "
                >
                    ● Ready
                </span>

            </div>

        </div>


        <div
            class="box"
            style="margin-top:18px"
        >

            <h3>
                Live Attendance
            </h3>


            <p class="muted">
                Keep exactly one registered
                participant visible in the camera.
            </p>


            <div
                id="attendanceCamera"
                class="camera"
            >
                Live Classroom
            </div>


            <div class="tools">

                <button
                    class="no-zoom"
                    onclick="startSmartAttendance()"
                >
                    Start Automatic Attendance
                </button>


                <button
                    class="secondary-button no-zoom"
                    onclick="stopSmartAttendance()"
                >
                    Stop Camera
                </button>

            </div>


            <div
                id="faceStatus"
                style="margin-top:16px"
            >

                <div
                    class="inline-status info"
                >

                    <span
                        class="inline-status-icon"
                    >
                        i
                    </span>

                    <span>
                        Camera is off.
                    </span>

                </div>

            </div>

        </div>


        <div
            class="box"
            style="margin-top:18px"
        >

            <h3>
                How it works
            </h3>


            <div
                style="
                    display:grid;
                    gap:12px;
                    margin-top:12px;
                "
            >

                <div
                    class="inline-status success"
                >

                    <span
                        class="inline-status-icon"
                    >
                        ✓
                    </span>

                    <span>
                        Registered participant:
                        recognized and automatically
                        marked Present.
                    </span>

                </div>


                <div
                    class="inline-status error"
                >

                    <span
                        class="inline-status-icon"
                    >
                        !
                    </span>

                    <span>
                        Unrecognized face:
                        shown as UNKNOWN and no
                        attendance is recorded.
                    </span>

                </div>


                <div
                    class="inline-status info"
                >

                    <span
                        class="inline-status-icon"
                    >
                        1
                    </span>

                    <span>
                        If multiple faces are visible,
                        EduVision asks for one person
                        at a time.
                    </span>

                </div>


                <div
                    class="inline-status info"
                >

                    <span
                        class="inline-status-icon"
                    >
                        ✓
                    </span>

                    <span>
                        The same student cannot receive
                        duplicate attendance for the
                        same day.
                    </span>

                </div>

            </div>

        </div>


        <div
            class="inline-status info"
            style="margin-top:18px"
        >

            <span
                class="inline-status-icon"
            >
                i
            </span>

            <span>
                Smart Attendance should only be used
                with participants whose profiles were
                registered with appropriate permission.
            </span>

        </div>

    `;
}


/* =========================================================
   BUILD FACE MATCHER
========================================================= */

async function buildFaceMatcher() {

    if (!db) {

        throw new Error(
            "Database is not configured."
        );
    }


    const {
        data,
        error
    } =
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
        throw error;
    }


    const profiles =
        Array.isArray(data)
            ? data
            : [];


    const validProfiles =
        profiles.filter(
            profile =>
                profile.student_id &&
                Array.isArray(
                    profile.descriptor
                ) &&
                profile.descriptor.length > 0
        );


    if (
        validProfiles.length === 0
    ) {

        throw new Error(
            "No Smart Attendance profiles are registered. Go to Students → Register Face first."
        );
    }


    const labels =
        validProfiles.map(
            profile => {

                const descriptor =
                    new Float32Array(
                        profile.descriptor
                    );


                return new faceapi
                    .LabeledFaceDescriptors(

                        String(
                            profile.student_id
                        ) +
                        "|" +
                        String(
                            profile.student_name ||
                            "Student"
                        ),

                        [
                            descriptor
                        ]
                    );
            }
        );


    /*
        Smaller threshold = stricter matching.
        0.50 is intentionally conservative
        for the school demo.
    */

    return new faceapi
        .FaceMatcher(
            labels,
            0.50
        );
}


/* =========================================================
   START SMART ATTENDANCE
========================================================= */

async function startSmartAttendance() {

    const status =
        $("#faceStatus");


    if (!status) {
        return;
    }


    try {

        stopCamera();


        status.innerHTML = `

            <div
                class="inline-status info"
            >

                <span
                    class="inline-status-icon"
                >
                    AI
                </span>

                <span>
                    Loading Smart Attendance...
                </span>

            </div>

        `;


        await loadFaceModels();


        const matcher =
            await buildFaceMatcher();


        status.innerHTML = `

            <div
                class="inline-status info"
            >

                <span
                    class="inline-status-icon"
                >
                    •
                </span>

                <span>
                    Starting camera...
                </span>

            </div>

        `;


        const video =
            await openCamera(
                "attendanceCamera"
            );


        const canvas =
            $("#attendanceCameraCanvas");


        status.innerHTML = `

            <div
                class="inline-status success"
            >

                <span
                    class="inline-status-icon"
                >
                    ●
                </span>

                <span>
                    Scanning — one person at a time.
                </span>

            </div>

        `;


        attendanceTimer =
            setInterval(

                async () => {

                    if (
                        attendanceBusy ||
                        !cameraStream ||
                        !video ||
                        video.readyState < 2
                    ) {
                        return;
                    }


                    attendanceBusy =
                        true;


                    try {

                        const detections =
                            await faceapi
                                .detectAllFaces(

                                    video,

                                    new faceapi
                                        .TinyFaceDetectorOptions({

                                            inputSize:
                                                320,

                                            scoreThreshold:
                                                0.5
                                        })
                                )
                                .withFaceLandmarks()
                                .withFaceDescriptors();


                        if (
                            canvas
                        ) {

                            prepareCanvas(
                                canvas,
                                video
                            );


                            const context =
                                canvas.getContext(
                                    "2d"
                                );


                            context.clearRect(
                                0,
                                0,
                                canvas.width,
                                canvas.height
                            );
                        }


                        /* -------------------------
                           NO FACE
                        ------------------------- */

                        if (
                            detections.length === 0
                        ) {

                            status.innerHTML = `

                                <div
                                    class="inline-status info"
                                >

                                    <span
                                        class="inline-status-icon"
                                    >
                                        •
                                    </span>

                                    <span>
                                        No face detected.
                                    </span>

                                </div>

                            `;

                            return;
                        }


                        /* -------------------------
                           MULTIPLE FACES
                        ------------------------- */

                        if (
                            detections.length > 1
                        ) {

                            status.innerHTML = `

                                <div
                                    class="inline-status error"
                                >

                                    <span
                                        class="inline-status-icon"
                                    >
                                        !
                                    </span>

                                    <span>
                                        ONE PERSON AT A TIME
                                    </span>

                                </div>

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


                        const context =
                            canvas
                                ? canvas.getContext(
                                    "2d"
                                )
                                : null;


                        /* -------------------------
                           UNKNOWN FACE
                        ------------------------- */

                        if (!known) {

                            if (
                                context
                            ) {

                                drawDetectionBox(

                                    context,

                                    detection
                                        .detection
                                        .box,

                                    "UNKNOWN",

                                    "#ff536c"
                                );
                            }


                            status.innerHTML = `

                                <div
                                    class="inline-status error"
                                >

                                    <span
                                        class="inline-status-icon"
                                    >
                                        !
                                    </span>

                                    <span>

                                        <b>
                                            UNKNOWN
                                        </b>

                                        <br>

                                        No attendance recorded.

                                    </span>

                                </div>

                            `;


                            return;
                        }


                        /* -------------------------
                           KNOWN FACE
                        ------------------------- */

                        const parts =
                            best.label.split(
                                "|"
                            );


                        const studentId =
                            parts.shift();


                        const studentName =
                            parts.join("|");


                        if (
                            context
                        ) {

                            drawDetectionBox(

                                context,

                                detection
                                    .detection
                                    .box,

                                studentName,

                                "#4ade80"
                            );
                        }


                        status.innerHTML = `

                            <div
                                class="inline-status success"
                            >

                                <span
                                    class="inline-status-icon"
                                >
                                    ✓
                                </span>

                                <span>

                                    <b>
                                        ${safe(
                                            studentName
                                        )}
                                    </b>

                                    <br>

                                    Recognized.

                                </span>

                            </div>

                        `;


                        await saveAutomaticAttendance(
                            studentId,
                            studentName
                        );

                    }

                    catch (error) {

                        console.error(
                            "Attendance scan error:",
                            error
                        );

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

        console.error(
            error
        );


        stopCamera();


        status.innerHTML = `

            <div
                class="inline-status error"
            >

                <span
                    class="inline-status-icon"
                >
                    !
                </span>

                <span>
                    ${safe(
                        error?.message ||
                        "Smart Attendance could not start."
                    )}
                </span>

            </div>

        `;


        showToast(
            error?.message ||
            "Smart Attendance could not start.",
            "error"
        );
    }
}


/* =========================================================
   PREPARE CAMERA CANVAS
========================================================= */

function prepareCanvas(
    canvas,
    video
) {

    if (
        !canvas ||
        !video
    ) {
        return;
    }


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


/* =========================================================
   DRAW FACE DETECTION BOX
========================================================= */

function drawDetectionBox(
    context,
    box,
    label,
    colour
) {

    if (
        !context ||
        !box
    ) {
        return;
    }


    context.strokeStyle =
        colour;

    context.lineWidth =
        5;


    context.strokeRect(
        box.x,
        box.y,
        box.width,
        box.height
    );


    context.font =
        "bold 20px Arial";


    const labelText =
        String(
            label ||
            ""
        );


    const width =
        context.measureText(
            labelText
        ).width + 20;


    const y =
        Math.max(
            0,
            box.y - 34
        );


    context.fillStyle =
        colour;


    context.fillRect(
        box.x,
        y,
        width,
        34
    );


    context.fillStyle =
        "#06101d";


    context.fillText(
        labelText,
        box.x + 10,
        y + 23
    );
}


/* =========================================================
   SAVE AUTOMATIC ATTENDANCE
========================================================= */

async function saveAutomaticAttendance(
    studentId,
    studentName
) {

    if (
        !db ||
        !S?.school
    ) {
        return;
    }


    const date =
        localDate();


    const attendanceKey =
        `${S.school}|${studentId}|${date}`;


    const status =
        $("#faceStatus");


    /*
        First check the local session.
        This reduces unnecessary database
        requests while the same student
        remains in front of the camera.
    */

    if (
        markedThisSession.has(
            attendanceKey
        )
    ) {

        if (
            status
        ) {

            status.innerHTML = `

                <div
                    class="inline-status success"
                >

                    <span
                        class="inline-status-icon"
                    >
                        ✓
                    </span>

                    <span>

                        <b>
                            ${safe(
                                studentName
                            )}
                        </b>

                        <br>

                        Attendance already recorded today.

                    </span>

                </div>

            `;
        }


        return;
    }


    /* =====================================================
       CHECK DATABASE FOR TODAY'S RECORD
    ===================================================== */

    const existing =
        await db
            .from(
                "attendance"
            )
            .select(
                "id,status"
            )
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


    if (
        existing.error
    ) {
        throw existing.error;
    }


    if (
        existing.data
    ) {

        markedThisSession.add(
            attendanceKey
        );


        if (
            status
        ) {

            status.innerHTML = `

                <div
                    class="inline-status success"
                >

                    <span
                        class="inline-status-icon"
                    >
                        ✓
                    </span>

                    <span>

                        <b>
                            ${safe(
                                studentName
                            )}
                        </b>

                        <br>

                        Attendance already recorded today.

                    </span>

                </div>

            `;
        }


        return;
    }


    /* =====================================================
       LOAD STUDENT
    ===================================================== */

    const studentResult =
        await db
            .from(
                "students"
            )
            .select(
                "student_id,name,class_name,status"
            )
            .eq(
                "school_id",
                S.school
            )
            .eq(
                "student_id",
                studentId
            )
            .maybeSingle();


    if (
        studentResult.error
    ) {
        throw studentResult.error;
    }


    const student =
        studentResult.data;


    if (!student) {

        throw new Error(
            "Recognized student could not be found."
        );
    }


    if (
        student.status !==
        "Active"
    ) {

        if (
            status
        ) {

            status.innerHTML = `

                <div
                    class="inline-status error"
                >

                    <span
                        class="inline-status-icon"
                    >
                        !
                    </span>

                    <span>
                        This student is not active.
                    </span>

                </div>

            `;
        }


        return;
    }


    /* =====================================================
       SAVE PRESENT
    ===================================================== */

    const now =
        new Date();


    const saveResult =
        await db
            .from(
                "attendance"
            )
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


    /*
        If two scans happen extremely close
        together, the database unique rule
        may reject the second one. In that
        case we verify whether the record
        already exists instead of showing
        a false failure.
    */

    if (
        saveResult.error
    ) {

        const check =
            await db
                .from(
                    "attendance"
                )
                .select("id")
                .eq(
                    "school_id",
                    S.school
                )
                .eq(
                    "student_id",
                    student.student_id
                )
                .eq(
                    "attendance_date",
                    date
                )
                .maybeSingle();


        if (
            check.error ||
            !check.data
        ) {

            throw saveResult.error;
        }
    }


    markedThisSession.add(
        attendanceKey
    );


    if (
        status
    ) {

        status.innerHTML = `

            <div
                class="inline-status success"
            >

                <span
                    class="inline-status-icon"
                >
                    ✓
                </span>

                <span>

                    <b>
                        ${safe(
                            student.name
                        )}
                    </b>

                    <br>

                    Present automatically saved.

                </span>

            </div>

        `;
    }


    showToast(
        `${student.name} marked Present.`,
        "success"
    );
}


/* =========================================================
   STOP SMART ATTENDANCE
========================================================= */

function stopSmartAttendance() {

    stopCamera();


    const status =
        $("#faceStatus");


    if (
        status
    ) {

        status.innerHTML = `

            <div
                class="inline-status info"
            >

                <span
                    class="inline-status-icon"
                >
                    i
                </span>

                <span>
                    Camera stopped.
                </span>

            </div>

        `;
    }
}
/* =========================================================
   SMART OCCUPANCY PAGE
========================================================= */

function occupancyPage() {

    $("#page").innerHTML = `

        <div class="box">

            <div
                style="
                    display:flex;
                    justify-content:space-between;
                    gap:15px;
                    align-items:center;
                    flex-wrap:wrap;
                "
            >

                <div>

                    <h3>
                        Smart Occupancy
                    </h3>

                    <p class="muted">
                        Live classroom occupancy
                        monitoring using the camera.
                    </p>

                </div>

                <span
                    style="
                        color:#5ad4a4;
                        font-weight:700;
                    "
                >
                    ● Ready
                </span>

            </div>

        </div>


        <div
            class="box"
            style="margin-top:18px"
        >

            <h3>
                Live Classroom
            </h3>


            <div
                id="occupancyCamera"
                class="camera"
            >
                Camera is off
            </div>


            <div class="tools">

                <button
                    class="no-zoom"
                    onclick="startSmartOccupancy()"
                >
                    Start Smart Occupancy
                </button>


                <button
                    class="secondary-button no-zoom"
                    onclick="stopSmartOccupancy()"
                >
                    Stop Camera
                </button>

            </div>

        </div>


        <div
            class="stats"
            style="margin-top:18px"
        >

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
            style="margin-top:18px"
        >

            <div class="inline-status info">

                <span
                    class="inline-status-icon"
                >
                    i
                </span>

                <span>
                    Camera is off.
                </span>

            </div>

        </div>

    `;
}


/* =========================================================
   LOAD OCCUPANCY MODEL
========================================================= */

async function loadOccupancyModel() {

    if (
        occupancyModel
    ) {

        return occupancyModel;
    }


    if (
        !window.cocoSsd
    ) {

        throw new Error(
            "Smart Occupancy library did not load."
        );
    }


    const status =
        $("#occupancyStatus");


    if (status) {

        status.innerHTML = `

            <div class="inline-status info">

                <span
                    class="inline-status-icon"
                >
                    AI
                </span>

                <span>
                    Loading Smart Occupancy...
                </span>

            </div>

        `;
    }


    occupancyModel =
        await cocoSsd.load({
            base:
                "lite_mobilenet_v2"
        });


    return occupancyModel;
}


/* =========================================================
   START SMART OCCUPANCY
========================================================= */

async function startSmartOccupancy() {

    const status =
        $("#occupancyStatus");


    const state =
        $("#occupancyState");


    try {

        stopCamera();


        if (status) {

            status.innerHTML = `

                <div class="inline-status info">

                    <span
                        class="inline-status-icon"
                    >
                        AI
                    </span>

                    <span>
                        Preparing Smart Occupancy...
                    </span>

                </div>

            `;
        }


        const model =
            await loadOccupancyModel();


        const video =
            await openCamera(
                "occupancyCamera"
            );


        const canvas =
            $("#occupancyCameraCanvas");


        if (state) {

            state.textContent =
                "Active";
        }


        if (status) {

            status.innerHTML = `

                <div class="inline-status success">

                    <span
                        class="inline-status-icon"
                    >
                        ●
                    </span>

                    <span>
                        Live classroom detection active.
                    </span>

                </div>

            `;
        }


        occupancyTimer =
            setInterval(

                async () => {

                    if (
                        occupancyBusy ||
                        !cameraStream ||
                        !video ||
                        video.readyState < 2
                    ) {

                        return;
                    }


                    occupancyBusy =
                        true;


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


                        if (
                            countElement
                        ) {

                            countElement.textContent =
                                count;
                        }


                        if (
                            canvas
                        ) {

                            prepareCanvas(
                                canvas,
                                video
                            );


                            const context =
                                canvas.getContext(
                                    "2d"
                                );


                            context.clearRect(
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

                                        context,

                                        x,
                                        y,
                                        width,
                                        height,

                                        index + 1,

                                        person.score
                                    );
                                }
                            );
                        }


                        if (status) {

                            status.innerHTML = `

                                <div
                                    class="inline-status success"
                                >

                                    <span
                                        class="inline-status-icon"
                                    >
                                        ●
                                    </span>

                                    <span>

                                        <b>
                                            Live Detection
                                        </b>

                                        <br>

                                        ${safe(count)}
                                        ${
                                            count === 1
                                                ? "person"
                                                : "people"
                                        }
                                        detected.

                                    </span>

                                </div>

                            `;
                        }

                    }

                    catch (error) {

                        console.error(
                            "Occupancy detection error:",
                            error
                        );

                    }

                    finally {

                        occupancyBusy =
                            false;
                    }

                },

                750
            );

    }

    catch (error) {

        console.error(
            error
        );


        stopCamera();


        if (state) {

            state.textContent =
                "Error";
        }


        if (status) {

            status.innerHTML = `

                <div class="inline-status error">

                    <span
                        class="inline-status-icon"
                    >
                        !
                    </span>

                    <span>
                        ${safe(
                            error?.message ||
                            "Smart Occupancy could not start."
                        )}
                    </span>

                </div>

            `;
        }


        showToast(
            error?.message ||
            "Smart Occupancy could not start.",
            "error"
        );
    }
}


/* =========================================================
   DRAW OCCUPANCY BOX
========================================================= */

function drawOccupancyBox(
    context,
    x,
    y,
    width,
    height,
    number,
    score
) {

    if (!context) {
        return;
    }


    const colour =
        "#4ade80";


    context.strokeStyle =
        colour;

    context.lineWidth =
        4;


    context.strokeRect(
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


    context.font =
        "bold 18px Arial";


    const labelWidth =
        context.measureText(
            label
        ).width + 18;


    const labelY =
        Math.max(
            0,
            y - 30
        );


    context.fillStyle =
        colour;


    context.fillRect(
        x,
        labelY,
        labelWidth,
        30
    );


    context.fillStyle =
        "#06101d";


    context.fillText(
        label,
        x + 9,
        labelY + 21
    );
}


/* =========================================================
   STOP SMART OCCUPANCY
========================================================= */

function stopSmartOccupancy() {

    stopCamera();


    const state =
        $("#occupancyState");


    const status =
        $("#occupancyStatus");


    const count =
        $("#occupancyCount");


    if (state) {

        state.textContent =
            "Off";
    }


    if (count) {

        count.textContent =
            "0";
    }


    if (status) {

        status.innerHTML = `

            <div class="inline-status info">

                <span
                    class="inline-status-icon"
                >
                    i
                </span>

                <span>
                    Camera stopped.
                </span>

            </div>

        `;
    }
}


/* =========================================================
   REPORTS
========================================================= */

async function reportsPage() {

    if (!db) {

        throw new Error(
            "Database is not configured."
        );
    }


    if (
        !S?.school
    ) {

        throw new Error(
            "School information is missing."
        );
    }


    const {
        data,
        error
    } =
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
            .order(
                "created_at",
                {
                    ascending:
                        false
                }
            )
            .limit(
                500
            );


    if (error) {
        throw error;
    }


    const records =
        Array.isArray(data)
            ? data
            : [];


    const today =
        localDate();


    const todayRecords =
        records.filter(
            record =>
                record.attendance_date ===
                today
        );


    const presentToday =
        todayRecords.filter(
            record =>
                record.status ===
                "Present"
        ).length;


    const lateToday =
        todayRecords.filter(
            record =>
                record.status ===
                "Late"
        ).length;


    $("#page").innerHTML = `

        ${stats([

            [
                "Records",
                records.length
            ],

            [
                "Marked Today",
                todayRecords.length
            ],

            [
                "Present Today",
                presentToday
            ],

            [
                "Late Today",
                lateToday
            ]

        ])}


        <div
            class="box"
            style="margin-top:18px"
        >

            <div
                style="
                    display:flex;
                    justify-content:space-between;
                    align-items:center;
                    gap:15px;
                    flex-wrap:wrap;
                "
            >

                <div>

                    <h3>
                        Attendance Reports
                    </h3>

                    <p class="muted">
                        Search or export recent
                        attendance records.
                    </p>

                </div>


                <button
                    class="no-zoom"
                    onclick="exportAttendanceReport()"
                >
                    Export CSV
                </button>

            </div>


            ${renderSearchBar(
                "reportSearch",
                "Search student, class, date or status..."
            )}


            ${
                records.length

                    ? `

                    <div
                        class="table"
                        id="reportsTable"
                    >

                        <table>

                            <thead>

                                <tr>

                                    <th>
                                        Date
                                    </th>

                                    <th>
                                        Time
                                    </th>

                                    <th>
                                        Student
                                    </th>

                                    <th>
                                        ID
                                    </th>

                                    <th>
                                        Class
                                    </th>

                                    <th>
                                        Status
                                    </th>

                                </tr>

                            </thead>


                            <tbody>

                                ${records.map(
                                    record => `

                                        <tr
                                            data-search-item
                                        >

                                            <td>
                                                ${safe(
                                                    record.attendance_date
                                                )}
                                            </td>

                                            <td>
                                                ${safe(
                                                    record.attendance_time ||
                                                    "-"
                                                )}
                                            </td>

                                            <td>
                                                <b>
                                                    ${safe(
                                                        record.name
                                                    )}
                                                </b>
                                            </td>

                                            <td>
                                                ${safe(
                                                    record.student_id
                                                )}
                                            </td>

                                            <td>
                                                ${safe(
                                                    record.class_name
                                                )}
                                            </td>

                                            <td>

                                                ${
                                                    record.status ===
                                                    "Present"

                                                        ? `

                                                        <span
                                                            style="
                                                                color:#5ad4a4;
                                                                font-weight:700;
                                                            "
                                                        >
                                                            Present
                                                        </span>

                                                        `

                                                        : safe(
                                                            record.status
                                                        )
                                                }

                                            </td>

                                        </tr>

                                    `
                                ).join("")}

                            </tbody>

                        </table>

                    </div>

                    `

                    :

                    emptyState(
                        "No attendance records",
                        "Attendance records will appear here after students are marked."
                    )
            }

        </div>

    `;


    /*
        Keep the data temporarily available
        for the export button.
    */

    window.eduvisionReportRows =
        records;


    bindSimpleSearch(
        "reportSearch",
        "#reportsTable"
    );
}


/* =========================================================
   EXPORT ATTENDANCE REPORT
========================================================= */

function exportAttendanceReport() {

    const records =
        Array.isArray(
            window.eduvisionReportRows
        )

            ? window.eduvisionReportRows

            : [];


    const exportRows =
        records.map(
            record => ({

                Date:
                    record.attendance_date ||
                    "",

                Time:
                    record.attendance_time ||
                    "",

                Student_ID:
                    record.student_id ||
                    "",

                Student:
                    record.name ||
                    "",

                Class:
                    record.class_name ||
                    "",

                Status:
                    record.status ||
                    ""

            })
        );


    exportCsvRows(

        exportRows,

        `EduVision-Attendance-${localDate()}.csv`
    );
}


/* =========================================================
   SETTINGS
========================================================= */

function settingsPage() {

    if (
        S.role !==
        "School Admin"
    ) {

        $("#page").innerHTML = `

            <div class="box">

                ${emptyState(
                    "Access Restricted",
                    "Only the School Admin can access school settings."
                )}

            </div>

        `;

        return;
    }


    $("#page").innerHTML = `

        <div class="box">

            <h3>
                School Settings
            </h3>


            <p class="muted">
                Current School ID
            </p>


            <b>
                ${safe(
                    S.school
                )}
            </b>

        </div>


        <div
            class="box"
            style="margin-top:18px"
        >

            <h3>
                Signed In As
            </h3>


            <p>
                <b>
                    ${safe(
                        S.name
                    )}
                </b>
            </p>


            <p class="muted">
                ${safe(
                    S.role
                )}
            </p>

        </div>


        <div
            class="box"
            style="margin-top:18px"
        >

            <h3>
                EduVision
            </h3>


            <p class="muted">
                Smarter classrooms through
                fast attendance, classroom
                monitoring and simple management.
            </p>


            <div
                class="inline-status success"
            >

                <span
                    class="inline-status-icon"
                >
                    ●
                </span>

                <span>
                    System Online
                </span>

            </div>

        </div>

    `;
}


/* =========================================================
   EDUVISION ADMIN — SCHOOLS
========================================================= */

async function schoolsPage() {

    if (
        S.role !==
        "EduVision Admin"
    ) {

        $("#page").innerHTML = `

            <div class="box">

                ${emptyState(
                    "Access Restricted",
                    "EduVision Admin access is required."
                )}

            </div>

        `;

        return;
    }


    if (!db) {

        throw new Error(
            "Supabase is not configured."
        );
    }


    /*
        IMPORTANT:
        We intentionally do NOT use:

            const { data = [] }

        because Supabase may return
        data: null when a request fails.

        This prevents the old endless
        Loading... problem.
    */


    const result =
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


    if (
        result.error
    ) {

        throw result.error;
    }


    const schools =
        Array.isArray(
            result.data
        )

            ? result.data

            : [];


    const pending =
        schools.filter(
            school =>
                school.approval_status ===
                "Pending"
        ).length;


    const approved =
        schools.filter(
            school =>
                school.approval_status ===
                "Approved"
        ).length;


    $("#page").innerHTML = `

        ${stats([

            [
                "Pending",
                pending
            ],

            [
                "Approved",
                approved
            ],

            [
                "Total Schools",
                schools.length
            ],

            [
                "System",
                "Online"
            ]

        ])}


        <div
            class="box"
            style="margin-top:18px"
        >

            <h3>
                School Registrations
            </h3>


            <p class="muted">
                Review schools requesting
                access to EduVision.
            </p>


            ${renderSearchBar(
                "schoolSearch",
                "Search school, ID, admin or status..."
            )}


            ${
                schools.length

                    ? `

                    <div
                        class="table"
                        id="schoolsTable"
                    >

                        <table>

                            <thead>

                                <tr>

                                    <th>
                                        School ID
                                    </th>

                                    <th>
                                        School
                                    </th>

                                    <th>
                                        Admin ID
                                    </th>

                                    <th>
                                        Status
                                    </th>

                                    <th>
                                        Action
                                    </th>

                                </tr>

                            </thead>


                            <tbody>

                                ${schools.map(
                                    school => `

                                        <tr
                                            data-search-item
                                        >

                                            <td>
                                                ${safe(
                                                    school.school_id
                                                )}
                                            </td>


                                            <td>
                                                <b>
                                                    ${safe(
                                                        school.school_name
                                                    )}
                                                </b>
                                            </td>


                                            <td>
                                                ${safe(
                                                    school.admin_id
                                                )}
                                            </td>


                                            <td>

                                                ${
                                                    school.approval_status ===
                                                    "Approved"

                                                        ? `

                                                        <span
                                                            style="
                                                                color:#5ad4a4;
                                                                font-weight:700;
                                                            "
                                                        >
                                                            ● Approved
                                                        </span>

                                                        `

                                                        :

                                                    school.approval_status ===
                                                    "Rejected"

                                                        ? `

                                                        <span
                                                            style="
                                                                color:#ff7d8d;
                                                                font-weight:700;
                                                            "
                                                        >
                                                            ● Rejected
                                                        </span>

                                                        `

                                                        : `

                                                        <span
                                                            style="
                                                                color:#f7c76b;
                                                                font-weight:700;
                                                            "
                                                        >
                                                            ● Pending
                                                        </span>

                                                        `
                                                }

                                            </td>


                                            <td>

                                                <div class="tools">

                                                    <button
                                                        class="small-button no-zoom"
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
                                                        class="small-button secondary-button no-zoom"
                                                        onclick="setSchoolStatus(
                                                            '${safe(
                                                                school.school_id
                                                            )}',
                                                            'Rejected'
                                                        )"
                                                    >
                                                        Reject
                                                    </button>

                                                </div>

                                            </td>

                                        </tr>

                                    `
                                ).join("")}

                            </tbody>

                        </table>

                    </div>

                    `

                    :

                    emptyState(
                        "No schools found",
                        "New school registration requests will appear here."
                    )
            }

        </div>

    `;


    bindSimpleSearch(
        "schoolSearch",
        "#schoolsTable"
    );
}


/* =========================================================
   APPROVE / REJECT SCHOOL
========================================================= */

async function setSchoolStatus(
    schoolId,
    status
) {

    if (
        S.role !==
        "EduVision Admin"
    ) {

        return;
    }


    try {

        const update = {

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
        };


        const result =
            await db
                .from("schools")
                .update(
                    update
                )
                .eq(
                    "school_id",
                    schoolId
                );


        if (
            result.error
        ) {

            throw result.error;
        }


        showToast(

            status === "Approved"

                ? "School approved."

                : "School rejected.",

            status === "Approved"
                ? "success"
                : "info"
        );


        await schoolsPage();

    }

    catch (error) {

        console.error(
            error
        );


        showToast(
            error?.message ||
            "Could not update school.",
            "error"
        );
    }
}


/* =========================================================
   STARTUP
========================================================= */

function initBootState() {

    initUiLayer();


    /*
        Existing login session.
    */

    if (
        S &&
        S.role
    ) {

        start(
            S
        );

        return;
    }


    /*
        New visitor.
    */

    S =
        null;


    localStorage.removeItem(
        "evs"
    );


    showView(
        "home"
    );
}


/* =========================================================
   STOP CAMERA WHEN TAB / PAGE CLOSES
========================================================= */

window.addEventListener(
    "beforeunload",
    () => {

        stopCamera();
    }
);


/* =========================================================
   ESC KEY
========================================================= */

document.addEventListener(
    "keydown",
    event => {

        if (
            event.key !==
            "Escape"
        ) {

            return;
        }


        if (
            cameraStream
        ) {

            stopCamera();


            showToast(
                "Camera stopped.",
                "info"
            );
        }
    }
);


/* =========================================================
   BOOT
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        initBootState();
    }
);
