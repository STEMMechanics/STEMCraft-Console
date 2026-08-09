function updateActiveNavigation() {
  const path = window.location.pathname;

  document
    .querySelectorAll(".nav-link")
    .forEach((link) => {
      link.classList.remove("active");

      const href = link.getAttribute("href");

      if (!href) {
        return;
      }

      if (href === path) {
        link.classList.add("active");
      }
    });
}

function normalizeButtonClasses() {
  document.querySelectorAll("button").forEach((button) =>
    button.classList.add("button")
  );
}

normalizeButtonClasses();

async function reviewServerImport() {
  const form = document.getElementById("import-server-form");
  const directory = document.getElementById("import-server-directory");
  const backend = document.getElementById("import-process-backend");
  const modal = document.getElementById("import-review-modal");
  const title = document.getElementById("import-review-title");
  const summary = document.getElementById("import-review-summary");
  const report = document.getElementById("import-inspection-report");
  const confirm = document.getElementById("confirm-import-server");
  if (!form || !directory || !backend || !modal || !report || !confirm) return;
  if (!directory.reportValidity()) return;

  modal.hidden = false;
  title.textContent = "Review server import";
  summary.textContent = "Checking the server directory and management requirements…";
  report.textContent = "Inspecting server directory...";
  confirm.hidden = true;
  confirm.disabled = true;

  try {
    const response = await fetch("/api/web/servers/import/inspect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        directory: directory.value,
        process_backend: backend.value,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Unable to inspect path");

    if (data.name && !document.getElementById("import-server-name").value) {
      document.getElementById("import-server-name").value = data.name;
    }
    const factItems = [];
    if (data.jar_name) {
      factItems.push(`<span>JAR <strong>${escapeHtml(data.jar_name)}</strong></span>`);
    }
    if (Number.isInteger(data.port)) {
      factItems.push(`<span>Port <strong>${data.port}</strong></span>`);
    }
    if (data.owner) {
      factItems.push(`<span>Owner <strong>${escapeHtml(data.owner)}</strong></span>`);
    }
    if (data.checked_as) {
      factItems.push(`<span>Checked as <strong>${escapeHtml(data.checked_as)}</strong></span>`);
    }
    factItems.push(`<span>Service <strong>${escapeHtml(data.service?.unit || "None detected")}</strong></span>`);
    const facts = `<div class="import-server-facts">${factItems.join("")}</div>`;
    const errors = (data.errors || []).map((message) =>
      `<p class="import-check error"><i class="fa-solid fa-circle-xmark"></i> ${escapeHtml(message)}</p>`
    ).join("");
    const warnings = (data.warnings || []).map((message) =>
      `<p class="import-check warning"><i class="fa-solid fa-triangle-exclamation"></i> ${escapeHtml(message)}</p>`
    ).join("");
    report.innerHTML = facts + errors + warnings;
    title.textContent = data.ready ? "Server found" : "Server cannot be imported";
    summary.textContent = data.ready
      ? "STEMCraft found this server and can manage it. Review the details before importing."
      : "STEMCraft found the following issues. Resolve them before trying again.";
    confirm.hidden = !data.ready;
    confirm.disabled = !data.ready;
  } catch (error) {
    title.textContent = "Unable to inspect server";
    summary.textContent = "The server directory could not be checked.";
    report.textContent = error.message;
  }
}

function closeImportReviewModal() {
  document.getElementById("import-review-modal").hidden = true;
}

function confirmServerImport() {
  const form = document.getElementById("import-server-form");
  const confirm = document.getElementById("confirm-import-server");
  if (!form || !confirm || confirm.disabled) return;
  confirm.disabled = true;
  confirm.textContent = "Importing...";
  form.requestSubmit();
}

function toggleServerMenu() {
  document
    .getElementById("server-menu")
    .classList.toggle("open");
}

document.addEventListener(
  "click",
  function (event) {
    if (event.target.closest("#server-menu a")) {
      document
        .getElementById("server-menu")
        ?.classList.remove("open");
    }

    const dropdown = document.querySelector(
      ".server-selector",
    );

    if (
      dropdown &&
      !dropdown.contains(
        event.target,
      )
    ) {
      document
        .getElementById(
          "server-menu",
        )
        ?.classList.remove(
          "open",
        );
    }
  },
);

async function updateSystemStats() {
  const cpuValue = document.getElementById("cpu-value");
  const memoryValue = document.getElementById("memory-value");
  const storageValue = document.getElementById("storage-value");

  if (!cpuValue || !memoryValue || !storageValue) {
    return;
  }

  try {
    const response = await fetch("/api/system/stats");

    if (!response.ok) {
      return;
    }

    const stats = await response.json();

    document.getElementById("cpu-value").textContent = stats.cpu.percent + "%";

    document.getElementById("cpu-bar").style.width = stats.cpu.percent + "%";

    document.getElementById("cpu-detail").textContent = stats.cpu.cores +
      " logical cores";

    document.getElementById("memory-value").textContent = stats.memory.percent +
      "%";

    document.getElementById("memory-bar").style.width = stats.memory.percent +
      "%";

    document.getElementById("memory-detail").textContent = stats.memory.used +
      " GB / " +
      stats.memory.total + " GB";

    document.getElementById("storage-value").textContent =
      stats.storage.percent + "%";

    document.getElementById("storage-bar").style.width = stats.storage.percent +
      "%";

    document.getElementById("storage-detail").textContent = stats.storage.used +
      " GB / " +
      stats.storage.total + " GB";

    const minecraft = stats.minecraft || { instances: [] };
    setText(
      "minecraft-running",
      `${minecraft.running} / ${minecraft.installed}`,
    );
    setText(
      "minecraft-installed",
      `${minecraft.running} running · ${minecraft.installed} installed`,
    );
    setText("minecraft-players", minecraft.players_online);
    const instances = document.getElementById("system-instance-list");
    if (instances) {
      instances.innerHTML = minecraft.instances.length
        ? minecraft.instances.map((server) => `
                    <div class="system-instance-row">
                      <div><span class="server-status-dot ${
          server.running ? "running" : ""
        }" data-server-id="${Number(server.id)}"></span><strong>${
          escapeHtml(server.name)
        }</strong>
                      <small>Paper ${
          escapeHtml(server.version || "unknown")
        } · ${server.players} online</small></div>
                      <button class="button ${
          server.running ? "danger" : "start"
        }" onclick="systemServerAction(${Number(server.id)}, '${
          server.running ? "stop" : "start"
        }')">${server.running ? "Stop" : "Start"}</button>
                    </div>`).join("")
        : '<div class="empty-message">No accessible Minecraft instances.</div>';
    }
  } catch (error) {
    console.error("Stats error:", error);
  }
}

updateSystemStats();

setInterval(
  updateSystemStats,
  3000,
);

document.body.addEventListener(
  "htmx:afterSwap",
  function () {
    if (document.querySelector(".console-page")) {
      lastConsoleSignature = "";
    }

    updateActiveNavigation();
    updateDocumentTitle();

    updateSystemStats();
    updateConsolePage();
    updateServerStatus();
    updateServerDots();
    updateOverviewLogs();
    updatePlayersPage();
    updateOverviewPlayers();
    updatePluginsPage();
    updateOverviewPlugins();
    updateBackupsPage();
    updatePropertiesPage();
    updateSMTPSettings();
    updateTFASettings();
    updateBackupJobs();
    updateServerProcessStats();
    updateConsoleVersionStatus();
    loadServerMetrics();
    loadServerSchedules();
    loadPaperVersionStatus();
    normalizeButtonClasses();
  },
);

async function updateServerStatus() {
  const startButton = document.getElementById("topbar-start");

  const restartButton = document.getElementById("topbar-restart");

  const stopButton = document.getElementById("topbar-stop");

  const statusText = document.getElementById(
    "topbar-status-text",
  );

  const statusDot = document.getElementById(
    "topbar-status-dot",
  );

  if (!statusText || !statusDot) {
    return;
  }

  const topbar = document.querySelector(".topbar");

  const serverId = topbar?.dataset.serverId;

  if (!serverId) {
    return;
  }

  try {
    const response = await fetch(
      `/api/web/servers/${serverId}/status`,
    );

    if (!response.ok) {
      throw new Error(
        "Status request failed",
      );
    }

    const data = await response.json();

    if (data.running) {
      statusText.textContent = "Running";

      statusText.style.color = "#21b45b";

      statusDot.style.background = "#21b45b";

      startButton.style.display = "none";
      restartButton.style.display = "";
      stopButton.style.display = "";
    } else {
      statusText.textContent = "Stopped";

      statusText.style.color = "#ef5050";

      statusDot.style.background = "#ef5050";

      startButton.style.display = "";
      restartButton.style.display = "none";
      stopButton.style.display = "none";
    }
  } catch (error) {
    statusText.textContent = "Unknown";

    statusText.style.color = "#888";

    statusDot.style.background = "#999";

    startButton.style.display = "none";
    restartButton.style.display = "none";
    stopButton.style.display = "none";
  }
}

updateServerStatus();

setInterval(
  updateServerStatus,
  3000,
);

async function updateServerDots() {
  const dots = document.querySelectorAll(
    ".server-status-dot",
  );

  for (const dot of dots) {
    const serverId = dot.dataset.serverId;

    try {
      const response = await fetch(
        `/api/web/servers/${serverId}/status`,
      );

      const data = await response.json();

      dot.style.background = data.running ? "#21b45b" : "#ef5050";

      document.querySelectorAll(
        `.server-status-text[data-server-id="${serverId}"]`,
      ).forEach((label) => {
        label.textContent = data.running ? "Running" : "Stopped";
      });
    } catch {
      dot.style.background = "#999";
    }
  }
}

updateServerDots();

setInterval(
  updateServerDots,
  3000,
);

let consoleLines = [];
let consoleFilter = "ALL";
let lastConsoleSignature = "";
let playerData = null;
let playerFilter = "all";
let pluginData = [];
let pluginPendingRemoval = null;
let pluginRestartRequired = false;

let pendingFilePath = null;

function currentFilesPage() {
  return document.querySelector(
    ".files-page",
  );
}

function reloadFilesPage() {
  const page = currentFilesPage();

  if (!page) {
    return;
  }

  const serverId = page.dataset.serverId;

  const path = page.dataset.currentPath || "";

  htmx.ajax(
    "GET",
    `/servers/${serverId}/files?path=${encodeURIComponent(path)}`,
    {
      target: "#page-content",

      swap: "innerHTML",
    },
  );
}

function openNewFolderModal() {
  document.getElementById(
    "new-folder-modal",
  ).hidden = false;

  const input = document.getElementById(
    "new-folder-name",
  );

  input.value = "";
  input.focus();
}

function closeNewFolderModal() {
  document.getElementById(
    "new-folder-modal",
  ).hidden = true;
}

async function createNewFolder() {
  const page = currentFilesPage();

  const input = document.getElementById(
    "new-folder-name",
  );

  const name = input.value.trim();

  if (!name) {
    return;
  }

  const response = await fetch(
    `/api/web/servers/${page.dataset.serverId}/files/mkdir`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        path: page.dataset.currentPath || "",
        name,
      }),
    },
  );

  const data = await response.json();

  if (!response.ok) {
    alert(
      data.error ||
        "Unable to create folder",
    );

    return;
  }

  closeNewFolderModal();

  reloadFilesPage();
}

let renameFilePath = null;

function openRenameModal(
  path,
  name,
) {
  renameFilePath = path;

  const modal = document.getElementById(
    "rename-file-modal",
  );

  const input = document.getElementById(
    "rename-file-name",
  );

  input.value = name;

  modal.hidden = false;

  input.focus();
  input.select();
}

function closeRenameModal() {
  document.getElementById(
    "rename-file-modal",
  ).hidden = true;

  renameFilePath = null;
}

async function confirmRenameFile() {
  const page = currentFilesPage();

  const name = document.getElementById(
    "rename-file-name",
  ).value.trim();

  if (
    !renameFilePath ||
    !name
  ) {
    return;
  }

  const response = await fetch(
    `/api/web/servers/${page.dataset.serverId}/files/rename`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        path: renameFilePath,

        name,
      }),
    },
  );

  const data = await response.json();

  if (!response.ok) {
    alert(
      data.error ||
        "Unable to rename",
    );

    return;
  }

  closeRenameModal();

  reloadFilesPage();
}

function openDeleteFileModal(
  path,
  name,
) {
  pendingFilePath = path;

  document.getElementById(
    "delete-file-name",
  ).textContent = name;

  document.getElementById(
    "delete-file-modal",
  ).hidden = false;
}

function closeDeleteFileModal() {
  document.getElementById(
    "delete-file-modal",
  ).hidden = true;

  pendingFilePath = null;
}

async function confirmDeleteFile() {
  const page = currentFilesPage();

  if (!pendingFilePath) {
    return;
  }

  const response = await fetch(
    `/api/web/servers/${page.dataset.serverId}/files/delete`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        path: pendingFilePath,
      }),
    },
  );

  const data = await response.json();

  if (!response.ok) {
    alert(
      data.error ||
        "Unable to delete",
    );

    return;
  }

  closeDeleteFileModal();

  reloadFilesPage();
}

async function updatePluginsPage() {
  const page = document.querySelector(
    ".plugins-page",
  );

  if (!page) {
    return;
  }

  try {
    const response = await fetch(
      `/api/web/servers/${page.dataset.serverId}/plugins`,
    );

    if (!response.ok) {
      throw new Error();
    }

    const data = await response.json();

    pluginData = data.plugins || [];

    pluginRestartRequired = data.restart_required === true;

    const restartAlert = document.getElementById(
      "plugin-restart-alert",
    );

    if (restartAlert) {
      restartAlert.hidden = !pluginRestartRequired;
    }

    renderPlugins();
  } catch {
    const list = document.getElementById(
      "plugin-list",
    );

    if (list) {
      list.textContent = "Unable to load plugins.";
    }
  }
}

async function uploadPluginJar(event) {
  event.preventDefault();
  const page = document.querySelector(".plugins-page");
  const status = document.getElementById("plugin-install-status");
  const form = event.currentTarget;
  status.textContent = "Uploading and validating...";
  try {
    const response = await fetch(
      `/api/web/servers/${page.dataset.serverId}/plugins/upload`,
      { method: "POST", body: new FormData(form) },
    );
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Plugin upload failed");
    status.textContent = `${data.plugin.name} installed. Restart required.`;
    form.reset();
    updatePluginFileName(form.elements.plugin);
    pluginRestartRequired = true;
    showPluginRestartAlert();
    updatePluginsPage();
  } catch (error) {
    status.textContent = error.message;
  }
}

function updatePluginFileName(input) {
  const name = input
    .closest(".plugin-file-picker")
    ?.querySelector(".plugin-file-name");

  if (name) {
    name.textContent = input.files?.[0]?.name || "No file selected";
  }
}

async function downloadPluginUrl(event) {
  event.preventDefault();
  const page = document.querySelector(".plugins-page");
  const status = document.getElementById("plugin-install-status");
  const form = event.currentTarget;
  status.textContent = "Downloading and validating...";
  try {
    const response = await fetch(
      `/api/web/servers/${page.dataset.serverId}/plugins/url`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: form.elements.url.value }),
      },
    );
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Plugin download failed");
    status.textContent = `${data.plugin.name} installed. Restart required.`;
    form.reset();
    pluginRestartRequired = true;
    showPluginRestartAlert();
    updatePluginsPage();
  } catch (error) {
    status.textContent = error.message;
  }
}

function renderPlugins() {
  const list = document.getElementById(
    "plugin-list",
  );

  if (!list) {
    return;
  }

  const search = (
    document
      .getElementById(
        "plugin-search",
      )
      ?.value ||
    ""
  )
    .trim()
    .toLowerCase();

  const plugins = pluginData.filter(
    (plugin) =>
      plugin.name
        .toLowerCase()
        .includes(search) ||
      plugin.filename
        .toLowerCase()
        .includes(search),
  );

  const count = document.getElementById(
    "plugin-count",
  );

  if (count) {
    count.textContent = `${pluginData.length} ${
      pluginData.length === 1 ? "plugin" : "plugins"
    }`;
  }

  if (!plugins.length) {
    list.innerHTML = `<div class="empty-message">
                No plugins found.
            </div>`;

    return;
  }

  list.innerHTML = plugins.map(
    (plugin, pluginIndex) => `
                <div class="
                    plugin-row
                    ${plugin.enabled ? "" : "disabled"}
                ">

                    <div class="plugin-main">

                        <strong>
                            ${escapeHtml(plugin.name)}
                        </strong>

                        <small>
                            ${escapeHtml(plugin.filename)}
                        </small>

                        <div class="plugin-meta">

                            ${
      plugin.version
        ? `
                                    <span>
                                        ${escapeHtml(plugin.version)}
                                    </span>
                                `
        : ""
    }

                            <span>
                                ${formatFileSize(plugin.size)}
                            </span>

                            <span class="${
      plugin.enabled ? "plugin-active-label" : "plugin-disabled-label"
    }">
                                ${plugin.enabled ? "Active" : "Disabled"}
                            </span>

                        </div>

                    </div>


                    <div class="plugin-actions">

                        ${renderPluginConfigActions(plugin, pluginIndex)}

                        <button
                            class="button"
                            onclick="togglePlugin(
                                '${escapeJs(plugin.filename)}',
                                '${plugin.enabled ? "disable" : "enable"}'
                            )"
                        >
                            ${plugin.enabled ? "Disable" : "Enable"}
                        </button>


                        <button
                            class="button"
                            onclick="openPluginRemoveModal(
                                '${escapeJs(plugin.filename)}'
                            )"
                        >
                            Remove
                        </button>

                    </div>

                </div>
            `,
  )
    .join("");
}

function renderPluginConfigActions(plugin, index) {
  const files = plugin.config_files || [];
  if (!files.length) {
    return `<button class="button" disabled title="Start the server once to generate plugin configuration files">No YAML config</button>`;
  }

  if (files.length === 1) {
    return `<button class="button" data-config-path="${
      escapeHtml(files[0])
    }" onclick="editPluginConfig(this.dataset.configPath)">Edit Config</button>`;
  }

  const selectId = `plugin-config-${index}`;
  const options = files.map((path) =>
    `<option value="${escapeHtml(path)}">${
      escapeHtml(path.split("/").at(-1))
    }</option>`
  ).join("");
  return `<span class="plugin-config-picker"><button class="button" onclick="editSelectedPluginConfig('${selectId}')">Edit Config</button><select id="${selectId}" aria-label="Choose configuration file" title="Choose configuration file">${options}</select></span>`;
}

function editSelectedPluginConfig(selectId) {
  const path = document.getElementById(selectId)?.value;
  if (path) editPluginConfig(path);
}

function editPluginConfig(path) {
  const page = document.querySelector(".plugins-page[data-server-id]");
  if (!page) return;
  const url = `/servers/${page.dataset.serverId}/files/edit?path=${
    encodeURIComponent(path)
  }`;
  htmx.ajax("GET", url, {
    target: "#page-content",
    swap: "innerHTML",
    pushUrl: url,
  });
}

function parseConsoleLine(line) {
  const match = line.match(
    /^\[?(\d{2}:\d{2}:\d{2})\]?\s*(?:\[([^\]]+)\/(INFO|WARN|ERROR|DEBUG)\]:)?\s*(.*)$/i,
  );

  if (!match) {
    return {
      time: "",
      level: "INFO",
      message: line,
    };
  }

  return {
    time: match[1] || "",
    level: (match[3] || "INFO").toUpperCase(),
    message: (match[2] ? `[${match[2]}] ` : "") +
      (match[4] || ""),
  };
}

function renderConsoleLines() {
  const output = document.getElementById(
    "console-output",
  );

  if (!output) {
    return;
  }

  const filtered = consoleFilter === "ALL" ? consoleLines : consoleLines.filter(
    (line) => line.level === consoleFilter,
  );

  if (!filtered.length) {
    output.innerHTML =
      '<div class="empty-message">No matching log entries.</div>';

    return;
  }

  output.innerHTML = filtered
    .map((line) => {
      const levelClass = line.level.toLowerCase();

      return (
        '<div class="console-line">' +
        '<span class="console-time">' +
        escapeHtml(line.time) +
        "</span>" +
        '<span class="console-level ' +
        levelClass +
        '">' +
        escapeHtml(line.level) +
        "</span>" +
        '<span class="console-message">' +
        escapeHtml(line.message) +
        "</span>" +
        "</div>"
      );
    })
    .join("");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function updateConsolePage() {
  const page = document.querySelector(
    ".console-page",
  );

  if (!page) {
    return;
  }

  const serverId = page.dataset.serverId;

  const output = document.getElementById(
    "console-output",
  );

  const input = document.getElementById(
    "console-input",
  );

  const send = document.getElementById(
    "console-send",
  );

  try {
    const response = await fetch(
      `/api/web/servers/${serverId}/console-data`,
    );

    if (!response.ok) {
      throw new Error();
    }

    const data = await response.json();

    const newLines = data.lines.map(
      parseConsoleLine,
    );

    /*
     * Check whether the log has actually
     * changed since the last poll.
     */
    const newSignature = JSON.stringify(newLines);

    const logChanged = newSignature !==
      lastConsoleSignature;

    const consoleNeedsRender = logChanged ||
      output.children.length === 0;

    lastConsoleSignature = newSignature;

    consoleLines = newLines;

    /*
     * We only need to redraw the console
     * when something changed.
     */
    if (consoleNeedsRender) {
      renderConsoleLines();
    }

    if (data.running) {
      input.disabled = false;
      send.disabled = false;

      input.placeholder = "Type a command and press Enter...";
    } else {
      input.disabled = true;
      send.disabled = true;

      input.placeholder = "Server is stopped";
    }

    /*
     * Only autoscroll when:
     *
     * 1. Autoscroll is enabled
     * 2. The log actually changed
     */
    if (
      consoleAutoScroll &&
      logChanged
    ) {
      scrollConsoleToBottom();
    }
  } catch {
    consoleLines = [];

    output.textContent = "Unable to load console.";

    input.disabled = true;
    send.disabled = true;
  }
}

async function sendConsoleCommand() {
  const page = document.querySelector(
    ".console-page",
  );

  if (!page) {
    return;
  }

  const serverId = page.dataset.serverId;

  const input = document.getElementById(
    "console-input",
  );

  const command = input.value.trim();

  if (!command) {
    return;
  }

  const response = await fetch(
    `/api/web/servers/${serverId}/command`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        command: command,
      }),
    },
  );

  const data = await response.json();

  if (!response.ok) {
    alert(
      data.error ||
        "Command failed",
    );

    return;
  }

  input.value = "";

  setTimeout(
    updateConsolePage,
    200,
  );
}

document.addEventListener(
  "keydown",
  function (event) {
    if (
      event.key === "Enter" &&
      event.target?.id === "console-input"
    ) {
      sendConsoleCommand();
    }
  },
);

updateConsolePage();

setInterval(
  updateConsolePage,
  1000,
);

async function updateOverviewLogs() {
  const overview = document.querySelector(
    ".server-overview",
  );

  if (!overview) {
    return;
  }

  const serverId = overview.dataset.serverId;

  const output = document.getElementById(
    "overview-logs",
  );

  if (!output) {
    return;
  }

  try {
    const response = await fetch(
      `/api/web/servers/${serverId}/console-data`,
    );

    if (!response.ok) {
      throw new Error();
    }

    const data = await response.json();

    if (!data.lines.length) {
      output.textContent = data.running
        ? "No console output yet."
        : "No recent logs available.";

      return;
    }

    output.textContent = data.lines
      .slice(-20)
      .join("\n");

    output.scrollTop = output.scrollHeight;
  } catch {
    output.textContent = "Unable to load recent logs.";
  }
}

updateOverviewLogs();

setInterval(
  updateOverviewLogs,
  3000,
);

function scrollConsoleToBottom() {
  const output = document.getElementById(
    "console-output",
  );

  if (!output) {
    return;
  }

  output.scrollTop = output.scrollHeight;
}

document.addEventListener(
  "click",
  function (event) {
    const button = event.target.closest(
      ".console-filter",
    );

    if (!button) {
      return;
    }

    document
      .querySelectorAll(
        ".console-filter",
      )
      .forEach((item) =>
        item.classList.remove(
          "active",
        )
      );

    button.classList.add(
      "active",
    );

    consoleFilter = button.dataset.level;

    renderConsoleLines();
  },
);

let consoleAutoScroll = true;

function toggleConsoleAutoScroll() {
  consoleAutoScroll = !consoleAutoScroll;

  const button = document.getElementById(
    "console-autoscroll",
  );

  if (!button) {
    return;
  }

  button.classList.toggle(
    "active",
    consoleAutoScroll,
  );

  button.title = consoleAutoScroll
    ? "Auto-scroll enabled"
    : "Auto-scroll disabled";

  if (consoleAutoScroll) {
    scrollConsoleToBottom();
  }
}

updateActiveNavigation();

async function updatePlayersPage() {
  const page = document.querySelector(
    ".players-page",
  );

  if (!page) {
    return;
  }

  const serverId = page.dataset.serverId;

  try {
    const response = await fetch(
      `/api/web/servers/${serverId}/players`,
    );

    if (!response.ok) {
      throw new Error();
    }

    playerData = await response.json();

    renderPlayerPage();
  } catch {
    const list = document.getElementById(
      "player-list",
    );

    if (list) {
      list.textContent = "Unable to load players.";
    }
  }
}

function renderPlayerPage() {
  if (!playerData) {
    return;
  }

  setText(
    "players-online-count",
    playerData.online_count,
  );

  setText(
    "players-whitelist-count",
    playerData.whitelisted_count,
  );

  setText(
    "players-op-count",
    playerData.operator_count,
  );

  setText(
    "players-ban-count",
    playerData.banned_count,
  );

  setText(
    "filter-all-count",
    playerData.players.length,
  );

  setText(
    "filter-online-count",
    playerData.online_count,
  );

  setText(
    "filter-whitelist-count",
    playerData.whitelisted_count,
  );

  setText(
    "filter-op-count",
    playerData.operator_count,
  );

  setText(
    "filter-ban-count",
    playerData.banned_count,
  );

  setText(
    "ip-ban-count",
    playerData.ip_banned_count,
  );

  const ipList = document.getElementById("ip-ban-list");
  if (ipList) {
    ipList.innerHTML = (playerData.ip_bans || []).length
      ? playerData.ip_bans.map((item) => `
          <div class="ip-ban-row"><div><strong>${
        escapeHtml(item.ip)
      }</strong><small>${escapeHtml(item.reason || "Banned")}</small></div>
          <button class="button" ${
        !playerData.running ? "disabled" : ""
      } onclick="ipBanAction('${
        escapeJs(item.ip)
      }', 'pardon')">Pardon</button></div>`).join("")
      : '<div class="empty-message">No IP bans.</div>';
  }

  const toggle = document.getElementById(
    "whitelist-toggle",
  );

  if (toggle) {
    toggle.checked = playerData.whitelist_enabled;
  }

  const offline = document.getElementById(
    "players-offline-note",
  );

  if (offline) {
    offline.hidden = playerData.running;
  }

  renderPlayerList();
}

function setText(
  id,
  value,
) {
  const element = document.getElementById(id);

  if (element) {
    element.textContent = value;
  }
}

function renderPlayerList() {
  const list = document.getElementById(
    "player-list",
  );

  if (
    !list ||
    !playerData
  ) {
    return;
  }

  const search = (
    document
      .getElementById(
        "player-search",
      )
      ?.value ||
    ""
  )
    .trim()
    .toLowerCase();

  let players = playerData.players.filter(
    (player) => {
      if (
        search &&
        !player.name
          .toLowerCase()
          .includes(search)
      ) {
        return false;
      }

      switch (
        playerFilter
      ) {
        case "online":
          return player.online;

        case "whitelisted":
          return player.whitelisted;

        case "operator":
          return player.operator;

        case "banned":
          return player.banned;

        default:
          return true;
      }
    },
  );

  if (!players.length) {
    list.innerHTML = '<div class="empty-message">No players found.</div>';

    return;
  }

  list.innerHTML = players.map(
    (player) => {
      const avatar = player.uuid
        ? `https://mc-heads.net/avatar/${encodeURIComponent(player.uuid)}/40`
        : "";

      return `
                    <div class="player-row">

                        <div class="player-identity">

                            <span class="
                                player-online-dot
                                ${player.online ? "online" : ""}
                            "></span>

                            ${
        avatar
          ? `
                                    <img
                                        class="player-avatar"
                                        src="${avatar}"
                                        alt=""
                                    >
                                `
          : `
                                    <div class="player-avatar placeholder">
                                        <i class="fa-solid fa-user"></i>
                                    </div>
                                `
      }

                            <div>

                                <strong>
                                    ${escapeHtml(player.name)}
                                </strong>

                                <small>
                                    ${player.online ? "Online" : "Offline"}
                                </small>

                            </div>

                        </div>


                        <div class="player-actions">

                            <button
                                class="
                                    player-pill
                                    ${player.whitelisted ? "positive" : ""}
                                "
                                ${!playerData.running ? "disabled" : ""}
                                onclick="
                                    playerAction(
                                        '${escapeJs(player.name)}',
                                        '${
        player.whitelisted ? "unwhitelist" : "whitelist"
      }'
                                    )
                                "
                            >
                                ${
        player.whitelisted ? "✓ Whitelisted" : "+ Whitelist"
      }
                            </button>


                            <button
                                class="
                                    player-pill
                                    ${player.operator ? "operator" : ""}
                                "
                                ${!playerData.running ? "disabled" : ""}
                                onclick="
                                    playerAction(
                                        '${escapeJs(player.name)}',
                                        '${player.operator ? "deop" : "op"}'
                                    )
                                "
                            >
                                ${player.operator ? "✓ Op" : "+ Op"}
                            </button>


                            ${
        player.operator
          ? `
                                    <span class="op-level">
                                        L${player.op_level ?? "-"}
                                    </span>
                                `
          : ""
      }


                            ${
        player.online
          ? `
                                    <button
                                        class="button secondary"
                                        onclick="
                                            playerAction(
                                                '${escapeJs(player.name)}',
                                                'kick'
                                            )
                                        "
                                    >
                                        Kick
                                    </button>
                                `
          : ""
      }


                            ${
        player.banned
          ? `
                                    <button
                                        ${!playerData.running ? "disabled" : ""}
                                        onclick="
                                            playerAction(
                                                '${escapeJs(player.name)}',
                                                'pardon'
                                            )
                                        "
                                    >
                                        Pardon
                                    </button>
                                `
          : `
                                    <button
                                        class="button danger"
                                        ${!playerData.running ? "disabled" : ""}
                                        onclick="
                                            playerAction(
                                                '${escapeJs(player.name)}',
                                                'ban'
                                            )
                                        "
                                    >
                                        Ban
                                    </button>
                                `
      }

                        </div>

                    </div>
                `;
    },
  )
    .join("");
}

function escapeJs(value) {
  return String(value)
    .replaceAll("\\", "\\\\")
    .replaceAll("'", "\\'");
}

async function playerAction(
  player,
  action,
) {
  const page = document.querySelector(
    ".players-page",
  );

  if (!page) {
    return;
  }

  const response = await fetch(
    `/api/web/servers/${page.dataset.serverId}/players/action`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        player,
        action,
      }),
    },
  );

  const data = await response.json();

  if (!response.ok) {
    alert(
      data.error ||
        "Player action failed",
    );

    return;
  }

  setTimeout(
    updatePlayersPage,
    500,
  );
}

function addPlayerAction(
  action,
) {
  const input = document.getElementById(
    "player-add-name",
  );

  const player = input?.value.trim();

  if (!player) {
    return;
  }

  playerAction(
    player,
    action,
  );

  input.value = "";
}

async function toggleWhitelist() {
  const page = document.querySelector(
    ".players-page",
  );

  const toggle = document.getElementById(
    "whitelist-toggle",
  );

  if (
    !page ||
    !toggle
  ) {
    return;
  }

  const response = await fetch(
    `/api/web/servers/${page.dataset.serverId}/whitelist-enabled`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        enabled: toggle.checked,
      }),
    },
  );

  if (!response.ok) {
    toggle.checked = !toggle.checked;

    const data = await response.json();

    alert(
      data.error ||
        "Unable to change whitelist",
    );
  }
}

document.addEventListener(
  "click",
  function (event) {
    const button = event.target.closest(
      ".player-filter",
    );

    if (!button) {
      return;
    }

    document
      .querySelectorAll(
        ".player-filter",
      )
      .forEach(
        (item) =>
          item.classList.remove(
            "active",
          ),
      );

    button.classList.add(
      "active",
    );

    playerFilter = button.dataset.filter;

    renderPlayerList();
  },
);

document.addEventListener(
  "input",
  function (event) {
    if (
      event.target.id ===
        "player-search"
    ) {
      renderPlayerList();
    }
  },
);

updatePlayersPage();

async function ipBanAction(ip, action) {
  const page = document.querySelector(".players-page");
  const response = await fetch(
    `/api/web/servers/${page.dataset.serverId}/ip-bans/action`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ip, action }),
    },
  );
  const data = await response.json();
  if (!response.ok) return alert(data.error || "Unable to update IP ban");
  setTimeout(updatePlayersPage, 300);
}

function banIpAddress(event) {
  event.preventDefault();
  const form = event.currentTarget;
  ipBanAction(form.elements.ip.value, "ban").then(() => form.reset());
}

setInterval(
  updatePlayersPage,
  3000,
);

async function updateOverviewPlayers() {
  const overview = document.querySelector(
    ".server-overview",
  );

  if (!overview) {
    return;
  }

  try {
    const response = await fetch(
      `/api/web/servers/${overview.dataset.serverId}/players`,
    );

    if (!response.ok) {
      return;
    }

    const data = await response.json();

    setText(
      "overview-players",
      data.online_count,
    );

    setText(
      "overview-max-players",
      data.max_players,
    );
  } catch {
    // Leave existing values alone.
  }
}

updateOverviewPlayers();

setInterval(
  updateOverviewPlayers,
  3000,
);

function formatFileSize(bytes) {
  if (bytes < 1024) {
    return `${bytes} Bytes`;
  }

  if (bytes < 1024 * 1024) {
    return `${
      (
        bytes / 1024
      ).toFixed(0)
    } KB`;
  }

  return `${
    (
      bytes /
      1024 /
      1024
    ).toFixed(1)
  } MB`;
}

async function togglePlugin(
  filename,
  action,
) {
  const page = document.querySelector(
    ".plugins-page",
  );

  if (!page) {
    return;
  }

  const response = await fetch(
    `/api/web/servers/${page.dataset.serverId}/plugins/action`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        filename,
        action,
      }),
    },
  );

  const data = await response.json();

  if (!response.ok) {
    alert(
      data.error ||
        "Unable to change plugin",
    );

    return;
  }

  pluginRestartRequired = true;

  showPluginRestartAlert();

  await updatePluginsPage();
}

function openPluginRemoveModal(
  filename,
) {
  const plugin = pluginData.find(
    (item) => item.filename === filename,
  );

  if (!plugin) {
    return;
  }

  pluginPendingRemoval = plugin;

  document.getElementById(
    "remove-plugin-name",
  ).textContent = plugin.name;

  const checkbox = document.getElementById(
    "remove-plugin-config",
  );

  checkbox.checked = false;

  const option = document.getElementById(
    "remove-config-option",
  );

  const description = document.getElementById(
    "remove-config-description",
  );

  if (plugin.config_directory) {
    option.hidden = false;

    description.textContent =
      `This will also permanently delete plugins/${plugin.config_directory}/`;
  } else {
    option.hidden = true;

    description.textContent = "No matching plugin data directory was detected.";
  }

  document.getElementById(
    "plugin-remove-modal",
  ).hidden = false;
}

function closePluginRemoveModal() {
  document.getElementById(
    "plugin-remove-modal",
  ).hidden = true;

  pluginPendingRemoval = null;
}

async function confirmPluginRemove() {
  if (!pluginPendingRemoval) {
    return;
  }

  const page = document.querySelector(
    ".plugins-page",
  );

  const response = await fetch(
    `/api/web/servers/${page.dataset.serverId}/plugins/action`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        filename: pluginPendingRemoval.filename,

        action: "remove",

        remove_config: document.getElementById(
          "remove-plugin-config",
        ).checked,
      }),
    },
  );

  const data = await response.json();

  if (!response.ok) {
    alert(
      data.error ||
        "Unable to remove plugin",
    );

    return;
  }

  pluginRestartRequired = true;

  closePluginRemoveModal();

  showPluginRestartAlert();

  await updatePluginsPage();
}

function showPluginRestartAlert() {
  const alert = document.getElementById(
    "plugin-restart-alert",
  );

  if (alert) {
    alert.hidden = false;
  }
}

document.addEventListener(
  "input",
  function (event) {
    if (
      event.target.id ===
        "plugin-search"
    ) {
      renderPlugins();
    }
  },
);

updatePluginsPage();

async function updateOverviewPlugins() {
  const overview = document.querySelector(
    ".server-overview",
  );

  if (!overview) {
    return;
  }

  const serverId = overview.dataset.serverId;

  const active = document.getElementById("overview-plugin-active");
  const total = document.getElementById("overview-plugin-total");

  try {
    const response = await fetch(
      `/api/web/servers/${serverId}/plugins`,
    );

    if (!response.ok) {
      throw new Error();
    }

    const data = await response.json();

    const plugins = data.plugins || [];

    const enabledPlugins = plugins.filter(
      (plugin) => plugin.enabled,
    );

    if (active) active.textContent = enabledPlugins.length;
    if (total) total.textContent = plugins.length;

    const status = document.getElementById("overview-plugin-status");
    if (status) {
      const disabled = plugins.length - enabledPlugins.length;
      status.textContent = `${disabled} disabled`;
    }

    const bedrockPort = document.getElementById("overview-bedrock-port");
    const bedrockStatus = document.getElementById("overview-bedrock-status");
    if (bedrockPort && bedrockStatus) {
      bedrockPort.textContent = data.geyser?.port || "";
      bedrockStatus.textContent = !data.geyser?.installed
        ? "Geyser is not installed"
        : !data.geyser.enabled
        ? "Geyser is disabled"
        : data.geyser.port
        ? ""
        : "Geyser installed; port not detected";
    }
  } catch (error) {
    console.error(
      "Overview plugins error:",
      error,
    );

    if (active) active.textContent = "-";
    if (total) total.textContent = "-";
  }
}

updateOverviewPlugins();

function updateDocumentTitle() {
  const page = document.querySelector(
    "#page-content [data-page-title]",
  );

  const title = document.getElementById(
    "topbar-title",
  );

  if (!page || !title) {
    return;
  }

  const pageTitle = page.dataset.pageTitle;

  title.textContent = pageTitle;

  document.title = `${pageTitle} | Server Console`;
}

updateDocumentTitle();

async function uploadFiles(files) {
  const page = currentFilesPage();

  if (
    !page ||
    !files.length
  ) {
    return;
  }

  for (const file of files) {
    const form = new FormData();

    form.append(
      "path",
      page.dataset.currentPath || "",
    );

    form.append(
      "file",
      file,
    );

    const response = await fetch(
      `/servers/${page.dataset.serverId}/files/upload`,
      {
        method: "POST",
        body: form,
      },
    );

    if (!response.ok) {
      alert(
        `Unable to upload ${file.name}`,
      );

      return;
    }
  }

  reloadFilesPage();
}

let internalDraggedPath = null;

function handleInternalDragStart(event) {
  const row = event.currentTarget;

  internalDraggedPath = row.dataset.path;

  event.dataTransfer.effectAllowed = "move";

  event.dataTransfer.setData(
    "text/plain",
    internalDraggedPath,
  );
}

function handleFolderDragOver(event) {
  if (!internalDraggedPath) {
    return;
  }

  event.preventDefault();
  event.stopPropagation();

  event.currentTarget.classList.add(
    "drag-target",
  );

  event.dataTransfer.dropEffect = "move";
}

function handleFolderDragLeave(event) {
  event.currentTarget.classList.remove(
    "drag-target",
  );
}

async function handleFolderDrop(event) {
  if (!internalDraggedPath) {
    return;
  }

  event.preventDefault();
  event.stopPropagation();

  event.currentTarget.classList.remove(
    "drag-target",
  );

  const page = currentFilesPage();

  const destination = event.currentTarget.dataset.folderPath;

  const response = await fetch(
    `/api/web/servers/${page.dataset.serverId}/files/move`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        source: internalDraggedPath,

        destination,
      }),
    },
  );

  const data = await response.json();

  internalDraggedPath = null;

  if (!response.ok) {
    alert(
      data.error ||
        "Unable to move file",
    );

    return;
  }

  reloadFilesPage();
}

function handleFileBrowserDragOver(
  event,
) {
  const hasFiles = Array.from(
    event.dataTransfer.types,
  ).includes("Files");

  if (!hasFiles) {
    return;
  }

  event.preventDefault();

  event.currentTarget.classList.add(
    "external-drag",
  );

  event.dataTransfer.dropEffect = "copy";
}

function handleFileBrowserDragLeave(
  event,
) {
  if (
    !event.currentTarget.contains(
      event.relatedTarget,
    )
  ) {
    event.currentTarget.classList.remove(
      "external-drag",
    );
  }
}

function handleFileBrowserDrop(
  event,
) {
  event.preventDefault();

  event.currentTarget.classList.remove(
    "external-drag",
  );

  if (internalDraggedPath) {
    return;
  }

  const files = event.dataTransfer.files;

  if (
    files &&
    files.length
  ) {
    uploadFiles(
      files,
    );
  }
}

function handleFolderRowDragOver(event) {
  if (!internalDraggedPath) {
    return;
  }

  const row = event.currentTarget;

  const destination = row.dataset.folderPath;

  if (
    !destination ||
    destination === internalDraggedPath
  ) {
    return;
  }

  event.preventDefault();
  event.stopPropagation();

  row.classList.add(
    "drag-target",
  );

  const icon = row.querySelector(
    "[data-folder-icon]",
  );

  if (icon) {
    icon.classList.remove(
      "fa-folder",
    );

    icon.classList.add(
      "fa-folder-open",
    );
  }

  event.dataTransfer.dropEffect = "move";
}

function handleFolderRowDragLeave(event) {
  const row = event.currentTarget;

  if (
    row.contains(
      event.relatedTarget,
    )
  ) {
    return;
  }

  clearFolderDropTarget(
    row,
  );
}

function clearFolderDropTarget(row) {
  row.classList.remove(
    "drag-target",
  );

  const icon = row.querySelector(
    "[data-folder-icon]",
  );

  if (icon) {
    icon.classList.remove(
      "fa-folder-open",
    );

    icon.classList.add(
      "fa-folder",
    );
  }
}

async function handleFolderRowDrop(event) {
  if (!internalDraggedPath) {
    return;
  }

  event.preventDefault();
  event.stopPropagation();

  const row = event.currentTarget;

  const destination = row.dataset.folderPath;

  clearFolderDropTarget(
    row,
  );

  if (
    !destination ||
    destination === internalDraggedPath
  ) {
    internalDraggedPath = null;
    return;
  }

  const page = currentFilesPage();

  const response = await fetch(
    `/api/web/servers/${page.dataset.serverId}/files/move`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        source: internalDraggedPath,

        destination,
      }),
    },
  );

  const data = await response.json();

  internalDraggedPath = null;

  if (!response.ok) {
    alert(
      data.error ||
        "Unable to move file",
    );

    return;
  }

  reloadFilesPage();
}

document.addEventListener(
  "dragend",
  function () {
    internalDraggedPath = null;

    document
      .querySelectorAll(
        ".file-folder-row.drag-target",
      )
      .forEach(
        clearFolderDropTarget,
      );
  },
);

let backupData = [];
let backupPendingRestore = null;
let backupPendingDelete = null;

async function updateBackupsPage() {
  const page = document.querySelector(
    ".backups-page",
  );

  if (!page) {
    return;
  }

  try {
    const response = await fetch(
      `/api/web/servers/${page.dataset.serverId}/backups`,
    );

    if (!response.ok) {
      throw new Error();
    }

    const data = await response.json();

    backupData = data.backups || [];

    const warning = document.getElementById(
      "backup-running-warning",
    );

    if (warning) {
      warning.hidden = !data.running;
    }

    renderBackups(
      data.running,
    );
  } catch {
    const list = document.getElementById(
      "backup-list",
    );

    if (list) {
      list.textContent = "Unable to load backups.";
    }
  }
}

function renderBackups(
  serverRunning,
) {
  const list = document.getElementById(
    "backup-list",
  );

  if (!list) {
    return;
  }

  const count = document.getElementById(
    "backup-count",
  );

  if (count) {
    count.textContent = `${backupData.length} ${
      backupData.length === 1 ? "backup" : "backups"
    }`;
  }

  if (!backupData.length) {
    list.innerHTML = `
            <div class="empty-message backup-empty">
                No backups created yet.
            </div>
            `;

    return;
  }

  list.innerHTML = backupData.map(
    (backup) => `
                <div class="backup-row">

                    <div class="backup-main">

                        <i class="fa-solid fa-box-archive"></i>

                        <div>

                            <strong>
                                ${escapeHtml(backup.filename)}
                            </strong>

                            <small>
                                ${escapeHtml(backup.created_display)}
                                ·
                                ${escapeHtml(backup.size_display)}
                            </small>

                        </div>

                    </div>


                    <div class="backup-actions">

                        <a
                            class="button"
                            href="/servers/${
      document.querySelector(".backups-page").dataset.serverId
    }/backups/download?filename=${encodeURIComponent(backup.filename)}"
                        >
                            Download
                        </a>

                        <button
                            class="button"
                            ${serverRunning ? "disabled" : ""}
                            onclick="openRestoreBackupModal(
                                '${escapeJs(backup.filename)}'
                            )"
                        >
                            Restore
                        </button>

                        <button
                            class="button danger"
                            onclick="openDeleteBackupModal(
                                '${escapeJs(backup.filename)}'
                            )"
                        >
                            Delete
                        </button>

                    </div>

                </div>
            `,
  )
    .join("");
}

function openCreateBackupModal() {
  document.getElementById(
    "backup-label",
  ).value = "";

  document.getElementById(
    "backup-create-form",
  ).hidden = false;

  document.getElementById(
    "backup-create-progress",
  ).hidden = true;

  document.getElementById(
    "create-backup-modal",
  ).hidden = false;
}

function closeCreateBackupModal() {
  document.getElementById(
    "create-backup-modal",
  ).hidden = true;
}

let activeBackupJobId = null;

async function createBackup() {
  const page = document.querySelector(
    ".backups-page",
  );

  if (!page) {
    return;
  }

  const label = document
    .getElementById(
      "backup-label",
    )
    .value
    .trim();

  const response = await fetch(
    `/api/web/servers/${page.dataset.serverId}/backups/create`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        label,
      }),
    },
  );

  const data = await response.json();

  if (!response.ok) {
    alert(
      data.error ||
        "Unable to create backup",
    );

    return;
  }

  activeBackupJobId = data.job_id;

  document.getElementById(
    "backup-create-form",
  ).hidden = true;

  document.getElementById(
    "backup-create-progress",
  ).hidden = false;

  updateBackupJobs();
}

function openRestoreBackupModal(
  filename,
) {
  backupPendingRestore = filename;

  document.getElementById(
    "restore-backup-name",
  ).textContent = filename;

  document.getElementById(
    "restore-backup-modal",
  ).hidden = false;
}

function closeRestoreBackupModal() {
  document.getElementById(
    "restore-backup-modal",
  ).hidden = true;

  backupPendingRestore = null;
}

async function confirmRestoreBackup() {
  if (!backupPendingRestore) {
    return;
  }

  const page = document.querySelector(
    ".backups-page",
  );

  const response = await fetch(
    `/api/web/servers/${page.dataset.serverId}/backups/restore`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        filename: backupPendingRestore,
      }),
    },
  );

  const data = await response.json();

  if (!response.ok) {
    alert(
      data.error ||
        "Unable to restore backup",
    );

    return;
  }

  closeRestoreBackupModal();

  updateBackupsPage();
}

function openDeleteBackupModal(
  filename,
) {
  backupPendingDelete = filename;

  document.getElementById(
    "delete-backup-name",
  ).textContent = filename;

  document.getElementById(
    "delete-backup-modal",
  ).hidden = false;
}

function closeDeleteBackupModal() {
  document.getElementById(
    "delete-backup-modal",
  ).hidden = true;

  backupPendingDelete = null;
}

async function confirmDeleteBackup() {
  if (!backupPendingDelete) {
    return;
  }

  const page = document.querySelector(
    ".backups-page",
  );

  const response = await fetch(
    `/api/web/servers/${page.dataset.serverId}/backups/delete`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        filename: backupPendingDelete,
      }),
    },
  );

  const data = await response.json();

  if (!response.ok) {
    alert(
      data.error ||
        "Unable to delete backup",
    );

    return;
  }

  closeDeleteBackupModal();

  updateBackupsPage();
}

updateBackupsPage();

async function updatePropertiesPage() {
  const page = document.querySelector(
    ".properties-page",
  );

  if (!page) {
    return;
  }

  try {
    const response = await fetch(
      `/api/web/servers/${page.dataset.serverId}/properties`,
    );

    if (!response.ok) {
      throw new Error();
    }

    const data = await response.json();

    const p = data.properties;

    setValue(
      "property-motd",
      p.motd,
    );

    setValue(
      "property-server-port",
      p.server_port,
    );

    setValue(
      "property-max-players",
      p.max_players,
    );

    setValue(
      "property-difficulty",
      p.difficulty,
    );

    setValue(
      "property-gamemode",
      p.gamemode,
    );

    setChecked(
      "property-online-mode",
      p.online_mode,
    );

    setValue(
      "property-level-name",
      p.level_name,
    );

    setValue(
      "property-level-seed",
      p.level_seed,
    );

    setValue(
      "property-view-distance",
      p.view_distance,
    );

    setValue(
      "property-simulation-distance",
      p.simulation_distance,
    );

    setValue(
      "property-spawn-protection",
      p.spawn_protection,
    );

    setChecked(
      "property-allow-nether",
      p.allow_nether,
    );

    setChecked(
      "property-pvp",
      p.pvp,
    );

    setChecked(
      "property-hardcore",
      p.hardcore,
    );

    setChecked(
      "property-command-block",
      p.enable_command_block,
    );

    setChecked(
      "property-allow-flight",
      p.allow_flight,
    );

    setChecked(
      "property-whitelist",
      p.white_list,
    );

    setChecked(
      "property-enable-query",
      p.enable_query,
    );

    setChecked(
      "property-enable-rcon",
      p.enable_rcon,
    );

    setValue(
      "property-resource-pack",
      p.resource_pack,
    );
  } catch {
    const status = document.getElementById(
      "properties-save-status",
    );

    if (status) {
      status.textContent = "Unable to load properties.";
    }
  }
}

function setValue(
  id,
  value,
) {
  const element = document.getElementById(id);

  if (element) {
    element.value = value ?? "";
  }
}

function setChecked(
  id,
  value,
) {
  const element = document.getElementById(id);

  if (element) {
    element.checked = value === true;
  }
}

async function saveServerProperties(
  event,
) {
  event.preventDefault();

  const page = document.querySelector(
    ".properties-page",
  );

  if (!page) {
    return;
  }

  const payload = {
    motd: valueOf(
      "property-motd",
    ),

    server_port: numberOf(
      "property-server-port",
    ),

    max_players: numberOf(
      "property-max-players",
    ),

    difficulty: valueOf(
      "property-difficulty",
    ),

    gamemode: valueOf(
      "property-gamemode",
    ),

    online_mode: checkedOf(
      "property-online-mode",
    ),

    level_name: valueOf(
      "property-level-name",
    ),

    level_seed: valueOf(
      "property-level-seed",
    ),

    view_distance: numberOf(
      "property-view-distance",
    ),

    simulation_distance: numberOf(
      "property-simulation-distance",
    ),

    spawn_protection: numberOf(
      "property-spawn-protection",
    ),

    allow_nether: checkedOf(
      "property-allow-nether",
    ),

    pvp: checkedOf(
      "property-pvp",
    ),

    hardcore: checkedOf(
      "property-hardcore",
    ),

    enable_command_block: checkedOf(
      "property-command-block",
    ),

    allow_flight: checkedOf(
      "property-allow-flight",
    ),

    white_list: checkedOf(
      "property-whitelist",
    ),

    enable_query: checkedOf(
      "property-enable-query",
    ),

    enable_rcon: checkedOf(
      "property-enable-rcon",
    ),

    resource_pack: valueOf(
      "property-resource-pack",
    ),
  };

  const response = await fetch(
    `/api/web/servers/${page.dataset.serverId}/properties`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify(
        payload,
      ),
    },
  );

  const data = await response.json();

  const status = document.getElementById(
    "properties-save-status",
  );

  if (!response.ok) {
    if (status) {
      status.textContent = data.error ||
        "Save failed.";
    }

    return;
  }

  if (status) {
    status.textContent = "Saved";
  }

  const restartAlert = document.getElementById(
    "properties-restart-alert",
  );

  if (restartAlert) {
    restartAlert.hidden = false;
  }
}

function valueOf(id) {
  return (
    document
      .getElementById(id)
      ?.value ??
      ""
  );
}

function numberOf(id) {
  return Number(
    valueOf(id),
  );
}

function checkedOf(id) {
  return (
    document
      .getElementById(id)
      ?.checked ===
      true
  );
}

updatePropertiesPage();

async function saveOwnProfile() {
  const username = document
    .getElementById(
      "settings-profile-username",
    )
    ?.value
    .trim();

  const email = document
    .getElementById(
      "settings-profile-email",
    )
    ?.value
    .trim() ||
    "";

  const password = document
    .getElementById(
      "settings-profile-password",
    )
    ?.value ||
    "";

  const status = document.getElementById(
    "profile-save-status",
  );

  const response = await fetch(
    "/api/web/settings/profile",
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        username,
        password,
      }),
    },
  );

  const data = await response.json();

  if (!response.ok) {
    if (status) {
      status.textContent = data.error ||
        "Unable to save.";
    }

    return;
  }

  if (status) {
    status.textContent = "Saved";
  }

  const passwordInput = document.getElementById(
    "settings-profile-password",
  );

  if (passwordInput) {
    passwordInput.value = "";
  }
}

function openAddUserModal() {
  document.getElementById(
    "user-modal-title",
  ).textContent = "Add User";

  document.getElementById(
    "settings-user-id",
  ).value = "";

  document.getElementById(
    "settings-user-username",
  ).value = "";

  document.getElementById(
    "settings-user-password",
  ).value = "";

  document.getElementById(
    "settings-user-role",
  ).value = "user";

  document.getElementById(
    "settings-user-enabled",
  ).checked = true;

  document.getElementById(
    "settings-user-must-change-password",
  ).checked = true;

  document
    .querySelectorAll(
      ".settings-server-checkbox",
    )
    .forEach(
      (checkbox) => {
        checkbox.checked = false;
      },
    );

  document.getElementById(
    "settings-password-help",
  ).textContent = "Minimum 8 characters";

  document.getElementById(
    "delete-user-button",
  ).hidden = true;

  clearSettingsUserError();

  updateUserServerAccessVisibility();

  const modal = document.getElementById(
    "user-modal",
  );

  modal.hidden = false;

  document.getElementById(
    "settings-user-username",
  ).focus();
}

async function openEditUserModal(
  userId,
) {
  const response = await fetch(
    `/api/web/settings/users/${userId}`,
  );

  const data = await response.json();

  if (!response.ok) {
    alert(
      data.error ||
        "Unable to load user",
    );

    return;
  }

  document.getElementById(
    "user-modal-title",
  ).textContent = "Edit User";

  document.getElementById(
    "settings-user-id",
  ).value = data.id;

  document.getElementById(
    "settings-user-username",
  ).value = data.username;

  document.getElementById(
    "settings-user-password",
  ).value = "";

  document.getElementById(
    "settings-user-role",
  ).value = data.role;

  document.getElementById(
    "settings-user-enabled",
  ).checked = data.enabled;

  document.getElementById(
    "settings-user-must-change-password",
  ).checked = data.must_change_password;

  document.getElementById(
    "settings-password-help",
  ).textContent = "Leave blank to keep current password";

  const allowed = new Set(
    data.servers.map(
      String,
    ),
  );

  document
    .querySelectorAll(
      ".settings-server-checkbox",
    )
    .forEach(
      (checkbox) => {
        checkbox.checked = allowed.has(
          checkbox.value,
        );
      },
    );

  document.getElementById(
    "delete-user-button",
  ).hidden = false;

  clearSettingsUserError();

  updateUserServerAccessVisibility();

  document.getElementById(
    "user-modal",
  ).hidden = false;
}

function closeUserModal() {
  document.getElementById(
    "user-modal",
  ).hidden = true;
}

function updateUserServerAccessVisibility() {
  const role = document.getElementById(
    "settings-user-role",
  )?.value;

  const access = document.getElementById(
    "settings-server-access",
  );

  if (!access) {
    return;
  }

  access.hidden = role === "admin";
}

function selectedSettingsServers() {
  return Array
    .from(
      document.querySelectorAll(
        ".settings-server-checkbox:checked",
      ),
    )
    .map(
      (checkbox) =>
        Number(
          checkbox.value,
        ),
    );
}

async function saveSettingsUser() {
  const id = document
    .getElementById(
      "settings-user-id",
    )
    .value;

  const payload = {
    username: document
      .getElementById(
        "settings-user-username",
      )
      .value
      .trim(),

    password: document
      .getElementById(
        "settings-user-password",
      )
      .value,

    role: document
      .getElementById(
        "settings-user-role",
      )
      .value,

    enabled: document
      .getElementById(
        "settings-user-enabled",
      )
      .checked,

    must_change_password: document.getElementById(
      "settings-user-must-change-password",
    ).checked,

    servers: selectedSettingsServers(),
  };

  const url = id ? `/api/web/settings/users/${id}` : "/api/web/settings/users";

  const response = await fetch(
    url,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify(
        payload,
      ),
    },
  );

  const data = await response.json();

  if (!response.ok) {
    showSettingsUserError(
      data.error ||
        "Unable to save user.",
    );

    return;
  }

  closeUserModal();

  window.location.reload();
}

async function deleteSettingsUser() {
  const id = document
    .getElementById(
      "settings-user-id",
    )
    .value;

  if (!id) {
    return;
  }

  if (
    !confirm(
      "Delete this user?",
    )
  ) {
    return;
  }

  const response = await fetch(
    `/api/web/settings/users/${id}`,
    {
      method: "DELETE",
    },
  );

  const data = await response.json();

  if (!response.ok) {
    showSettingsUserError(
      data.error ||
        "Unable to delete user.",
    );

    return;
  }

  window.location.reload();
}

function showSettingsUserError(
  message,
) {
  const error = document.getElementById(
    "settings-user-error",
  );

  error.textContent = message;

  error.hidden = false;
}

function clearSettingsUserError() {
  const error = document.getElementById(
    "settings-user-error",
  );

  if (!error) {
    return;
  }

  error.textContent = "";
  error.hidden = true;
}

async function updateSMTPSettings() {
  const host = document.getElementById(
    "smtp-host",
  );

  if (!host) {
    return;
  }

  try {
    const response = await fetch(
      "/api/web/settings/smtp",
    );

    if (!response.ok) {
      throw new Error();
    }

    const data = await response.json();

    setValue(
      "smtp-host",
      data.smtp_host,
    );

    setValue(
      "smtp-port",
      data.smtp_port,
    );

    setValue(
      "smtp-username",
      data.smtp_username,
    );

    setValue(
      "smtp-password",
      "",
    );

    setValue(
      "smtp-security",
      data.smtp_security,
    );

    setValue(
      "smtp-from-name",
      data.smtp_from_name,
    );

    setValue(
      "smtp-from-address",
      data.smtp_from_address,
    );
  } catch {
    const status = document.getElementById(
      "smtp-save-status",
    );

    if (status) {
      status.textContent = "Unable to load SMTP settings.";
    }
  }
}

async function saveSMTPSettings() {
  const status = document.getElementById(
    "smtp-save-status",
  );

  const payload = {
    smtp_host: valueOf(
      "smtp-host",
    ),

    smtp_port: valueOf(
      "smtp-port",
    ),

    smtp_username: valueOf(
      "smtp-username",
    ),

    smtp_password: valueOf(
      "smtp-password",
    ),

    smtp_security: valueOf(
      "smtp-security",
    ),

    smtp_from_name: valueOf(
      "smtp-from-name",
    ),

    smtp_from_address: valueOf(
      "smtp-from-address",
    ),
  };

  const response = await fetch(
    "/api/web/settings/smtp",
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify(
        payload,
      ),
    },
  );

  const data = await response.json();

  if (!response.ok) {
    if (status) {
      status.textContent = data.error ||
        "Unable to save SMTP settings.";
    }

    return;
  }

  if (status) {
    status.textContent = "Saved";
  }

  const password = document.getElementById(
    "smtp-password",
  );

  if (password) {
    password.value = "";
  }
}

async function sendSMTPTest() {
  const status = document.getElementById(
    "smtp-save-status",
  );

  if (status) {
    status.textContent = "Sending...";
  }

  const response = await fetch(
    "/api/web/settings/smtp/test",
    {
      method: "POST",
    },
  );

  const data = await response.json();

  if (!response.ok) {
    if (status) {
      status.textContent = data.error ||
        "Test failed.";
    }

    return;
  }

  if (status) {
    status.textContent = "Test email sent.";
  }
}

updateSMTPSettings();

async function updateTFASettings() {
  const disabled = document.getElementById(
    "tfa-disabled-controls",
  );

  const enabled = document.getElementById(
    "tfa-enabled-controls",
  );

  if (
    !disabled ||
    !enabled
  ) {
    return;
  }

  try {
    const response = await fetch(
      "/api/web/settings/tfa",
    );

    if (!response.ok) {
      throw new Error();
    }

    const data = await response.json();

    disabled.hidden = data.enabled;

    enabled.hidden = !data.enabled;
  } catch {
    disabled.hidden = true;
    enabled.hidden = true;
  }
}

async function beginTFASetup() {
  const response = await fetch(
    "/api/web/settings/tfa/setup",
    {
      method: "POST",
    },
  );

  const data = await response.json();

  if (!response.ok) {
    alert(
      data.error ||
        "Unable to start 2FA setup",
    );

    return;
  }

  document.getElementById(
    "tfa-qr-code",
  ).src = data.qr_code;

  document.getElementById(
    "tfa-secret",
  ).textContent = data.secret;

  document.getElementById(
    "tfa-confirm-code",
  ).value = "";

  const error = document.getElementById(
    "tfa-setup-error",
  );

  error.hidden = true;

  document.getElementById(
    "tfa-setup-modal",
  ).hidden = false;

  document.getElementById(
    "tfa-confirm-code",
  ).focus();
}

function closeTFASetupModal() {
  document.getElementById(
    "tfa-setup-modal",
  ).hidden = true;
}

async function confirmTFASetup() {
  const code = document
    .getElementById(
      "tfa-confirm-code",
    )
    .value
    .trim();

  const response = await fetch(
    "/api/web/settings/tfa/confirm",
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        code,
      }),
    },
  );

  const data = await response.json();

  if (!response.ok) {
    const error = document.getElementById(
      "tfa-setup-error",
    );

    error.textContent = data.error ||
      "Invalid code";

    error.hidden = false;

    return;
  }

  closeTFASetupModal();

  showRecoveryCodes(
    data.recovery_codes,
  );

  updateTFASettings();
}

function showRecoveryCodes(
  codes,
) {
  const container = document.getElementById(
    "tfa-recovery-codes",
  );

  container.innerHTML = codes.map(
    (code) => `
                <code>
                    ${escapeHtml(code)}
                </code>
            `,
  ).join("");

  document.getElementById(
    "tfa-recovery-modal",
  ).hidden = false;
}

function closeRecoveryCodesModal() {
  document.getElementById(
    "tfa-recovery-modal",
  ).hidden = true;
}

async function regenerateRecoveryCodes() {
  if (
    !confirm(
      "Generate new recovery codes? Existing unused codes will stop working.",
    )
  ) {
    return;
  }

  const response = await fetch(
    "/api/web/settings/tfa/recovery-codes",
    {
      method: "POST",
    },
  );

  const data = await response.json();

  if (!response.ok) {
    alert(
      data.error ||
        "Unable to generate recovery codes",
    );

    return;
  }

  showRecoveryCodes(
    data.recovery_codes,
  );
}

function openDisableTFAModal() {
  document.getElementById(
    "tfa-disable-password",
  ).value = "";

  document.getElementById(
    "tfa-disable-error",
  ).hidden = true;

  document.getElementById(
    "tfa-disable-modal",
  ).hidden = false;

  document.getElementById(
    "tfa-disable-password",
  ).focus();
}

function closeDisableTFAModal() {
  document.getElementById(
    "tfa-disable-modal",
  ).hidden = true;
}

async function disableTFA() {
  const password = document
    .getElementById(
      "tfa-disable-password",
    )
    .value;

  const response = await fetch(
    "/api/web/settings/tfa/disable",
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        password,
      }),
    },
  );

  const data = await response.json();

  if (!response.ok) {
    const error = document.getElementById(
      "tfa-disable-error",
    );

    error.textContent = data.error ||
      "Unable to disable 2FA";

    error.hidden = false;

    return;
  }

  closeDisableTFAModal();

  updateTFASettings();
}

updateTFASettings();

async function updateBackupJobs() {
  const page = document.querySelector(
    ".backups-page",
  );

  if (!page) {
    return;
  }

  try {
    const response = await fetch(
      `/api/web/servers/${page.dataset.serverId}/backups/jobs`,
    );

    if (!response.ok) {
      return;
    }

    const data = await response.json();

    renderBackupJobs(
      data.jobs || [],
    );

    if (activeBackupJobId) {
      const job = (data.jobs || []).find(
        (item) =>
          item.id ===
            activeBackupJobId,
      );

      if (job) {
        updateBackupModalProgress(
          job,
        );
      }
    }
  } catch {
    // leave existing UI alone
  }
}

function renderBackupJobs(
  jobs,
) {
  const container = document.getElementById(
    "backup-jobs",
  );

  if (!container) {
    return;
  }

  const active = jobs.filter(
    (job) =>
      [
        "queued",
        "saving",
        "archiving",
      ].includes(
        job.status,
      ),
  );

  if (!active.length) {
    container.innerHTML = "";
    return;
  }

  container.innerHTML = active.map(
    (job) => `
                <div class="overview-card backup-job-card">

                    <div class="backup-job-header">

                        <div>
                            <strong>
                                Backup in progress
                            </strong>

                            <small>
                                ${
      escapeHtml(
        job.message ||
          job.status,
      )
    }
                            </small>
                        </div>

                        <strong>
                            ${job.progress}%
                        </strong>

                    </div>

                    <div class="upload-progress-track">

                        <div
                            class="upload-progress-bar"
                            style="width: ${job.progress}%"
                        ></div>

                    </div>

                </div>
            `,
  )
    .join("");
}

function updateBackupModalProgress(
  job,
) {
  const message = document.getElementById(
    "backup-create-message",
  );

  const bar = document.getElementById(
    "backup-create-progress-bar",
  );

  const percent = document.getElementById(
    "backup-create-progress-percent",
  );

  if (message) {
    message.textContent = job.message ||
      job.status;
  }

  if (bar) {
    bar.style.width = `${job.progress}%`;
  }

  if (percent) {
    percent.textContent = `${job.progress}%`;
  }

  if (
    job.status === "complete" ||
    job.status === "failed"
  ) {
    activeBackupJobId = null;

    if (
      job.status === "complete"
    ) {
      updateBackupsPage();
    }
  }
}

setInterval(
  updateBackupJobs,
  1500,
);

updateBackupJobs();

async function serverAction(
  action,
) {
  const topbar = document.querySelector(
    ".topbar",
  );

  if (!topbar) {
    return;
  }

  const serverId = topbar.dataset.serverId;

  if (!serverId) {
    return;
  }

  try {
    const response = await fetch(
      `/api/web/servers/${serverId}/${action}`,
      {
        method: "POST",
      },
    );

    const data = await response.json();

    if (!response.ok) {
      alert(
        data.error ||
          `Unable to ${action} server`,
      );

      return;
    }

    // Give the process a moment to change state.
    setTimeout(
      updateServerStatus,
      500,
    );
  } catch (error) {
    console.error(
      "Server action failed:",
      error,
    );

    alert(
      `Unable to ${action} server`,
    );
  }
}

async function updateServerProcessStats() {
  const page = document.querySelector(
    ".server-overview",
  );

  if (!page) {
    return;
  }

  const serverId = page.dataset.serverId;

  try {
    const response = await fetch(
      `/api/web/servers/${serverId}/process-stats`,
    );

    if (!response.ok) {
      throw new Error();
    }

    const data = await response.json();

    const cpuValue = document.getElementById(
      "overview-cpu-value",
    );

    const memoryValue = document.getElementById(
      "overview-memory-value",
    );

    const uptimeValue = document.getElementById(
      "overview-uptime",
    );

    if (!data.running) {
      if (cpuValue) {
        cpuValue.textContent = "0%";
      }

      if (memoryValue) {
        memoryValue.textContent = "0 MB";
      }

      if (uptimeValue) {
        uptimeValue.textContent = "-";
      }

      return;
    }

    if (cpuValue) {
      cpuValue.textContent = `${data.cpu_percent}%`;
    }

    if (memoryValue) {
      const configuredMemory = memoryValue.dataset.memory;

      memoryValue.textContent = `${formatMemoryBytes(data.memory_used)} / ${
        formatConfiguredMemory(configuredMemory)
      }`;
    }

    if (uptimeValue) {
      uptimeValue.textContent = formatUptime(data.uptime_seconds);
    }
  } catch (error) {
    console.error(
      "Process stats error:",
      error,
    );
  }
}

setInterval(
  updateServerProcessStats,
  2000,
);

updateServerProcessStats();

function formatUptime(value) {
  const totalSeconds = Math.max(0, Math.floor(Number(value) || 0));
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (days) return `${days}d ${hours}h ${minutes}m`;
  if (hours) return `${hours}h ${minutes}m`;
  if (minutes) return `${minutes}m ${seconds}s`;
  return `${seconds}s`;
}

function formatMemoryBytes(bytes) {
  const mb = bytes / 1024 / 1024;

  if (mb >= 1024) {
    const gb = mb / 1024;

    return `${gb.toFixed(2)} GB`;
  }

  return `${mb.toFixed(0)} MB`;
}

function formatConfiguredMemory(memory) {
  if (!memory) {
    return "";
  }

  return memory
    .replace(/(\d+)G$/i, "$1 GB")
    .replace(/(\d+)M$/i, "$1 MB");
}

let consoleUpdateTag = null;

async function updateConsoleVersionStatus() {
  const status = document.getElementById(
    "console-update-status",
  );

  if (!status) {
    return;
  }

  const button = document.getElementById(
    "console-update-button",
  );

  try {
    const response = await fetch(
      "/api/web/settings/update",
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.error ||
          "Unable to check",
      );
    }

    if (
      data.release_available ===
        false
    ) {
      status.textContent = "No published releases";

      button.hidden = true;

      return;
    }

    if (data.update_available) {
      consoleUpdateTag = data.tag;

      status.textContent = `v${data.latest_version} available`;

      button.hidden = false;
    } else {
      consoleUpdateTag = null;

      status.textContent = "Up to date";

      button.hidden = true;
    }
  } catch {
    status.textContent = "Unable to check for updates";

    button.hidden = true;
  }
}

updateConsoleVersionStatus();

async function upgradeConsole() {
  if (
    !consoleUpdateTag ||
    !confirm(
      `Install ${consoleUpdateTag}? A verified backup will be created first.`,
    )
  ) return;
  const button = document.getElementById("console-update-button");
  const status = document.getElementById("console-update-status");
  button.disabled = true;
  status.textContent = "Downloading and verifying...";
  try {
    const response = await fetch("/api/web/settings/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tag: consoleUpdateTag }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Update failed");
    status.textContent = "Installed; restarting console...";
    if (data.rollback_id) {
      sessionStorage.setItem("consoleRollbackId", data.rollback_id);
      document.getElementById("console-rollback-button").hidden = false;
    }
    button.hidden = true;
    await waitForConsoleRestart();
  } catch (error) {
    status.textContent = error.message;
    button.disabled = false;
  }
}

function delay(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function waitForConsoleRestart() {
  const status = document.getElementById("console-update-status");
  const deadline = Date.now() + 90000;

  await delay(2500);
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`/health?restart=${Date.now()}`, {
        cache: "no-store",
      });
      if (response.ok) {
        window.location.reload();
        return;
      }
    } catch {
      // The service is expected to be briefly unavailable while systemd restarts it.
    }
    await delay(1000);
  }

  if (status) {
    status.textContent = "Restart is taking longer than expected; refresh this page shortly";
  }
  const button = document.getElementById("console-restart-button");
  if (button) button.disabled = false;
}

async function restartConsoleService() {
  if (!confirm("Restart STEMCraft Console now?")) return;

  const button = document.getElementById("console-restart-button");
  const status = document.getElementById("console-update-status");
  button.disabled = true;
  status.textContent = "Restarting console...";

  try {
    const response = await fetch("/api/web/settings/restart", {
      method: "POST",
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Restart failed");
    await waitForConsoleRestart();
  } catch (error) {
    status.textContent = error.message;
    button.disabled = false;
  }
}

async function systemServerAction(serverId, action) {
  const response = await fetch(`/api/web/servers/${serverId}/${action}`, {
    method: "POST",
  });
  const data = await response.json();
  if (!response.ok) return alert(data.error || `Unable to ${action} server`);
  setTimeout(updateSystemStats, 500);
}

async function loadPaperVersionStatus() {
  const page = document.querySelector(
    ".paper-management[data-server-id], .server-overview[data-server-id]",
  );
  const detail = document.getElementById("paper-version-detail");
  if (!page || !detail) return;
  try {
    const response = await fetch(
      `/api/web/servers/${page.dataset.serverId}/paper`,
    );
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Unable to check Paper");
    const buildText = data.builds_behind === null
      ? "build status unknown"
      : data.builds_behind === 0
      ? `build ${data.current_build || data.latest_build} is current`
      : `${data.builds_behind} builds behind (${data.latest_build} latest)`;
    const sortedVersions = sortMinecraftVersions(data.versions || []);
    const newestVersion = sortedVersions[0] || data.latest_version;
    const versionText = newestVersion && newestVersion !== data.current_version
      ? ` · ${newestVersion} available`
      : "";
    detail.textContent = `${buildText}${versionText}`;
    const button = document.getElementById("paper-update-button");
    const select = document.getElementById("paper-version-select");
    if (select) {
      select.innerHTML = sortedVersions.map((version) =>
        `<option value="${escapeHtml(version)}" ${
          version === data.current_version ? "selected" : ""
        }>${escapeHtml(version)}</option>`
      ).join("");
    }
    populatePaperBuilds(data.builds || [], data.current_build);
    if (button) {
      button.disabled = data.running;
      button.title = data.running
        ? "Stop the server before changing Paper"
        : "";
    }
  } catch (error) {
    detail.textContent = error.message;
  }
}

function sortMinecraftVersions(versions) {
  return [...new Set(versions)].sort((left, right) => {
    const leftParts = String(left).match(/\d+/g)?.map(Number) || [];
    const rightParts = String(right).match(/\d+/g)?.map(Number) || [];
    const length = Math.max(leftParts.length, rightParts.length);
    for (let index = 0; index < length; index += 1) {
      const difference = (rightParts[index] || 0) - (leftParts[index] || 0);
      if (difference) return difference;
    }
    return String(right).localeCompare(String(left));
  });
}

function populatePaperBuilds(builds, installedBuild = null) {
  const select = document.getElementById("paper-build-select");
  if (!select) return;
  if (!builds.length) {
    select.innerHTML = "<option>No build data — restart the panel</option>";
    return;
  }
  select.innerHTML = builds.map((build, index) => {
    const labels = [];
    if (index === 0) labels.push("latest");
    if (String(build.id) === String(installedBuild)) labels.push("installed");
    if (build.channel && build.channel !== "STABLE") {
      labels.push(build.channel.toLowerCase());
    }
    return `<option value="${escapeHtml(build.id)}">Build ${
      escapeHtml(build.id)
    }${labels.length ? ` — ${labels.join(", ")}` : ""}</option>`;
  }).join("");
  const button = document.getElementById("paper-update-button");
  if (button && builds.length) {
    button.textContent = "Download and replace JAR";
  }
}

function openDeleteServerModal() {
  document.getElementById("delete-server-files").checked = false;
  document.getElementById("delete-server-error").textContent = "";
  document.getElementById("delete-server-modal").hidden = false;
  document.getElementById("confirm-delete-server").focus();
}

function closeDeleteServerModal() {
  document.getElementById("delete-server-modal").hidden = true;
}

async function confirmDeleteServer() {
  const page = document.querySelector(".properties-page[data-server-id]");
  const button = document.getElementById("confirm-delete-server");
  const error = document.getElementById("delete-server-error");
  button.disabled = true;
  error.textContent = "Deleting server...";

  try {
    const response = await fetch(`/api/web/servers/${page.dataset.serverId}/delete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        confirmed: true,
        delete_files: document.getElementById("delete-server-files").checked,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Unable to delete server");
    if (data.warning) alert(data.warning);
    window.location.href = "/servers";
  } catch (requestError) {
    error.textContent = requestError.message;
    button.disabled = false;
  }
}

async function loadPaperBuilds(version) {
  const page = document.querySelector(".paper-management[data-server-id]");
  const select = document.getElementById("paper-build-select");
  const button = document.getElementById("paper-update-button");
  if (!page || !select) return;
  select.innerHTML = "<option>Loading builds...</option>";
  if (button) button.disabled = true;
  try {
    const response = await fetch(
      `/api/web/servers/${page.dataset.serverId}/paper?version=${
        encodeURIComponent(version)
      }`,
    );
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Unable to load builds");
    populatePaperBuilds(data.builds || [], data.current_build);
    if (button) button.disabled = data.running || !data.builds?.length;
  } catch (error) {
    select.innerHTML = `<option>${escapeHtml(error.message)}</option>`;
  }
}

async function installPaperVersion() {
  const page = document.querySelector(".paper-management[data-server-id]");
  const message = document.getElementById("paper-update-message");
  message.textContent = "Downloading and verifying Paper...";
  try {
    const response = await fetch(
      `/api/web/servers/${page.dataset.serverId}/paper`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          version: document.getElementById("paper-version-select").value,
          build: document.getElementById("paper-build-select").value,
        }),
      },
    );
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Paper update failed");
    message.textContent =
      `Paper ${data.version} build ${data.build} installed.`;
    setTimeout(() => window.location.reload(), 800);
  } catch (error) {
    message.textContent = error.message;
  }
}

loadPaperVersionStatus();

async function rollbackConsoleUpdate() {
  const rollbackId = sessionStorage.getItem("consoleRollbackId");
  if (
    !rollbackId ||
    !confirm("Restore the application files from before this update?")
  ) return;
  const button = document.getElementById("console-rollback-button");
  const status = document.getElementById("console-update-status");
  button.disabled = true;
  status.textContent = "Restoring previous version...";
  try {
    const response = await fetch("/api/web/settings/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "rollback", rollback_id: rollbackId }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Rollback failed");
    status.textContent = "Previous version restored; restarting console...";
    sessionStorage.removeItem("consoleRollbackId");
    button.hidden = true;
    await waitForConsoleRestart();
  } catch (error) {
    status.textContent = error.message;
    button.disabled = false;
  }
}

function automationPage() {
  return document.querySelector(
    ".server-overview[data-server-id], .backups-page[data-server-id]",
  );
}

function drawMetricChart(canvasId, rows, value, label) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ratio = window.devicePixelRatio || 1;
  const width = Math.max(300, canvas.clientWidth);
  const height = 120;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  const context = canvas.getContext("2d");
  context.scale(ratio, ratio);
  context.clearRect(0, 0, width, height);
  const values = rows.map((row) => Number(value(row) || 0));
  if (!values.length) {
    context.fillStyle = "#94a3b8";
    context.fillText("No historical data yet", 8, 24);
    return;
  }
  const maximum = Math.max(1, ...values);
  context.strokeStyle = "#38bdf8";
  context.lineWidth = 2;
  context.beginPath();
  values.forEach((point, index) => {
    const x = values.length === 1
      ? 0
      : index * (width - 2) / (values.length - 1);
    const y = height - 18 - (point / maximum) * (height - 28);
    index ? context.lineTo(x, y) : context.moveTo(x, y);
  });
  context.stroke();
  context.fillStyle = "#94a3b8";
  context.fillText(
    `${label}: ${
      values.at(-1).toLocaleString()
    }  Max: ${maximum.toLocaleString()}`,
    8,
    height - 3,
  );
}

async function loadServerMetrics() {
  const page = automationPage();
  if (!page || !document.getElementById("metric-cpu")) return;
  const hours = document.getElementById("metrics-range")?.value || 24;
  try {
    const response = await fetch(
      `/api/web/servers/${page.dataset.serverId}/metrics?hours=${hours}`,
    );
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Unable to load metrics");
    const rows = data.metrics || [];
    drawMetricChart("metric-cpu", rows, (row) => row.cpu_percent, "CPU %");
    drawMetricChart(
      "metric-memory",
      rows,
      (row) => Math.round(row.memory_bytes / 1048576),
      "MiB",
    );
    drawMetricChart(
      "metric-players",
      rows,
      (row) => row.player_count,
      "Players",
    );
    drawMetricChart(
      "metric-uptime",
      rows,
      (row) => Math.round((row.uptime_seconds || 0) / 60),
      "Minutes",
    );
  } catch (error) {
    ["metric-cpu", "metric-memory", "metric-players", "metric-uptime"].forEach(
      (id) => drawMetricChart(id, [], () => 0, error.message),
    );
  }
}

async function loadServerSchedules() {
  const page = automationPage();
  const list = document.getElementById("schedule-list");
  if (!page || !list) return;
  try {
    const response = await fetch(
      `/api/web/servers/${page.dataset.serverId}/schedules`,
    );
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Unable to load schedules");
    const tasks = (data.tasks || []).filter((task) => task.enabled);
    list.innerHTML = tasks.length
      ? tasks.map((task) => `
            <div class="schedule-row"><div><strong>${
        escapeHtml(task.name)
      }</strong><br>
            <small>${
        task.task_type === "backup"
          ? `Backup; keep ${task.retention_count || "all"}`
          : escapeHtml(task.command)
      } · every ${task.interval_minutes} minutes</small></div>
            <button class="button" onclick="deleteServerSchedule(${
        Number(task.id)
      })">Disable</button></div>`).join("")
      : '<div class="empty-message">No active schedules.</div>';
    const runs = document.getElementById("schedule-runs");
    runs.innerHTML = (data.runs || []).slice(0, 10).map((run) => `
            <div class="schedule-run"><span><strong>${
      escapeHtml(run.task_type)
    }</strong> ${escapeHtml(run.status)}</span>
            <small>${escapeHtml(run.detail || "")} · ${
      new Date(run.started_at).toLocaleString()
    }</small></div>`).join("");
  } catch (error) {
    list.textContent = error.message;
  }
}

function toggleScheduleFields(type) {
  const form = document.getElementById("schedule-form");
  if (!form) return;
  form.elements.command.hidden = type !== "command";
  form.elements.command.required = type === "command";
  form.elements.retention_count.hidden = type !== "backup";
}

async function createServerSchedule(event) {
  event.preventDefault();
  const page = automationPage();
  const form = event.currentTarget;
  const payload = Object.fromEntries(new FormData(form));
  const response = await fetch(
    `/api/web/servers/${page.dataset.serverId}/schedules`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
  const data = await response.json();
  if (!response.ok) return alert(data.error || "Unable to add schedule");
  form.reset();
  toggleScheduleFields("backup");
  loadServerSchedules();
}

async function deleteServerSchedule(taskId) {
  const page = automationPage();
  const response = await fetch(
    `/api/web/servers/${page.dataset.serverId}/schedules/${taskId}`,
    { method: "DELETE" },
  );
  const data = await response.json();
  if (!response.ok) return alert(data.error || "Unable to disable schedule");
  loadServerSchedules();
}

loadServerMetrics();
loadServerSchedules();
