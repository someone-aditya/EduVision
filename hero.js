/* =========================================================
   EDUVISION — HERO VISUALS
   ---------------------------------------------------------
   Plain-JS ports of the two supplied hero components, so the
   project keeps its zero-build setup (no React / three.js):

   1. Animated shader hero  -> #heroShader   (landing page)
      Fragment shader by Matthias Hurrle (@atzedent), re-tinted
      to the EduVision palette.

   2. Dot-globe hero        -> #globeCanvas  (portal selection)
      Rotating wireframe globe behind centred content, drawn
      with raw WebGL instead of three.js.

   Both pause automatically when their screen is hidden.
========================================================= */

(function () {
    "use strict";

    const reduceMotion =
        window.matchMedia &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;


    /* -----------------------------------------------------
       Shared helpers
    ----------------------------------------------------- */

    function compile(gl, type, source) {
        const shader = gl.createShader(type);
        gl.shaderSource(shader, source);
        gl.compileShader(shader);

        if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
            console.error(
                "EduVision hero: shader error",
                gl.getShaderInfoLog(shader)
            );
            gl.deleteShader(shader);
            return null;
        }
        return shader;
    }

    function link(gl, vertexSource, fragmentSource) {
        const vs = compile(gl, gl.VERTEX_SHADER, vertexSource);
        const fs = compile(gl, gl.FRAGMENT_SHADER, fragmentSource);
        if (!vs || !fs) return null;

        const program = gl.createProgram();
        gl.attachShader(program, vs);
        gl.attachShader(program, fs);
        gl.linkProgram(program);

        if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
            console.error(
                "EduVision hero: link error",
                gl.getProgramInfoLog(program)
            );
            return null;
        }
        return program;
    }

    /*
        Runs `frame(seconds)` only while the canvas is actually on
        screen. A hidden screen (display:none) reports as not
        intersecting, so no GPU time is spent on it.
    */
    function createLoop(canvas, { onShow, frame }) {
        let raf = 0;
        let visible = false;
        let pageVisible = !document.hidden;
        const t0 = performance.now();

        function tick(now) {
            frame((now - t0) / 1000);
            raf = requestAnimationFrame(tick);
        }

        function sync() {
            const shouldRun = visible && pageVisible;

            if (shouldRun && !raf) {
                onShow();

                if (reduceMotion) {
                    frame(4);
                } else {
                    raf = requestAnimationFrame(tick);
                }
            }

            if (!shouldRun && raf) {
                cancelAnimationFrame(raf);
                raf = 0;
            }
        }

        new IntersectionObserver(entries => {
            visible = entries[entries.length - 1].isIntersecting;
            sync();
        }).observe(canvas);

        document.addEventListener("visibilitychange", () => {
            pageVisible = !document.hidden;
            sync();
        });

        return {
            redraw() {
                if (reduceMotion && visible) {
                    onShow();
                    frame(4);
                }
            }
        };
    }


    /* =====================================================
       1. SHADER HERO
    ===================================================== */

    const SHADER_VERTEX = `#version 300 es
precision highp float;
in vec4 position;
void main(){gl_Position=position;}`;

    const SHADER_FRAGMENT = `#version 300 es
/*********
* made by Matthias Hurrle (@atzedent)
* Re-tinted for EduVision: slate green, sage and brass.
*/
precision highp float;
out vec4 O;
uniform vec2 resolution;
uniform float time;
uniform vec2 focus;
#define FC gl_FragCoord.xy
#define T time
#define R resolution
#define MN min(R.x,R.y)

float rnd(vec2 p) {
  p=fract(p*vec2(12.9898,78.233));
  p+=dot(p,p+34.56);
  return fract(p.x*p.y);
}
float noise(in vec2 p) {
  vec2 i=floor(p), f=fract(p), u=f*f*(3.-2.*f);
  float
  a=rnd(i),
  b=rnd(i+vec2(1,0)),
  c=rnd(i+vec2(0,1)),
  d=rnd(i+1.);
  return mix(mix(a,b,u.x),mix(c,d,u.x),u.y);
}
float fbm(vec2 p) {
  float t=.0, a=1.; mat2 m=mat2(1.,-.5,.2,1.2);
  for (int i=0; i<5; i++) {
    t+=a*noise(p);
    p*=2.*m;
    a*=.5;
  }
  return t;
}
float clouds(vec2 p) {
  float d=1., t=.0;
  for (float i=.0; i<3.; i++) {
    float a=d*fbm(i*10.+p.x*.2+.2*(1.+i)*p.y+d+i*i+p);
    t=mix(t,d,a);
    d=a;
    p*=2./(i+1.);
  }
  return t;
}
void main(void) {
  vec2 uv=(FC-focus*R)/MN, st=uv*vec2(2,1);
  vec3 col=vec3(0);
  float bg=clouds(vec2(st.x+T*.5,-st.y));
  uv*=1.-.3*(sin(T*.2)*.5+.5);
  for (float i=1.; i<12.; i++) {
    uv+=.1*cos(i*vec2(.1+.01*i, .8)+i*i+T*.5+.1*uv.x);
    vec2 p=uv;
    float d=length(p);
    // sage -> brass ribbons
    vec3 tint=mix(vec3(.28,.74,.55), vec3(.96,.72,.26), .5+.5*sin(i*1.3));
    col+=.0021/d*tint;
    float b=noise(i+p+bg*1.731);
    col+=.0018*b/length(max(p,vec2(b*p.x*.02,p.y)))*vec3(.50,.86,.70);
    // slate-green haze toward the edges
    col=mix(col,vec3(bg*.045,bg*.20,bg*.155),d);
  }
  col=1.-exp(-col*1.25);
  col=max(col,vec3(.035,.085,.07));
  O=vec4(col,1);
}`;

    function initShaderHero(canvas) {
        const gl = canvas.getContext("webgl2", {
            antialias: false,
            alpha: false,
            powerPreference: "low-power"
        });
        if (!gl) return;

        const program = link(gl, SHADER_VERTEX, SHADER_FRAGMENT);
        if (!program) return;

        const buffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
        gl.bufferData(
            gl.ARRAY_BUFFER,
            new Float32Array([-1, 1, -1, -1, 1, 1, 1, -1]),
            gl.STATIC_DRAW
        );

        const position = gl.getAttribLocation(program, "position");
        gl.enableVertexAttribArray(position);
        gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);

        const uResolution = gl.getUniformLocation(program, "resolution");
        const uTime = gl.getUniformLocation(program, "time");
        const uFocus = gl.getUniformLocation(program, "focus");

        function resize() {
            /*
                Half-resolution render: the nebula is soft by nature,
                and this keeps integrated GPUs cool.
            */
            const scale = Math.min(window.devicePixelRatio || 1, 2) * 0.5;
            const w = Math.max(2, Math.round(canvas.clientWidth * scale));
            const h = Math.max(2, Math.round(canvas.clientHeight * scale));

            if (canvas.width !== w || canvas.height !== h) {
                canvas.width = w;
                canvas.height = h;
            }
            gl.viewport(0, 0, canvas.width, canvas.height);
        }

        const loop = createLoop(canvas, {
            onShow: resize,
            frame(seconds) {
                gl.useProgram(program);
                gl.uniform2f(uResolution, canvas.width, canvas.height);
                gl.uniform1f(uTime, seconds + 11);

                /*
                    Keep the bright centre of the nebula on the right,
                    clear of the headline. Narrow screens centre it.
                */
                const wide = canvas.clientWidth > 900;
                gl.uniform2f(uFocus, wide ? 0.68 : 0.5, 0.5);

                gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
            }
        });

        window.addEventListener("resize", () => {
            resize();
            loop.redraw();
        });
    }


    /* =====================================================
       2. DOT-GLOBE HERO
    ===================================================== */

    const GLOBE_VERTEX = `
attribute vec3 aPos;
uniform mat3 uRot;
uniform float uR;
uniform float uF;
uniform float uAspect;
uniform float uPoint;
varying float vDepth;
void main() {
  vec3 p = uRot * aPos * uR;
  vDepth = p.z / uR;
  float w = 3.0 - p.z;
  gl_Position = vec4(p.x * uF / uAspect, p.y * uF, 0.0, w);
  gl_PointSize = uPoint * (3.0 / w);
}`;

    const GLOBE_FRAGMENT = `
precision mediump float;
uniform vec4 uColor;
uniform float uRound;
varying float vDepth;
void main() {
  float depth = mix(0.22, 1.0, smoothstep(-1.0, 1.0, vDepth));
  float a = uColor.a * depth;
  if (uRound > 0.5) {
    float d = length(gl_PointCoord - 0.5);
    if (d > 0.5) discard;
    a *= smoothstep(0.5, 0.18, d);
  }
  gl_FragColor = vec4(uColor.rgb, a);
}`;

    function sphereLines() {
        const verts = [];
        const SEG = 72;

        // Parallels every 15 degrees
        for (let lat = -75; lat <= 75; lat += 15) {
            const phi = (lat * Math.PI) / 180;
            for (let i = 0; i < SEG; i++) {
                const a = (i / SEG) * Math.PI * 2;
                const b = ((i + 1) / SEG) * Math.PI * 2;
                verts.push(
                    Math.cos(phi) * Math.cos(a), Math.sin(phi), Math.cos(phi) * Math.sin(a),
                    Math.cos(phi) * Math.cos(b), Math.sin(phi), Math.cos(phi) * Math.sin(b)
                );
            }
        }

        // Meridians every 15 degrees
        for (let lon = 0; lon < 360; lon += 15) {
            const theta = (lon * Math.PI) / 180;
            for (let i = 0; i < SEG / 2; i++) {
                const a = -Math.PI / 2 + (i / (SEG / 2)) * Math.PI;
                const b = -Math.PI / 2 + ((i + 1) / (SEG / 2)) * Math.PI;
                verts.push(
                    Math.cos(a) * Math.cos(theta), Math.sin(a), Math.cos(a) * Math.sin(theta),
                    Math.cos(b) * Math.cos(theta), Math.sin(b), Math.cos(b) * Math.sin(theta)
                );
            }
        }
        return new Float32Array(verts);
    }

    function gridDots() {
        const verts = [0, 1, 0, 0, -1, 0];
        for (let lat = -75; lat <= 75; lat += 15) {
            for (let lon = 0; lon < 360; lon += 15) {
                const phi = (lat * Math.PI) / 180;
                const theta = (lon * Math.PI) / 180;
                verts.push(
                    Math.cos(phi) * Math.cos(theta),
                    Math.sin(phi),
                    Math.cos(phi) * Math.sin(theta)
                );
            }
        }
        return new Float32Array(verts);
    }

    // Decorative node positions [lat, lon]
    const NODES = [
        [28.6, 77.2], [19.1, 72.9], [13.1, 80.3], [26.9, 75.8],
        [1.35, 103.8], [51.5, -0.1], [40.7, -74.0], [-33.9, 151.2],
        [-1.3, 36.8], [35.7, 139.7], [52.5, 13.4], [-23.5, -46.6]
    ];

    function nodePoints() {
        const verts = [];
        NODES.forEach(([lat, lon]) => {
            const phi = (lat * Math.PI) / 180;
            const theta = (lon * Math.PI) / 180;
            verts.push(
                Math.cos(phi) * Math.cos(theta),
                Math.sin(phi),
                Math.cos(phi) * Math.sin(theta)
            );
        });
        return new Float32Array(verts);
    }

    function rotation(spin, tiltX, tiltZ) {
        const cy = Math.cos(spin), sy = Math.sin(spin);
        const cx = Math.cos(tiltX), sx = Math.sin(tiltX);
        const cz = Math.cos(tiltZ), sz = Math.sin(tiltZ);

        const Ry = [cy, 0, -sy, 0, 1, 0, sy, 0, cy];
        const Rz = [cz, sz, 0, -sz, cz, 0, 0, 0, 1];
        const Rx = [1, 0, 0, 0, cx, sx, 0, -sx, cx];

        const mul = (A, B) => {
            const out = new Array(9).fill(0);
            for (let c = 0; c < 3; c++) {
                for (let r = 0; r < 3; r++) {
                    for (let k = 0; k < 3; k++) {
                        out[c * 3 + r] += A[k * 3 + r] * B[c * 3 + k];
                    }
                }
            }
            return out;
        };

        return new Float32Array(mul(Rx, mul(Rz, Ry)));
    }

    function initGlobeHero(canvas, options = {}) {
        const rotationSpeed = options.rotationSpeed ?? 0.004;
        const coverage = options.coverage ?? 0.9;

        const gl = canvas.getContext("webgl", {
            antialias: true,
            alpha: true,
            premultipliedAlpha: false
        });
        if (!gl) return;

        const program = link(gl, GLOBE_VERTEX, GLOBE_FRAGMENT);
        if (!program) return;

        const lines = sphereLines();
        const nodes = nodePoints();

        const lineBuffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, lineBuffer);
        gl.bufferData(gl.ARRAY_BUFFER, lines, gl.STATIC_DRAW);

        const dots = gridDots();
        const dotBuffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, dotBuffer);
        gl.bufferData(gl.ARRAY_BUFFER, dots, gl.STATIC_DRAW);

        const nodeBuffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, nodeBuffer);
        gl.bufferData(gl.ARRAY_BUFFER, nodes, gl.STATIC_DRAW);

        const aPos = gl.getAttribLocation(program, "aPos");
        const u = name => gl.getUniformLocation(program, name);
        const uRot = u("uRot"), uR = u("uR"), uF = u("uF");
        const uAspect = u("uAspect"), uPoint = u("uPoint");
        const uColor = u("uColor"), uRound = u("uRound");

        // Camera: fov 75deg at z = 3 (as in the original component)
        const F = 1 / Math.tan((75 * Math.PI) / 360);

        function resize() {
            const dpr = Math.min(window.devicePixelRatio || 1, 2);
            const w = Math.max(2, Math.round(canvas.clientWidth * dpr));
            const h = Math.max(2, Math.round(canvas.clientHeight * dpr));

            if (canvas.width !== w || canvas.height !== h) {
                canvas.width = w;
                canvas.height = h;
            }
            gl.viewport(0, 0, w, h);
        }

        const loop = createLoop(canvas, {
            onShow: resize,
            frame(seconds) {
                const aspect = canvas.width / canvas.height;

                /*
                    Size the globe against the shorter side so it
                    fills the screen without clipping on phones.
                */
                const target = Math.min(coverage, 0.95 * aspect);
                const radius = (3 * target) / Math.sqrt(F * F + target * target);

                // 60fps-equivalent speed, independent of refresh rate
                const spin = seconds * rotationSpeed * 60;
                const tiltX = 0.42 + 0.08 * Math.sin(seconds * 0.12);

                gl.clearColor(0, 0, 0, 0);
                gl.clear(gl.COLOR_BUFFER_BIT);
                gl.enable(gl.BLEND);
                gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
                gl.useProgram(program);

                gl.uniformMatrix3fv(uRot, false, rotation(spin, tiltX, 0.41));
                gl.uniform1f(uR, radius);
                gl.uniform1f(uF, F);
                gl.uniform1f(uAspect, aspect);
                gl.enableVertexAttribArray(aPos);

                // Wireframe in chalk (the source uses 0.15 on a dense mesh; this graticule is sparser, so a touch stronger)
                gl.bindBuffer(gl.ARRAY_BUFFER, lineBuffer);
                gl.vertexAttribPointer(aPos, 3, gl.FLOAT, false, 0, 0);
                gl.uniform4f(uColor, 0.93, 0.95, 0.92, 0.34);
                gl.uniform1f(uRound, 0);
                gl.uniform1f(uPoint, 1);
                gl.drawArrays(gl.LINES, 0, lines.length / 3);

                // Dots at every graticule crossing
                gl.bindBuffer(gl.ARRAY_BUFFER, dotBuffer);
                gl.vertexAttribPointer(aPos, 3, gl.FLOAT, false, 0, 0);
                gl.uniform4f(uColor, 0.93, 0.95, 0.92, 0.55);
                gl.uniform1f(uRound, 1);
                gl.uniform1f(uPoint, Math.max(3, canvas.height / 300));
                gl.drawArrays(gl.POINTS, 0, dots.length / 3);

                // Nodes
                const pulse = reduceMotion ? 1 : 0.85 + 0.15 * Math.sin(seconds * 1.6);
                gl.bindBuffer(gl.ARRAY_BUFFER, nodeBuffer);
                gl.vertexAttribPointer(aPos, 3, gl.FLOAT, false, 0, 0);
                gl.uniform4f(uColor, 0.85, 0.67, 0.25, 0.95);
                gl.uniform1f(uRound, 1);
                gl.uniform1f(
                    uPoint,
                    Math.max(7, canvas.height / 90) * pulse
                );
                gl.drawArrays(gl.POINTS, 0, nodes.length / 3);
            }
        });

        window.addEventListener("resize", () => {
            resize();
            loop.redraw();
        });
    }


    /* =====================================================
       3. LIVE SYSTEM STATUS  (reads /api/health)
    ===================================================== */

    const STATUS_TEXT = {
        checking: "Checking system",
        online: "System online",
        offline: "System unreachable"
    };

    function setStatus(state) {
        document.querySelectorAll("[data-status]").forEach(el => {
            el.dataset.state = state;
            const label = el.querySelector(".status-text");
            if (label) label.textContent = STATUS_TEXT[state];
        });
    }

    async function checkHealth() {
        try {
            const response = await fetch("/api/health", { cache: "no-store" });
            const data = response.ok ? await response.json() : null;
            setStatus(data && data.ok ? "online" : "offline");
        } catch (error) {
            setStatus("offline");
        }
    }


    /* =====================================================
       4. BOOT
    ===================================================== */

    function boot() {
        const shader = document.getElementById("heroShader");
        const globe = document.getElementById("globeCanvas");

        if (shader) initShaderHero(shader);
        if (globe) initGlobeHero(globe, { rotationSpeed: 0.004, coverage: 0.92 });

        const today = document.getElementById("today");
        if (today) {
            today.textContent = new Date().toLocaleDateString(undefined, {
                weekday: "long",
                day: "numeric",
                month: "long",
                year: "numeric"
            });
        }

        setStatus("checking");
        checkHealth();
        setInterval(checkHealth, 60000);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }
})();
