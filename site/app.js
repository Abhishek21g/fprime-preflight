let severityChart = null;

function renderReceipt(r) {
  const shipEl = document.getElementById("shipBadge");
  shipEl.textContent = r.ship ? "SHIP" : "NO SHIP";
  shipEl.className = "ship-badge " + (r.ship ? "yes" : "no");

  document.getElementById("shipLabel").textContent = r.ship
    ? "Topology passed all critical checks"
    : "Fix critical findings before HWIT";

  const summary = r.summary || {};
  document.getElementById("critCount").textContent = summary.critical || 0;
  document.getElementById("warnCount").textContent = summary.warning || 0;
  document.getElementById("infoCount").textContent = summary.info || 0;

  document.getElementById("topologyLabel").textContent = r.topology_name || "";
  document.getElementById("topoPath").textContent = r.topology_path || "—";
  document.getElementById("generatedAt").textContent = r.generated_at
    ? `Generated ${new Date(r.generated_at).toLocaleString()}`
    : "—";

  const notes = document.getElementById("notesList");
  notes.innerHTML = (r.notes || [])
    .map((n) => `<li>${n}</li>`)
    .join("");

  const findings = r.findings || [];
  const list = document.getElementById("findingsList");
  if (!findings.length) {
    list.innerHTML = '<li style="color:var(--good)">All checks passed.</li>';
  } else {
    list.innerHTML = findings
      .map((f) => {
        const where = f.connection
          ? `<br/><span class="code-tag">${f.connection}</span>`
          : f.component
            ? `<br/><span class="code-tag">${f.component}</span>`
            : "";
        return `<li>
          <span class="sev sev-${f.severity}">${f.severity}</span>
          <strong>${f.code}</strong>: ${f.message}${where}
        </li>`;
      })
      .join("");
  }

  const critical = findings.find((f) => f.severity === "critical");
  const fixEl = document.getElementById("fixFirst");
  if (critical && !r.ship) {
    fixEl.hidden = false;
    fixEl.innerHTML = `Fix first: <strong>${critical.code}</strong> — ${critical.message}`;
  } else {
    fixEl.hidden = true;
  }

  const ctx = document.getElementById("severityChart");
  if (typeof Chart !== "undefined") {
    if (severityChart) severityChart.destroy();
    severityChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: ["Critical", "Warning", "Info"],
        datasets: [
          {
            data: [
              summary.critical || 0,
              summary.warning || 0,
              summary.info || 0,
            ],
            backgroundColor: ["#f56565", "#f5b83d", "#4ecdc4"],
            borderWidth: 0,
          },
        ],
      },
      options: {
        plugins: { legend: { labels: { color: "#8b97ad", boxWidth: 12 } } },
      },
    });
  }

  window.__lastReceipt = r;
}

async function loadSample() {
  const res = await fetch("./sample_receipt.json");
  renderReceipt(await res.json());
}

function loadFile(file) {
  const reader = new FileReader();
  reader.onload = () => {
    try {
      renderReceipt(JSON.parse(reader.result));
    } catch {
      alert("Invalid JSON receipt");
    }
  };
  reader.readAsText(file);
}

document.addEventListener("DOMContentLoaded", () => {
  const script = document.createElement("script");
  script.src = "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js";
  script.onload = loadSample;
  document.head.appendChild(script);

  document.getElementById("loadSample").addEventListener("click", loadSample);
  document.getElementById("fileInput").addEventListener("change", (e) => {
    const f = e.target.files?.[0];
    if (f) loadFile(f);
  });
  document.getElementById("copyReceipt").addEventListener("click", async () => {
    if (!window.__lastReceipt) return;
    await navigator.clipboard.writeText(JSON.stringify(window.__lastReceipt, null, 2));
  });
});
