const PALETTE = [
    "#FFB7B2", "#FFDAC1", "#E2F0CB", "#B5EAD7", "#C7CEEA",
    "#F0C4C4", "#FDE2C3", "#D4E8C4", "#A8DFD4", "#BBC6E5",
    "#F8B8C0", "#FFE0C8", "#DCF0C8", "#C2EDDC", "#D0D6F0",
];

let convergenceChart = null;
let network = null;
let lastResult = null;

// ===================== تعویض تم =====================
const themeToggle = document.getElementById("theme-toggle");
const storedTheme = localStorage.getItem("gbsa-theme");

function applyTheme(theme) {
    if (theme === "dark") {
        document.documentElement.setAttribute("data-theme", "dark");
        themeToggle.textContent = "☀️";
        themeToggle.title = "تم روشن";
    } else {
        document.documentElement.removeAttribute("data-theme");
        themeToggle.textContent = "🌙";
        themeToggle.title = "تم تاریک";
    }
    localStorage.setItem("gbsa-theme", theme);

    // بازرسم نمودار و گراف اگر وجود داشته باشند
    if (lastResult) {
        renderChart(lastResult.history);
        renderGraph(lastResult);
    }
}

// پیش‌فرض: تم کاربر یا روشن
applyTheme(storedTheme || "light");

themeToggle.addEventListener("click", () => {
    const current = document.documentElement.hasAttribute("data-theme") ? "dark" : "light";
    applyTheme(current === "dark" ? "light" : "dark");
});

// ===================== helpers برای تم =====================
function getChartColors() {
    const isDark = document.documentElement.hasAttribute("data-theme");
    return {
        line: isDark ? "#2dd4bf" : "#7ecfaa",
        fill: isDark ? "rgba(45, 212, 191, 0.08)" : "rgba(181, 234, 215, 0.25)",
        point: isDark ? "#2dd4bf" : "#5eaa82",
        text: isDark ? "#5e6985" : "#b0a5a5",
        grid: isDark ? "rgba(30, 45, 74, 0.4)" : "rgba(0, 0, 0, 0.06)",
        label: isDark ? "#8894b0" : "#7a6e6e",
    };
}

function getGraphColors() {
    const isDark = document.documentElement.hasAttribute("data-theme");
    return {
        edge: isDark ? "#1e2d4a" : "#e0d8d4",
        edgeHighlight: isDark ? "#4f83f7" : "#d98b8b",
        fontColor: isDark ? "#fff" : "#5e4b4b",
        fontStroke: isDark ? "rgba(0,0,0,0.5)" : "#ffffff",
        border: isDark ? "#0f1629" : "#f0e8e5",
        borderHighlight: isDark ? "#fff" : "#d98b8b",
    };
}

const form = document.getElementById("run-form");
const runBtn = document.getElementById("run-btn");
const statusEl = document.getElementById("status");

function setStatus(msg, kind) {
    statusEl.textContent = msg;
    statusEl.className = "status" + (kind ? " " + kind : "");
}

// ===================== آپلود فایل — نمایش نام فایل =====================
document.getElementById("file").addEventListener("change", () => {
    const f = document.getElementById("file").files[0];
    document.getElementById("file-name").textContent = f ? f.name : "Select File";
});

// ===================== پنل چت — باز/بسته =====================
const chatDock = document.getElementById("chat-dock");
const chatToggle = document.getElementById("chat-toggle");
let chatOpen = true;

chatToggle.addEventListener("click", (e) => {
    e.stopPropagation();
    chatOpen = !chatOpen;
    if (chatOpen) {
        chatDock.classList.remove("collapsed");
        chatToggle.textContent = "▾";
    } else {
        chatDock.classList.add("collapsed");
        chatToggle.textContent = "▴";
    }
});

document.getElementById("chat-dock-header").addEventListener("click", (e) => {
    if (e.target.tagName === "BUTTON") return;
    chatOpen = !chatOpen;
    if (chatOpen) {
        chatDock.classList.remove("collapsed");
        chatToggle.textContent = "▾";
    } else {
        chatDock.classList.add("collapsed");
        chatToggle.textContent = "▴";
    }
});

// ===================== اجرای GbSA =====================
form.addEventListener("submit", async (e) => {
    e.preventDefault();
    runBtn.disabled = true;
    setStatus("در حال اجرای الگوریتم...");

    const formData = new FormData();
    const file = document.getElementById("file").files[0];
    if (file) formData.append("file", file);
    formData.append("population_size", document.getElementById("population").value);
    formData.append("iterations", document.getElementById("iterations").value);

    try {
        const res = await fetch("/api/run", { method: "POST", body: formData });
        if (!res.ok) { const err = await res.text(); throw new Error(err); }
        const data = await res.json();
        lastResult = data;
        renderResults(data);

        // نمایش بخش‌های AI و چت
        document.getElementById("ai-section").style.display = "block";
        document.getElementById("ai-output").style.display = "none";

        // پیام خوش‌آمدگویی هوشمند
        const hist = document.getElementById("chat-history");
        hist.innerHTML = "";
        const n = data.num_nodes;
        const m = data.num_edges;
        const q = data.modularity.toFixed(4);
        const c = data.num_communities;
        appendChat("bot",
            `سلام! نتایج تحلیل گراف (${n} نود، ${m} یال) آماده است.\n\n` +
            `🔹 Modularity = ${q} (${q > 0.35 ? "عملکرد خوب" : q > 0.2 ? "متوسط" : "نیاز به بهبود"})\n` +
            `🔹 ${c} انجمن شناسایی شد.\n\n` +
            `می‌توانید درباره کیفیت خوشه‌بندی، بهبود پارامترها، یا ساختار انجمن‌ها سوال بپرسید.`
        );
        document.getElementById("chat-badge").style.display = "block";

        setStatus(`انجام شد | منبع: ${data.source} | Q = ${data.modularity.toFixed(4)}`, "success");
    } catch (err) {
        setStatus("خطا: " + err.message, "error");
    } finally {
        runBtn.disabled = false;
    }
});

function renderResults(data) {
    document.getElementById("m-nodes").textContent = data.num_nodes;
    document.getElementById("m-edges").textContent = data.num_edges;
    document.getElementById("m-comms").textContent = data.num_communities;
    document.getElementById("m-q").textContent = data.modularity.toFixed(4);

    const lines = data.partition.map((c, i) => `Node ${i} → Community ${c}`);
    document.getElementById("partition-output").textContent = lines.join("\n");

    renderGraph(data);
    renderChart(data.history);
}

// ===================== گراف با Glow =====================
function renderGraph(data) {
    const gc = getGraphColors();
    const nodes = data.nodes.map((n) => ({
        id: n.id,
        label: String(n.id),
        color: {
            background: PALETTE[data.partition[n.id] % PALETTE.length],
            border: gc.border,
            highlight: { border: gc.borderHighlight, background: PALETTE[data.partition[n.id] % PALETTE.length] },
        },
        borderWidth: 2,
        shadow: { enabled: true, color: PALETTE[data.partition[n.id] % PALETTE.length], size: 12 },
        font: { color: gc.fontColor, size: 12, face: "Vazirmatn", strokeWidth: 2, strokeColor: gc.fontStroke },
    }));

    const edges = data.edges.map((e) => ({
        from: e.source, to: e.target,
        color: { color: gc.edge, opacity: 0.7, highlight: gc.edgeHighlight },
        width: 1.4, smooth: { type: "continuous" },
    }));

    const container = document.getElementById("graph");
    container.innerHTML = "";

    const options = {
        physics: {
            solver: "forceAtlas2Based",
            forceAtlas2Based: { gravitationalConstant: -40, centralGravity: 0.01 },
            stabilization: { iterations: 200 },
        },
        interaction: { hover: true, tooltipDelay: 100 },
        nodes: {
            shape: "dot",
            size: 18,
            shadow: { enabled: true, size: 8 },
        },
    };

    network = new vis.Network(container, { nodes, edges }, options);
}

// ===================== نمودار همگرایی =====================
function renderChart(history) {
    const ctx = document.getElementById("convergence-chart").getContext("2d");
    if (convergenceChart) convergenceChart.destroy();
    const c = getChartColors();

    convergenceChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: history.map((_, i) => i),
            datasets: [{
                label: "Best Modularity",
                data: history,
                borderColor: c.line,
                backgroundColor: c.fill,
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 5,
                pointHoverBackgroundColor: c.point,
                tension: 0.4,
                fill: true,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: "top",
                    align: "end",
                    labels: {
                        color: c.label,
                        usePointStyle: true,
                        pointStyleWidth: 8,
                        padding: 15,
                        font: { size: 11, family: "Vazirmatn" },
                    },
                },
            },
            scales: {
                x: {
                    title: { display: true, text: "Iteration", color: c.text, font: { size: 11 } },
                    ticks: { color: c.text, font: { size: 10 } },
                    grid: { color: c.grid, drawBorder: false },
                },
                y: {
                    title: { display: true, text: "Q", color: c.text, font: { size: 11 } },
                    ticks: { color: c.text, font: { size: 10 }, callback: (v) => v.toFixed(3) },
                    grid: { color: c.grid, drawBorder: false },
                },
            },
        },
    });
}

// ===================== LLM — پیشنهاد پارامتر =====================
document.getElementById("suggest-btn").addEventListener("click", async () => {
    const btn = document.getElementById("suggest-btn");
    btn.disabled = true;
    setStatus("✨ در حال پیشنهاد پارامتر...");
    try {
        const numNodes = parseInt(document.getElementById("m-nodes").textContent) || 34;
        const numEdges = parseInt(document.getElementById("m-edges").textContent) || 78;
        const res = await fetch("/api/llm/suggest", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ data: { num_nodes: numNodes, num_edges: numEdges } }),
        });
        if (!res.ok) throw new Error(await res.text());
        const json = await res.json();
        if (json.population_size) document.getElementById("population").value = json.population_size;
        if (json.iterations) document.getElementById("iterations").value = json.iterations;
        setStatus(`✅ AI: pop=${json.population_size} , iter=${json.iterations}`, "success");
    } catch (err) {
        setStatus("خطا: " + err.message, "error");
    } finally {
        btn.disabled = false;
    }
});

// ===================== LLM — تحلیل نتایج =====================
document.getElementById("analyze-btn").addEventListener("click", async () => {
    if (!lastResult) return;
    const btn = document.getElementById("analyze-btn");
    const out = document.getElementById("ai-output");
    const load = document.getElementById("ai-loading");
    btn.disabled = true;
    out.style.display = "none";
    load.style.display = "flex";
    try {
        const res = await fetch("/api/llm/analyze", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ data: lastResult }),
        });
        if (!res.ok) throw new Error(await res.text());
        const json = await res.json();
        out.textContent = json.report;
        out.style.display = "block";
        load.style.display = "none";
    } catch (err) {
        out.textContent = "⛔ " + err.message;
        out.style.color = "#f87171";
        out.style.display = "block";
        load.style.display = "none";
    } finally {
        btn.disabled = false;
    }
});

// ===================== چت =====================
function appendChat(role, text) {
    const hist = document.getElementById("chat-history");
    const cls = role === "user" ? "user" : "bot";
    hist.innerHTML += `<div class="chat-msg ${cls}">${text}</div>`;
    hist.scrollTop = hist.scrollHeight;
}

document.getElementById("chat-btn").addEventListener("click", sendChat);
document.getElementById("chat-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendChat();
});

async function sendChat() {
    if (!lastResult) {
        appendChat("bot", "لطفاً ابتدا الگوریتم را اجرا کنید تا داده‌ها بارگذاری شوند.");
        return;
    }
    const input = document.getElementById("chat-input");
    const question = input.value.trim();
    if (!question) return;

    appendChat("user", question);
    input.value = "";

    const btn = document.getElementById("chat-btn");
    const loading = document.getElementById("chat-loading");
    btn.disabled = true;
    loading.style.display = "flex";

    try {
        const res = await fetch("/api/llm/chat", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ data: lastResult, question }),
        });
        if (!res.ok) throw new Error(await res.text());
        const json = await res.json();
        appendChat("bot", json.answer);
    } catch (err) {
        appendChat("error", "⛔ " + err.message);
    } finally {
        loading.style.display = "none";
        btn.disabled = false;
    }
}