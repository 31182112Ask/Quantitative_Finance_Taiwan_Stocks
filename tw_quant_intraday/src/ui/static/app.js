async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!data.ok) {
    throw new Error(data.error || "request failed");
  }
  return data.result;
}

async function getJson(url) {
  const response = await fetch(url);
  return response.json();
}

function value(id) {
  const el = document.getElementById(id);
  return el.type === "checkbox" ? el.checked : el.value;
}

function setText(id, text) {
  document.getElementById(id).textContent = text;
}

function formatMoney(value) {
  const number = Number(value || 0);
  return number.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatPct(value) {
  const number = Number(value || 0);
  return `${number.toFixed(4)}%`;
}

function classForNumber(value) {
  const number = Number(value || 0);
  if (number > 0) return "positive";
  if (number < 0) return "negative";
  return "";
}

function objectRows(targetId, data) {
  const target = document.getElementById(targetId);
  target.innerHTML = "";
  Object.entries(data || {}).forEach(([key, val]) => {
    const row = document.createElement("div");
    row.className = "kv";
    row.innerHTML = `<div>${key}</div><div>${val ?? ""}</div>`;
    target.appendChild(row);
  });
}

function renderTable(targetId, rows, columns) {
  const target = document.getElementById(targetId);
  if (!rows || rows.length === 0) {
    target.innerHTML = '<div class="message">No rows</div>';
    return;
  }
  const header = columns.map((col) => `<th>${col}</th>`).join("");
  const body = rows
    .map((row) => `<tr>${columns.map((col) => `<td>${row[col] ?? ""}</td>`).join("")}</tr>`)
    .join("");
  target.innerHTML = `<div class="table-wrap"><table><thead><tr>${header}</tr></thead><tbody>${body}</tbody></table></div>`;
}

function renderEquityChart(targetId, rows) {
  const target = document.getElementById(targetId);
  if (!rows || rows.length === 0) {
    target.innerHTML = "";
    return;
  }
  const values = rows.map((row) => Number(row.equity));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const width = 900;
  const height = 260;
  const pad = 28;
  const span = max - min || 1;
  const points = values
    .map((val, index) => {
      const x = pad + (index / Math.max(values.length - 1, 1)) * (width - pad * 2);
      const y = height - pad - ((val - min) / span) * (height - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  target.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="equity curve">
      <line x1="${pad}" y1="${height - pad}" x2="${width - pad}" y2="${height - pad}" stroke="#d8dee6" />
      <line x1="${pad}" y1="${pad}" x2="${pad}" y2="${height - pad}" stroke="#d8dee6" />
      <polyline points="${points}" fill="none" stroke="#0f766e" stroke-width="3" />
      <text x="${pad}" y="20" fill="#667485" font-size="12">${formatMoney(max)}</text>
      <text x="${pad}" y="${height - 8}" fill="#667485" font-size="12">${formatMoney(min)}</text>
    </svg>`;
}
