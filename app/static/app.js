const recentToasts = new Map();

function showToast(message, type = "info", timeout = 4500) {
  const text = String(message || "").trim();
  if (!text) return;
  const now = Date.now();
  if (now - (recentToasts.get(`${type}:${text}`) || 0) < 1200) return;
  recentToasts.set(`${type}:${text}`, now);

  let region = document.getElementById("toast-region");
  if (!region) {
    region = document.createElement("div");
    region.id = "toast-region";
    region.className = "toast-region";
    region.setAttribute("aria-live", "polite");
    document.body.append(region);
  }
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.setAttribute("role", type === "error" ? "alert" : "status");
  const icon = document.createElement("i");
  icon.className = type === "success"
    ? "fa-solid fa-circle-check"
    : type === "error"
      ? "fa-solid fa-circle-exclamation"
      : type === "warning"
        ? "fa-solid fa-triangle-exclamation"
      : "fa-solid fa-circle-info";
  const content = document.createElement("span");
  content.textContent = text;
  const close = document.createElement("button");
  close.type = "button";
  close.className = "toast-close";
  close.setAttribute("aria-label", "Dismiss notification");
  close.innerHTML = "&times;";
  close.addEventListener("click", () => toast.remove());
  toast.append(icon, content, close);
  region.append(toast);
  requestAnimationFrame(() => toast.classList.add("visible"));
  window.setTimeout(() => {
    toast.classList.remove("visible");
    window.setTimeout(() => toast.remove(), 200);
  }, timeout);
}

function clearFieldError(field) {
  if (!field) return;
  field.classList.remove("field-invalid");
  field.removeAttribute("aria-invalid");
  if (field.nextElementSibling?.classList.contains("field-error-message")) {
    field.nextElementSibling.remove();
  }
}

function setFieldError(field, message) {
  if (!field) return false;
  clearFieldError(field);
  field.classList.add("field-invalid");
  field.setAttribute("aria-invalid", "true");
  const error = document.createElement("small");
  error.className = "field-error-message";
  error.textContent = message;
  field.insertAdjacentElement("afterend", error);
  return true;
}

function clearFormErrors(form) {
  if (!form) return;
  form.querySelectorAll(".field-invalid").forEach((field) => clearFieldError(field));
  form.querySelectorAll(".field-error-message").forEach((error) => error.remove());
}

function fieldForServerError(form, fieldName) {
  if (!form || !fieldName) return null;
  const normalized = String(fieldName).replaceAll("_", "-");
  return form.querySelector(`[name="${CSS.escape(fieldName)}"]`)
    || form.querySelector(`#property-${CSS.escape(normalized)}`)
    || form.querySelector(`#${CSS.escape(normalized)}`);
}

function showFormError(form, message, fieldName = null) {
  const field = fieldForServerError(form, fieldName);
  if (field) {
    setFieldError(field, message);
    field.focus();
  }
  showToast(message, "error");
}

document.addEventListener("invalid", (event) => {
  const field = event.target;
  if (!(field instanceof HTMLInputElement || field instanceof HTMLSelectElement || field instanceof HTMLTextAreaElement)) return;
  setFieldError(field, field.validationMessage || "Check this value");
  showToast("Please correct the highlighted fields.", "error");
}, true);

document.addEventListener("input", (event) => clearFieldError(event.target));
document.addEventListener("change", (event) => clearFieldError(event.target));

// Existing actions that still call alert now use the common non-blocking UI.
window.alert = (message) => showToast(message, "error");

const nativeFetch = window.fetch.bind(window);
window.fetch = async (...args) => {
  try {
    const response = await nativeFetch(...args);
    const request = args[0];
    const options = args[1] || {};
    const method = String(options.method || request?.method || "GET").toUpperCase();
    if (!new Set(["GET", "HEAD", "OPTIONS"]).has(method)) {
      response.clone().json().then((data) => {
        if (data?.suppress_toast) return;
        const message = data?.message || data?.error;
        if (!response.ok) {
          showToast(message || "The action could not be completed.", "error");
        } else {
          showToast(message || "Action completed successfully.", "success");
        }
      }).catch(() => {
        showToast(
          response.ok ? "Action completed successfully." : "The action could not be completed.",
          response.ok ? "success" : "error",
        );
      });
    }
    return response;
  } catch (error) {
    showToast("Unable to connect to the server.", "error");
    throw error;
  }
};

document.addEventListener("htmx:afterRequest", (event) => {
  const detail = event.detail || {};
  const verb = String(detail.requestConfig?.verb || "GET").toUpperCase();
  if (new Set(["GET", "HEAD", "OPTIONS"]).has(verb)) return;
  let data = {};
  try {
    data = JSON.parse(detail.xhr?.responseText || "{}");
  } catch {
    data = {};
  }
  if (detail.successful) {
    clearFormErrors(detail.elt?.closest?.("form"));
    showToast(data.message || "Action completed successfully.", "success");
  } else {
    const message = data.error || "The action could not be completed.";
    showFormError(detail.elt?.closest?.("form"), message, data.field);
  }
});

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

function setMobileSidebar(open) {
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("sidebar-backdrop");
  const toggle = document.querySelector(".mobile-menu-toggle");
  sidebar?.classList.toggle("mobile-open", open);
  backdrop?.classList.toggle("open", open);
  document.body.classList.toggle("mobile-nav-open", open);
  toggle?.setAttribute("aria-expanded", String(open));
}

function toggleMobileSidebar() {
  setMobileSidebar(!document.getElementById("sidebar")?.classList.contains("mobile-open"));
}

function closeMobileSidebar() {
  setMobileSidebar(false);
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
    if (event.target.closest("#sidebar a")) {
      closeMobileSidebar();
    }
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

window.addEventListener("resize", () => {
  if (window.innerWidth > 900) closeMobileSidebar();
});

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
    const javaList = document.getElementById("system-java-list");
    if (javaList) {
      javaList.innerHTML = (stats.java_runtimes || []).length
        ? stats.java_runtimes.map((runtime) => `
            <div class="system-instance-row"><div><strong>Java ${Number(runtime.major)}</strong>
            <small>${escapeHtml(runtime.name)} · ${escapeHtml(runtime.path)}</small></div></div>`).join("")
        : '<div class="empty-message">No Java runtimes detected.</div>';
    }
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
        } · Java ${server.java || "unknown"} · ${server.players} online</small></div>
                      <button class="server-control-button ${
          server.running ? "stop" : "start"
        }" aria-label="${server.running ? "Stop" : "Start"} ${escapeHtml(server.name)}" title="${server.running ? "Stop" : "Start"} server" onclick="systemServerAction(${Number(server.id)}, '${
          server.running ? "stop" : "start"
        }')"><i class="fa-solid fa-${server.running ? "stop" : "play"}" aria-hidden="true"></i></button>
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
    const serverPage = document.querySelector("#page-content > [data-server-id]");
    const topbar = document.querySelector(".topbar[data-server-id]");
    if (
      serverPage?.dataset.serverId &&
      topbar?.dataset.serverId &&
      serverPage.dataset.serverId !== topbar.dataset.serverId
    ) {
      window.location.reload();
      return;
    }
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
    loadAdvancedProperties();
    updateSMTPSettings();
    loadOffsiteBackupSettings();
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

    const pluginsPage = document.querySelector(".plugins-page");
    if (pluginsPage?.dataset.serverId === serverId) {
      pluginServerRunning = data.running === true;
      showPluginRestartAlert();
    }

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
let pluginServerRunning = false;
let pluginDuplicateGroups = [];
let duplicatePluginFilenames = new Set();
let duplicatePluginDetails = new Map();
let sessionAcknowledgedPluginDuplicates = new Set();
const acknowledgedPluginDuplicatesKey = "stemcraft.acknowledgedPluginDuplicates";

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

async function updatePluginsPage(forceDuplicatePrompt = false) {
  const page = document.querySelector(
    ".plugins-page",
  );

  if (!page) {
    return;
  }

  const serverId = page.dataset.serverId;

  try {
    const response = await fetch(
      `/api/web/servers/${serverId}/plugins`,
    );

    if (!response.ok) {
      throw new Error();
    }

    const data = await response.json();

    const currentPage = document.querySelector(".plugins-page");
    if (!page.isConnected || currentPage?.dataset.serverId !== serverId) {
      return;
    }

    pluginData = data.plugins || [];
    pluginDuplicateGroups = data.duplicates || [];
    duplicatePluginFilenames = new Set(
      pluginDuplicateGroups.flatMap((group) =>
        group.plugins.map((plugin) => plugin.filename)
      ),
    );
    duplicatePluginDetails = new Map();
    for (const group of pluginDuplicateGroups) {
      for (const plugin of group.plugins) {
        duplicatePluginDetails.set(
          plugin.filename,
          group.plugins
            .filter((candidate) => candidate.filename !== plugin.filename)
            .map((candidate) => candidate.filename),
        );
      }
    }

    pluginRestartRequired = data.restart_required === true;
    pluginServerRunning = data.running === true;

    showPluginRestartAlert();

    renderPlugins();
    showPluginDuplicatesModal(forceDuplicatePrompt);
  } catch {
    const list = document.getElementById(
      "plugin-list",
    );

    if (list) {
      list.textContent = "Unable to load plugins.";
    }
  }
}

function selectPluginJar(button) {
  const input = button.form?.elements.plugin;
  if (!input) return;
  input.value = "";
  input.click();
}

async function uploadPluginJar(input) {
  if (!input.files?.length) return;

  const page = document.querySelector(".plugins-page");
  const status = document.getElementById("plugin-install-status");
  const form = input.form;
  const button = form?.querySelector(".plugin-upload-button");
  if (!page || !status || !form) return;

  if (button) button.disabled = true;
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
    pluginRestartRequired = true;
    showPluginRestartAlert();
    await updatePluginsPage(true);
  } catch (error) {
    status.textContent = error.message;
  } finally {
    input.value = "";
    if (button) button.disabled = false;
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
    await updatePluginsPage(true);
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
                    ${duplicatePluginFilenames.has(plugin.filename) ? "duplicate" : ""}
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

                            ${duplicatePluginDetails.has(plugin.filename) ? `
                                <span class="plugin-duplicate-label" title="Another enabled JAR identifies as ${escapeHtml(plugin.name)}">
                                    <i class="fa-solid fa-triangle-exclamation"></i>
                                    Possible duplicate of ${escapeHtml(duplicatePluginDetails.get(plugin.filename).join(", "))}
                                </span>
                            ` : ""}

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

function pluginDuplicateGroupSignature(group) {
  const serverId = document.querySelector(".plugins-page")?.dataset.serverId || "";
  return `${serverId}:${JSON.stringify({
    name: group.name,
    files: group.plugins.map((plugin) => ({
      filename: plugin.filename,
      version: plugin.version || null,
      size: plugin.size ?? null,
      modified_ns: plugin.modified_ns ?? null,
    })).sort((left, right) => left.filename.localeCompare(right.filename)),
  })}`;
}

function acknowledgedPluginDuplicates() {
  const acknowledged = new Set(sessionAcknowledgedPluginDuplicates);
  try {
    const stored = JSON.parse(localStorage.getItem(acknowledgedPluginDuplicatesKey) || "[]");
    if (Array.isArray(stored)) {
      for (const signature of stored) acknowledged.add(signature);
    }
  } catch {
    // Session acknowledgements still prevent repeated prompts.
  }
  return acknowledged;
}

function storeAcknowledgedPluginDuplicates(acknowledged) {
  sessionAcknowledgedPluginDuplicates = new Set(acknowledged);
  try {
    localStorage.setItem(
      acknowledgedPluginDuplicatesKey,
      JSON.stringify(Array.from(acknowledged).slice(-100)),
    );
  } catch {
    // The warning still remains dismissed for this page load when storage is unavailable.
  }
}

function prunePluginDuplicateAcknowledgements() {
  const serverId = document.querySelector(".plugins-page")?.dataset.serverId || "";
  if (!serverId) return;
  const current = new Set(
    pluginDuplicateGroups.map((group) => pluginDuplicateGroupSignature(group)),
  );
  const acknowledged = acknowledgedPluginDuplicates();
  for (const signature of acknowledged) {
    if (signature.startsWith(`${serverId}:`) && !current.has(signature)) {
      acknowledged.delete(signature);
    }
  }
  storeAcknowledgedPluginDuplicates(acknowledged);
}

function showPluginDuplicatesModal() {
  const modal = document.getElementById("plugin-duplicates-modal");
  const container = document.getElementById("plugin-duplicate-groups");
  if (!modal || !container) return;
  prunePluginDuplicateAcknowledgements();
  if (!pluginDuplicateGroups.length) {
    modal.hidden = true;
    return;
  }
  const acknowledged = acknowledgedPluginDuplicates();
  const groupsToShow = pluginDuplicateGroups.filter(
    (group) => !acknowledged.has(pluginDuplicateGroupSignature(group)),
  );
  if (!groupsToShow.length) {
    modal.hidden = true;
    return;
  }
  modal.dataset.groupSignatures = JSON.stringify(
    groupsToShow.map((group) => pluginDuplicateGroupSignature(group)),
  );
  container.replaceChildren();
  for (const group of groupsToShow) {
    const section = document.createElement("div");
    section.className = "plugin-duplicate-group";
    const header = document.createElement("div");
    header.className = "plugin-duplicate-group-header";
    const title = document.createElement("strong");
    title.textContent = group.name;
    const count = document.createElement("span");
    count.textContent = `${group.plugins.length} enabled`;
    header.append(title, count);
    section.appendChild(header);
    for (const plugin of group.plugins) {
      const label = document.createElement("label");
      label.className = "plugin-duplicate-option";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.value = plugin.filename;
      checkbox.checked = true;
      checkbox.setAttribute("aria-label", `Enable ${plugin.filename}`);
      checkbox.addEventListener("change", () => {
        label.classList.toggle("will-disable", !checkbox.checked);
        state.textContent = checkbox.checked ? "Enabled" : "Will be disabled";
        updateDuplicatePluginButton();
      });
      const description = document.createElement("span");
      description.className = "plugin-duplicate-description";
      const filename = document.createElement("strong");
      filename.textContent = plugin.filename;
      description.appendChild(filename);
      if (plugin.version) {
        const version = document.createElement("small");
        version.textContent = `Version ${plugin.version}`;
        description.appendChild(version);
      }
      const state = document.createElement("small");
      state.className = "plugin-duplicate-state";
      state.textContent = "Enabled";
      description.appendChild(state);
      label.append(checkbox, description);
      section.appendChild(label);
    }
    container.appendChild(section);
  }
  updateDuplicatePluginButton();
  modal.hidden = false;
}

function updateDuplicatePluginButton() {
  const button = document.getElementById("disable-selected-duplicates");
  if (button) {
    button.disabled = !document.querySelector(
      '#plugin-duplicate-groups input[type="checkbox"]:not(:checked)',
    );
  }
}

function keepDuplicatePluginsEnabled() {
  const modal = document.getElementById("plugin-duplicates-modal");
  const acknowledged = acknowledgedPluginDuplicates();
  try {
    const signatures = JSON.parse(modal?.dataset.groupSignatures || "[]");
    for (const signature of signatures) acknowledged.add(signature);
    storeAcknowledgedPluginDuplicates(acknowledged);
  } catch {
    if (modal?.dataset.groupSignatures) {
      sessionAcknowledgedPluginDuplicates.add(modal.dataset.groupSignatures);
    }
  }
  if (modal) modal.hidden = true;
}

async function disableSelectedDuplicatePlugins() {
  const page = document.querySelector(".plugins-page");
  const button = document.getElementById("disable-selected-duplicates");
  if (!page || !button) return;
  const selected = Array.from(document.querySelectorAll(
    '#plugin-duplicate-groups input[type="checkbox"]:not(:checked)',
  )).map((checkbox) => checkbox.value);
  if (!selected.length) return;
  button.disabled = true;
  const response = await fetch(
    `/api/web/servers/${page.dataset.serverId}/plugins/duplicates/resolve`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ disable: selected }),
    },
  );
  const data = await response.json();
  if (!response.ok) {
    showToast(data.error || "Unable to disable duplicate plugins", "error");
    button.disabled = false;
    return;
  }
  const modal = document.getElementById("plugin-duplicates-modal");
  if (modal) modal.hidden = true;
  pluginRestartRequired = true;
  showPluginRestartAlert();
  await updatePluginsPage();
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

function escapeJsString(value) {
  return escapeHtml(String(value).replaceAll("\\", "\\\\").replaceAll("'", "\\'"));
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
  const icon = document.getElementById("plugin-change-alert-icon");
  const message = document.getElementById("plugin-change-alert-message");
  const label = document.getElementById("plugin-change-alert-label");

  if (!alert) return;
  alert.hidden = !pluginRestartRequired;
  if (!pluginRestartRequired || !icon || !message || !label) return;

  icon.className = pluginServerRunning
    ? "fa-solid fa-rotate"
    : "fa-solid fa-circle-info";
  message.textContent = pluginServerRunning
    ? "Plugin changes are pending. Restart the server to apply them."
    : "Plugin changes will apply when the server is next started.";
  label.textContent = pluginServerRunning
    ? "Restart required"
    : "Applies on next start";
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
    const startup = data.startup || {};
    const management = data.management || {};

    setValue("property-process-backend", management.process_backend || "subprocess");
    const backendSelect = document.getElementById("property-process-backend");
    if (backendSelect) {
      backendSelect.dataset.systemdAvailable = String(management.systemd_available !== false);
    }
    const systemdOption = backendSelect?.querySelector('option[value="systemd"]');
    if (systemdOption) {
      systemdOption.disabled = management.systemd_available === false;
    }
    const systemdNotice = document.getElementById("property-systemd-unavailable");
    if (systemdNotice) {
      systemdNotice.hidden = management.systemd_available !== false;
    }
    const serviceName = document.getElementById("property-service-name");
    if (serviceName) {
      serviceName.textContent = management.unit_name || management.service_name || "—";
    }
    setChecked("property-systemd-enabled", management.enabled_at_boot);
    const serviceState = document.getElementById("property-service-state");
    if (serviceState) {
      const runtimeState = management.running ? "Running" : "Stopped";
      const bootState = management.enabled_at_boot === true
        ? "enabled at boot"
        : management.enabled_at_boot === false
          ? "disabled at boot"
          : "boot status unavailable";
      serviceState.textContent = `${runtimeState} · ${bootState}`;
    }
    updateProcessManagementFields();

    setValue("property-min-memory", startup.min_memory || "2G");
    setValue("property-max-memory", startup.max_memory || "2G");
    setValue("property-jar-name", startup.jar_name || "paper.jar");
    setValue("property-java-args", startup.java_args || "");
    const javaSelect = document.getElementById("property-java-path");
    if (javaSelect) {
      javaSelect.replaceChildren(...(startup.java_runtimes || []).map((runtime) => {
        const option = document.createElement("option");
        option.value = runtime.major;
        option.textContent = runtime.label || `Java ${runtime.major}`;
        option.selected = runtime.major === startup.java_major;
        return option;
      }));
    }

    const jarList = document.getElementById("server-jar-files");
    if (jarList) {
      jarList.replaceChildren(
        ...(startup.jar_files || []).map((name) => {
          const option = document.createElement("option");
          option.value = name;
          return option;
        }),
      );
    }

    const commandPreview = document.getElementById("startup-command-preview");
    if (commandPreview && Array.isArray(startup.command)) {
      commandPreview.textContent = startup.command.join(" ");
    }

    setValue(
      "property-motd",
      p.motd,
    );

    setValue(
      "property-server-port",
      p.server_port,
    );
    checkServerPortWarning(p.server_port, page.dataset.serverId);

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

async function loadAdvancedProperties() {
  const page = document.querySelector(".advanced-properties-page");
  const container = document.getElementById("advanced-properties-groups");
  if (!page || !container) return;
  try {
    const response = await fetch(
      `/api/web/servers/${page.dataset.serverId}/advanced-properties`,
    );
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Unable to load advanced properties.");
    container.replaceChildren();
    if (!(data.groups || []).length) {
      container.innerHTML = '<div class="empty-message">No supported YAML configuration files have been generated yet. Start the server once, then return here.</div>';
      return;
    }
    (data.groups || []).forEach((group, groupIndex) => {
      const section = document.createElement("details");
      section.className = "advanced-property-group";
      section.open = groupIndex === 0;
      const summary = document.createElement("summary");
      summary.textContent = `${group.name} (${group.files.length})`;
      section.appendChild(summary);
      group.files.forEach((file) => {
        const editor = document.createElement("div");
        editor.className = "advanced-property-editor";
        editor.dataset.path = file.path;
        const heading = document.createElement("div");
        heading.className = "advanced-property-heading";
        const title = document.createElement("div");
        const strong = document.createElement("strong");
        strong.textContent = file.label;
        const path = document.createElement("small");
        path.textContent = file.path;
        title.append(strong, path);
        const status = document.createElement("span");
        status.className = "muted-small advanced-property-status";
        heading.append(title, status);
        const textarea = document.createElement("textarea");
        textarea.className = "advanced-property-content";
        textarea.value = file.content;
        textarea.spellcheck = false;
        const actions = document.createElement("div");
        actions.className = "advanced-property-actions";
        const save = document.createElement("button");
        save.type = "button";
        save.className = "button";
        save.textContent = "Save file";
        save.addEventListener("click", () => saveAdvancedProperty(editor, save));
        actions.appendChild(save);
        editor.append(heading, textarea, actions);
        section.appendChild(editor);
      });
      container.appendChild(section);
    });
  } catch (error) {
    container.innerHTML = `<div class="empty-message">${escapeHtml(error.message)}</div>`;
  }
}

async function saveAdvancedProperty(editor, button) {
  const page = document.querySelector(".properties-page");
  const textarea = editor.querySelector(".advanced-property-content");
  const status = editor.querySelector(".advanced-property-status");
  if (!page || !textarea || !status) return;
  button.disabled = true;
  status.textContent = "Saving...";
  try {
    const response = await fetch(
      `/api/web/servers/${page.dataset.serverId}/advanced-properties`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: editor.dataset.path, content: textarea.value }),
      },
    );
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Unable to save configuration.");
    status.textContent = data.running ? "Saved · restart required" : "Saved";
  } catch (error) {
    status.textContent = error.message;
  } finally {
    button.disabled = false;
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

let portWarningTimer = null;

function checkServerPortWarning(port, excludeServerId = null) {
  clearTimeout(portWarningTimer);
  portWarningTimer = setTimeout(async () => {
    const notice = document.getElementById("server-port-warning");
    if (!notice) return;
    const numericPort = Number(port);
    if (!Number.isInteger(numericPort) || numericPort < 1 || numericPort > 65535) {
      notice.hidden = true;
      return;
    }
    const params = new URLSearchParams({ port: String(numericPort) });
    if (excludeServerId) params.set("exclude_server_id", String(excludeServerId));
    try {
      const response = await fetch(`/api/web/servers/port-warning?${params}`);
      const data = await response.json();
      notice.textContent = data.warning || "";
      notice.hidden = !data.warning;
    } catch {
      notice.hidden = true;
    }
  }, 250);
}

async function saveServerProperties(
  event,
  restartIfRunning = false,
) {
  event?.preventDefault();

  const page = document.querySelector(
    ".properties-page",
  );

  if (!page) {
    return;
  }

  const payload = {
    restart_if_running: restartIfRunning,

    process_backend: valueOf("property-process-backend"),

    enabled_at_boot: checkedOf("property-systemd-enabled"),

    min_memory: normalizedStartupMemory("property-min-memory"),

    max_memory: normalizedStartupMemory("property-max-memory"),

    jar_name: valueOf("property-jar-name"),

    java_args: valueOf("property-java-args"),

    java_major: numberOf("property-java-path"),

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
    if (data.restart_confirmation_required) {
      openPropertiesRestartModal();
      return;
    }
    showFormError(
      document.getElementById("properties-form"),
      data.error || "Save failed.",
      data.field,
    );
    if (status) {
      status.textContent = data.error ||
        "Save failed.";
    }

    return;
  }

  if (status) {
    status.textContent = "Saved";
  }
  if (data.warning) showToast(data.warning, "warning");
  clearFormErrors(document.getElementById("properties-form"));

  const restartAlert = document.getElementById(
    "properties-restart-alert",
  );

  if (restartAlert) {
    const message = document.getElementById("properties-pending-message");
    const label = document.getElementById("properties-pending-label");
    if (data.restarted) {
      restartAlert.hidden = true;
      if (status) status.textContent = "Saved · server restarted";
    } else if (data.running) {
      restartAlert.hidden = false;
      if (message) message.textContent = "Property changes are pending. Restart the server to apply them.";
      if (label) label.textContent = "Restart required";
    } else {
      restartAlert.hidden = true;
    }
  }
}

function openPropertiesRestartModal() {
  const modal = document.getElementById("properties-restart-modal");
  if (modal) modal.hidden = false;
}

function closePropertiesRestartModal() {
  const modal = document.getElementById("properties-restart-modal");
  if (modal) modal.hidden = true;
}

async function confirmPropertiesRestart() {
  const button = document.getElementById("confirm-properties-restart");
  if (button) button.disabled = true;
  closePropertiesRestartModal();
  try {
    await saveServerProperties(null, true);
  } finally {
    if (button) button.disabled = false;
  }
}

function updateProcessManagementFields() {
  const backend = document.getElementById("property-process-backend");
  const service = document.getElementById("property-systemd-service");
  const enabled = document.getElementById("property-systemd-enabled-row");
  const enabledToggle = document.getElementById("property-systemd-enabled");
  const isSystemd = backend?.value === "systemd";
  const systemdAvailable = backend?.dataset.systemdAvailable !== "false";
  if (service) service.hidden = !isSystemd;
  if (enabled) enabled.hidden = !isSystemd || !systemdAvailable;
  if (!isSystemd && enabledToggle) enabledToggle.checked = false;
}

function updateStartupCommandPreview() {
  const preview = document.getElementById("startup-command-preview");
  if (!preview) {
    return;
  }

  const initial = valueOf("property-min-memory") || "2G";
  const maximum = valueOf("property-max-memory") || "2G";
  const jar = valueOf("property-jar-name") || "paper.jar";
  const options = valueOf("property-java-args").trim();
  preview.textContent = [
    `java`,
    `-Xms${initial}`,
    `-Xmx${maximum}`,
    options,
    "-jar",
    jar,
    "--nogui",
  ].filter(Boolean).join(" ");
}

async function updateLatestLog() {
  const viewer = document.querySelector('.server-log-content[data-live="true"]');
  if (!viewer || viewer.dataset.refreshing === "true") return;
  viewer.dataset.refreshing = "true";
  const params = new URLSearchParams();
  if (viewer.dataset.logSize) params.set("size", viewer.dataset.logSize);
  if (viewer.dataset.logModifiedNs) params.set("modified_ns", viewer.dataset.logModifiedNs);
  try {
    const response = await fetch(
      `/api/web/servers/${viewer.dataset.serverId}/logs/latest?${params}`,
    );
    if (!response.ok) return;
    const data = await response.json();
    viewer.dataset.logSize = String(data.size ?? "");
    viewer.dataset.logModifiedNs = String(data.modified_ns ?? "");
    if (!data.changed) return;
    const truncatedNotice = document.getElementById("server-log-truncated-notice");
    if (truncatedNotice) truncatedNotice.hidden = data.truncated !== true;
    const nearBottom = viewer.scrollHeight - viewer.scrollTop - viewer.clientHeight < 48;
    viewer.textContent = data.content || "";
    if (nearBottom) viewer.scrollTop = viewer.scrollHeight;
  } catch (error) {
    console.debug("Unable to refresh latest.log", error);
  } finally {
    viewer.dataset.refreshing = "false";
  }
}

setInterval(updateLatestLog, 3000);

function serverLogPageUrl(serverId, page, selectedLog = "") {
  const params = new URLSearchParams({ page: String(page) });
  if (selectedLog) params.set("file", selectedLog);
  return `/servers/${serverId}/logs?${params}`;
}

async function updateServerLogList() {
  const pageElement = document.querySelector(".server-logs-page");
  const rows = document.getElementById("server-log-rows");
  if (!pageElement || !rows || pageElement.dataset.listRefreshing === "true") return;
  pageElement.dataset.listRefreshing = "true";
  try {
    const response = await fetch(
      `/api/web/servers/${pageElement.dataset.serverId}/logs?page=${pageElement.dataset.logsPage}`,
    );
    if (!response.ok) return;
    const data = await response.json();
    pageElement.dataset.logsPage = String(data.page);
    rows.replaceChildren();
    for (const log of data.logs || []) {
      const link = document.createElement("a");
      link.className = `server-log-row${log.name === pageElement.dataset.selectedLog ? " active" : ""}`;
      link.href = serverLogPageUrl(pageElement.dataset.serverId, data.page, log.name);
      link.setAttribute("hx-get", link.href);
      link.setAttribute("hx-target", "#page-content");
      link.setAttribute("hx-push-url", "true");
      const name = document.createElement("span");
      name.className = "server-log-name";
      const icon = document.createElement("i");
      icon.className = "fa-regular fa-file-lines";
      name.append(icon, document.createTextNode(log.name));
      const modified = document.createElement("span");
      modified.textContent = log.modified_display;
      const size = document.createElement("span");
      size.textContent = log.size_display;
      link.append(name, modified, size);
      rows.appendChild(link);
    }
    if (!(data.logs || []).length) {
      const empty = document.createElement("div");
      empty.className = "empty-message";
      empty.textContent = "No Minecraft log files were found in this server's logs directory.";
      rows.appendChild(empty);
    }
    if (window.htmx) window.htmx.process(rows);

    const count = document.getElementById("server-log-count");
    if (count) count.textContent = `${data.total_logs} files`;
    const pagination = document.getElementById("server-log-pagination");
    if (pagination) pagination.hidden = data.total_pages <= 1;
    const label = document.getElementById("server-log-page-label");
    if (label) label.textContent = `Page ${data.page} of ${data.total_pages}`;
    const previous = pagination?.querySelector('[data-log-page="previous"]');
    const next = pagination?.querySelector('[data-log-page="next"]');
    const selected = pageElement.dataset.selectedLog;
    if (previous) {
      previous.href = serverLogPageUrl(pageElement.dataset.serverId, Math.max(1, data.page - 1), selected);
      previous.setAttribute("hx-get", previous.href);
      previous.setAttribute("aria-disabled", String(data.page <= 1));
    }
    if (next) {
      next.href = serverLogPageUrl(pageElement.dataset.serverId, Math.min(data.total_pages, data.page + 1), selected);
      next.setAttribute("hx-get", next.href);
      next.setAttribute("aria-disabled", String(data.page >= data.total_pages));
    }
  } catch (error) {
    console.debug("Unable to refresh server log list", error);
  } finally {
    pageElement.dataset.listRefreshing = "false";
  }
}

setInterval(updateServerLogList, 5000);

function normalizedStartupMemory(id) {
  const input = document.getElementById(id);
  const value = input?.value.trim() || "";
  const match = value.match(/^([1-9][0-9]*)\s*(K|KB|M|MB|G|GB)$/i);
  if (!match) {
    return value;
  }
  const normalized = `${match[1]}${match[2][0].toUpperCase()}`;
  if (input) {
    input.value = normalized;
  }
  return normalized;
}

function normalizeStartupMemoryInput(input) {
  normalizedStartupMemory(input.id);
  updateStartupCommandPreview();
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
loadAdvancedProperties();

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
        email,
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

function selectedRolePermissions() {
  return Array.from(document.querySelectorAll(".settings-role-permission:checked"))
    .map((checkbox) => checkbox.value);
}

function setRolePermissions(keys) {
  const selected = new Set(keys || []);
  document.querySelectorAll(".settings-role-permission").forEach((checkbox) => {
    checkbox.checked = selected.has(checkbox.value);
  });
}

function clearRoleError() {
  const error = document.getElementById("settings-role-error");
  if (error) {
    error.hidden = true;
    error.textContent = "";
  }
}

function openAddRoleModal() {
  document.getElementById("role-modal-title").textContent = "Add Role";
  document.getElementById("settings-role-id").value = "";
  document.getElementById("settings-role-name").value = "";
  document.getElementById("settings-role-description").value = "";
  document.getElementById("delete-role-button").hidden = true;
  setRolePermissions([]);
  clearRoleError();
  document.getElementById("role-modal").hidden = false;
  document.getElementById("settings-role-name").focus();
}

async function openEditRoleModal(roleId) {
  const response = await fetch(`/api/web/settings/roles/${roleId}`);
  const data = await response.json();
  if (!response.ok) {
    alert(data.error || "Unable to load role");
    return;
  }
  document.getElementById("role-modal-title").textContent = "Edit Role";
  document.getElementById("settings-role-id").value = data.id;
  document.getElementById("settings-role-name").value = data.name;
  document.getElementById("settings-role-description").value = data.description;
  document.getElementById("delete-role-button").hidden = data.system;
  setRolePermissions(data.permissions);
  clearRoleError();
  document.getElementById("role-modal").hidden = false;
}

function closeRoleModal() {
  document.getElementById("role-modal").hidden = true;
}

async function saveSettingsRole() {
  const id = document.getElementById("settings-role-id").value;
  const response = await fetch(
    id ? `/api/web/settings/roles/${id}` : "/api/web/settings/roles",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: document.getElementById("settings-role-name").value.trim(),
        description: document.getElementById("settings-role-description").value.trim(),
        permissions: selectedRolePermissions(),
      }),
    },
  );
  const data = await response.json();
  if (!response.ok) {
    const error = document.getElementById("settings-role-error");
    error.textContent = data.error || "Unable to save role";
    error.hidden = false;
    return;
  }
  window.location.reload();
}

async function deleteSettingsRole() {
  const id = document.getElementById("settings-role-id").value;
  if (!id || !window.confirm("Delete this role?")) return;
  const response = await fetch(`/api/web/settings/roles/${id}`, { method: "DELETE" });
  const data = await response.json();
  if (!response.ok) {
    const error = document.getElementById("settings-role-error");
    error.textContent = data.error || "Unable to delete role";
    error.hidden = false;
    return;
  }
  window.location.reload();
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

  const roleSelect = document.getElementById("settings-user-role");
  const defaultRole = Array.from(roleSelect.options).find(
    (option) => option.dataset.roleName === "User",
  );
  roleSelect.value = defaultRole?.value || roleSelect.options[0]?.value || "";

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
  ).value = String(data.role_id);

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
  const select = document.getElementById("settings-user-role");
  const selected = select?.selectedOptions[0];

  const access = document.getElementById(
    "settings-server-access",
  );

  if (!access) {
    return;
  }

  access.hidden = selected?.dataset.viewAll === "true";
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

    role_id: Number(document
      .getElementById(
        "settings-user-role",
      )
      .value),

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

let offsiteRemoteState = [];

async function loadOffsiteBackupSettings() {
  const status = document.getElementById("offsite-settings-status");
  const list = document.getElementById("offsite-remote-list");
  if (!status) return;
  try {
    const response = await fetch("/api/web/settings/offsite-backups");
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Off-site backups could not be checked.");
    status.textContent = data.available
      ? `${data.remotes.length} destination${data.remotes.length === 1 ? "" : "s"} configured`
      : data.reason === "not_installed"
        ? "rclone is not installed. Install it to enable off-site backups."
        : `Off-site backups are unavailable: ${data.error}`;
    const options = document.getElementById("offsite-test-remote");
    const selectedRemote = options.value;
    options.innerHTML = '<option value="">Choose a destination</option>' + (data.remotes || []).map((remote) => `<option value="${escapeHtml(remote)}">${escapeHtml(remote)}</option>`).join("");
    if ((data.remotes || []).includes(selectedRemote)) options.value = selectedRemote;
    offsiteRemoteState = data.destinations || [];
    list.innerHTML = offsiteRemoteState.length ? offsiteRemoteState.map((remote) => `
      <div class="offsite-remote-row">
        <div><strong>${escapeHtml(remote.name)}</strong><small>${escapeHtml(offsiteProviderName(remote.backend))}${remote.host ? ` · ${escapeHtml(remote.user || "")}@${escapeHtml(remote.host)}` : ""}</small></div>
        <div class="offsite-remote-actions">${["b2", "storj", "sftp"].includes(remote.backend) ? `<button class="button" type="button" onclick="openOffsiteRemoteModal('${escapeJsString(remote.name)}')">Edit</button>` : ""}<button class="button danger" type="button" onclick="deleteOffsiteRemote('${escapeJsString(remote.name)}')">Remove</button></div>
      </div>`).join("") : `<div class="empty-message">${data.reason === "not_installed" ? "Install rclone, then add your first destination here." : "No off-site destinations configured yet."}</div>`;
  } catch (error) {
    status.textContent = "Off-site backups could not be checked. Try refreshing after restarting the panel.";
    if (list) list.innerHTML = '<div class="empty-message">No destination information is available.</div>';
  }
}

function offsiteProviderName(backend) {
  return { b2: "Backblaze B2", storj: "Storj", sftp: "SFTP server" }[backend] || backend;
}

function updateOffsiteRemoteFields() {
  const backend = document.getElementById("offsite-remote-backend")?.value;
  document.querySelectorAll("[data-offsite-provider]").forEach((fields) => {
    const active = fields.dataset.offsiteProvider === backend;
    fields.hidden = !active;
    fields.style.display = active ? "grid" : "none";
    fields.querySelectorAll("input, select").forEach((control) => {
      control.disabled = !active;
    });
  });
}

function openOffsiteRemoteModal(name = "") {
  const remote = offsiteRemoteState.find((item) => item.name === name);
  document.getElementById("offsite-remote-name").value = remote?.name || "";
  document.getElementById("offsite-remote-name").readOnly = Boolean(remote);
  document.getElementById("offsite-remote-backend").value = remote?.backend || "b2";
  document.getElementById("offsite-b2-account").value = remote?.account || "";
  document.getElementById("offsite-b2-secret").value = "";
  document.getElementById("offsite-storj-access").value = remote?.access_key_id || "";
  document.getElementById("offsite-storj-secret").value = "";
  document.getElementById("offsite-storj-endpoint").value = remote?.endpoint || "https://gateway.storjshare.io";
  document.getElementById("offsite-sftp-host").value = remote?.host || "";
  document.getElementById("offsite-sftp-port").value = remote?.port || "22";
  document.getElementById("offsite-sftp-user").value = remote?.user || "";
  document.getElementById("offsite-sftp-secret").value = "";
  document.getElementById("offsite-remote-save-status").textContent = remote ? "Leave the secret blank to keep the saved value." : "";
  updateOffsiteRemoteFields();
  document.getElementById("offsite-remote-modal").hidden = false;
}

function closeOffsiteRemoteModal() {
  document.getElementById("offsite-remote-modal").hidden = true;
}

async function saveOffsiteRemote() {
  const backend = document.getElementById("offsite-remote-backend").value;
  const payload = { name: document.getElementById("offsite-remote-name").value.trim(), backend };
  if (backend === "b2") Object.assign(payload, { account: document.getElementById("offsite-b2-account").value.trim(), secret: document.getElementById("offsite-b2-secret").value });
  if (backend === "storj") Object.assign(payload, { access_key: document.getElementById("offsite-storj-access").value.trim(), secret: document.getElementById("offsite-storj-secret").value, endpoint: document.getElementById("offsite-storj-endpoint").value.trim() });
  if (backend === "sftp") Object.assign(payload, { host: document.getElementById("offsite-sftp-host").value.trim(), port: document.getElementById("offsite-sftp-port").value, user: document.getElementById("offsite-sftp-user").value.trim(), secret: document.getElementById("offsite-sftp-secret").value });
  const status = document.getElementById("offsite-remote-save-status");
  status.textContent = "Saving...";
  const response = await fetch("/api/web/settings/offsite-backups/remotes", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  const data = await response.json();
  if (!response.ok) return status.textContent = data.error || "Unable to save destination.";
  closeOffsiteRemoteModal();
  await loadOffsiteBackupSettings();
}

async function deleteOffsiteRemote(name) {
  if (!confirm(`Remove the ${name} destination? Existing remote files will not be deleted.`)) return;
  const response = await fetch(`/api/web/settings/offsite-backups/remotes/${encodeURIComponent(name)}`, { method: "DELETE" });
  const data = await response.json();
  if (!response.ok) return alert(data.error || "Unable to remove destination.");
  loadOffsiteBackupSettings();
}

function testNamedOffsiteRemote(name) {
  document.getElementById("offsite-test-remote").value = name;
  document.getElementById("offsite-test-path").value = "";
  testOffsiteBackupDestination();
}

function setOffsiteTestStatus(message, error = false) {
  const status = document.getElementById("offsite-test-status");
  if (!status) return;
  status.textContent = message;
  status.hidden = !message;
  status.classList.toggle("error", error);
}

async function testOffsiteBackupDestination() {
  const remote = document.getElementById("offsite-test-remote")?.value;
  const path = document.getElementById("offsite-test-path")?.value.trim() || "";
  if (!remote) {
    setOffsiteTestStatus("Choose a destination before testing the connection.", true);
    document.getElementById("offsite-test-remote")?.focus();
    return;
  }
  setOffsiteTestStatus("Testing connection...");
  try {
    const response = await fetch("/api/web/settings/offsite-backups/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ remote, path }),
    });
    const data = await response.json();
    setOffsiteTestStatus(
      response.ok ? "Connection successful." : (data.error || "Connection failed."),
      !response.ok,
    );
  } catch (error) {
    setOffsiteTestStatus("Connection test could not be completed.", true);
  }
}

loadOffsiteBackupSettings();

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
        "uploading",
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
                            ${Number.isFinite(Number(job.progress)) ? `${Number(job.progress)}%` : "In progress"}
                        </strong>

                    </div>

                    <div class="upload-progress-track">

                        <div
                            class="upload-progress-bar"
                            style="width: ${Number(job.progress || 0)}%"
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

    if (!response.ok) {
      return;
    }

    // Give the process a moment to change state.
    setTimeout(
      async () => {
        await updateServerStatus();
        await updatePluginsPage();
      },
      500,
    );
  } catch (error) {
    console.error(
      "Server action failed:",
      error,
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

  if (days) return `${days}d ${hours}h ${minutes}m`;
  if (hours) return `${hours}h ${minutes}m`;
  if (minutes) return `${minutes}m`;
  return `${totalSeconds}s`;
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
const SYSTEM_OPERATION_KEY = "stemcraftSystemOperation";
let systemOperationActive = false;
let localSystemOperation = false;
let sharedSystemOperationSeen = false;

function setSystemOperationState(title, message, phase = "working") {
  const overlay = document.getElementById("system-operation-overlay");
  if (!overlay) return;
  document.getElementById("system-operation-title").textContent = title;
  document.getElementById("system-operation-message").textContent = message;
  overlay.dataset.phase = phase;
  sessionStorage.setItem(SYSTEM_OPERATION_KEY, JSON.stringify({
    title,
    message,
    phase,
    startedAt: Date.now(),
  }));
}

function beginSystemOperation(title, message, phase = "working", local = true) {
  const overlay = document.getElementById("system-operation-overlay");
  if (!overlay) return;
  systemOperationActive = true;
  localSystemOperation = local;
  overlay.hidden = false;
  overlay.classList.remove("failed");
  document.getElementById("system-operation-spinner").hidden = false;
  document.getElementById("system-operation-failed-icon").hidden = true;
  document.getElementById("system-operation-note").hidden = false;
  document.getElementById("system-operation-close").hidden = true;
  document.body.classList.add("system-operation-active");
  const shell = document.querySelector(".app-shell");
  if (shell) shell.inert = true;
  setSystemOperationState(title, message, phase);
}

function failSystemOperation(message) {
  const overlay = document.getElementById("system-operation-overlay");
  if (!overlay) return;
  systemOperationActive = false;
  localSystemOperation = false;
  sharedSystemOperationSeen = false;
  sessionStorage.removeItem(SYSTEM_OPERATION_KEY);
  overlay.classList.add("failed");
  document.getElementById("system-operation-title").textContent = "Operation failed";
  document.getElementById("system-operation-message").textContent = message;
  document.getElementById("system-operation-spinner").hidden = true;
  document.getElementById("system-operation-failed-icon").hidden = false;
  document.getElementById("system-operation-note").hidden = true;
  document.getElementById("system-operation-close").hidden = false;
  document.getElementById("system-operation-close").focus();
}

function closeSystemOperation() {
  const overlay = document.getElementById("system-operation-overlay");
  if (!overlay?.classList.contains("failed")) return;
  overlay.hidden = true;
  overlay.classList.remove("failed");
  localSystemOperation = false;
  document.body.classList.remove("system-operation-active");
  const shell = document.querySelector(".app-shell");
  if (shell) shell.inert = false;
}

window.addEventListener("beforeunload", (event) => {
  if (!systemOperationActive) return;
  event.preventDefault();
  event.returnValue = "A system operation is still in progress.";
});

function resumeSystemOperation() {
  const stored = sessionStorage.getItem(SYSTEM_OPERATION_KEY);
  if (!stored) return;
  try {
    const operation = JSON.parse(stored);
    beginSystemOperation(operation.title, operation.message, operation.phase, false);
    if (operation.phase === "restarting") {
      waitForConsoleRestart();
    } else {
      failSystemOperation(
        "The page was reloaded before the update completed. Check the installed version and service logs before trying again.",
      );
    }
  } catch {
    sessionStorage.removeItem(SYSTEM_OPERATION_KEY);
  }
}

async function pollSharedSystemOperation() {
  try {
    const response = await nativeFetch("/api/web/settings/system-operation", {
      cache: "no-store",
    });
    if (!response.ok) return;
    const operation = await response.json();
    if (operation.active) {
      sharedSystemOperationSeen = true;
      if (!systemOperationActive) {
        beginSystemOperation(
          operation.title || "System operation in progress",
          operation.message || "The console is temporarily locked.",
          operation.phase || "working",
          false,
        );
      } else if (!localSystemOperation) {
        setSystemOperationState(
          operation.title || "System operation in progress",
          operation.message || "The console is temporarily locked.",
          operation.phase || "working",
        );
      }
      return;
    }
    if (sharedSystemOperationSeen && !localSystemOperation) {
      sharedSystemOperationSeen = false;
      systemOperationActive = false;
      sessionStorage.removeItem(SYSTEM_OPERATION_KEY);
      window.location.reload();
    }
  } catch {
    // Connection failures are expected while the console service restarts.
  }
}

window.setInterval(pollSharedSystemOperation, 1000);
pollSharedSystemOperation();

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
resumeSystemOperation();

async function upgradeConsole() {
  if (
    !consoleUpdateTag ||
    !confirm(
      `Install ${consoleUpdateTag}? A verified backup will be created first.`,
    )
  ) return;
  beginSystemOperation(
    "Updating STEMCraft Console",
    `Downloading and verifying ${consoleUpdateTag}. Do not close this page.`,
    "installing",
  );
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
    setSystemOperationState(
      "Restarting STEMCraft Console",
      "The update is installed. Waiting for the console service to return...",
      "restarting",
    );
    if (data.rollback_id) {
      sessionStorage.setItem("consoleRollbackId", data.rollback_id);
      document.getElementById("console-rollback-button").hidden = false;
    }
    button.hidden = true;
    await waitForConsoleRestart();
  } catch (error) {
    button.disabled = false;
    failSystemOperation(error.message);
    updateConsoleVersionStatus();
  }
}

function delay(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function waitForConsoleRestart() {
  const deadline = Date.now() + 90000;

  await delay(2500);
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`/health?restart=${Date.now()}`, {
        cache: "no-store",
      });
      if (response.ok) {
        systemOperationActive = false;
        sessionStorage.removeItem(SYSTEM_OPERATION_KEY);
        window.location.reload();
        return;
      }
    } catch {
      // The service is expected to be briefly unavailable while systemd restarts it.
    }
    await delay(1000);
  }

  const message = "The console service did not return within 90 seconds. Check the service logs before trying again.";
  failSystemOperation(message);
  updateConsoleVersionStatus();
}

async function restartConsoleService() {
  if (!confirm("Restart STEMCraft Console now?")) return;

  beginSystemOperation(
    "Restarting STEMCraft Console",
    "Requesting a service restart. This page will reconnect automatically...",
    "restarting",
  );

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
    button.disabled = false;
    failSystemOperation(error.message);
    updateConsoleVersionStatus();
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
    const installed = document.getElementById("paper-installed-version");
    if (installed) {
      installed.innerHTML = `${escapeHtml(data.current_version || "Unknown")}${
        data.current_build
          ? ` <small>(build ${escapeHtml(data.current_build)})</small>`
          : ""
      }`;
    }
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
      setPaperUpdateAvailability(
        button,
        data.running
          ? "Stop the server before downloading and replacing the Paper JAR."
          : !(data.builds || []).length
            ? "No Paper builds are available for the selected version."
            : "",
      );
    }
  } catch (error) {
    detail.textContent = error.message;
  }
}

function setPaperUpdateAvailability(button, reason = "") {
  if (!button) return;
  button.dataset.unavailableReason = reason;
  button.setAttribute("aria-disabled", reason ? "true" : "false");
  button.classList.toggle("is-unavailable", Boolean(reason));
  button.title = reason;
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
  setPaperUpdateAvailability(button, "Paper builds are still loading.");
  try {
    const response = await fetch(
      `/api/web/servers/${page.dataset.serverId}/paper?version=${
        encodeURIComponent(version)
      }`,
    );
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Unable to load builds");
    populatePaperBuilds(data.builds || [], data.current_build);
    setPaperUpdateAvailability(
      button,
      data.running
        ? "Stop the server before downloading and replacing the Paper JAR."
        : !data.builds?.length
          ? "No Paper builds are available for the selected version."
          : "",
    );
  } catch (error) {
    select.innerHTML = `<option>${escapeHtml(error.message)}</option>`;
    setPaperUpdateAvailability(button, "Paper builds could not be loaded.");
  }
}

async function installPaperVersion() {
  const page = document.querySelector(".paper-management[data-server-id]");
  const message = document.getElementById("paper-update-message");
  const button = document.getElementById("paper-update-button");
  const unavailableReason = button?.dataset.unavailableReason;
  if (unavailableReason) {
    message.textContent = unavailableReason;
    message.classList.add("error");
    return;
  }
  if (button?.disabled) return;
  if (button) button.disabled = true;
  message.classList.remove("error");
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
    message.classList.add("error");
    if (button) button.disabled = false;
    if (String(error.message).includes("Stop the server")) {
      setPaperUpdateAvailability(button, error.message);
    }
  }
}

loadPaperVersionStatus();

async function rollbackConsoleUpdate() {
  const rollbackId = sessionStorage.getItem("consoleRollbackId");
  if (
    !rollbackId ||
    !confirm("Restore the application files from before this update?")
  ) return;
  beginSystemOperation(
    "Rolling back STEMCraft Console",
    "Restoring the verified application backup. Do not close this page.",
    "installing",
  );
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
    setSystemOperationState(
      "Restarting STEMCraft Console",
      "The previous version is restored. Waiting for the console service to return...",
      "restarting",
    );
    sessionStorage.removeItem("consoleRollbackId");
    button.hidden = true;
    await waitForConsoleRestart();
  } catch (error) {
    button.disabled = false;
    failSystemOperation(error.message);
    updateConsoleVersionStatus();
  }
}

function automationPage() {
  return document.querySelector(
    ".server-overview[data-server-id], .automation-page[data-server-id]",
  );
}

function localScheduleTimezone() {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || automationPage()?.dataset.timezone || "local time";
}

function parseUtcTimestamp(value) {
  const timestamp = String(value || "");
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(timestamp);
  return new Date(hasTimezone ? timestamp : `${timestamp}Z`);
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

let serverScheduleState = [];
let scheduleRunsPage = 1;

async function loadServerSchedules() {
  if (document.hidden) return;
  const page = automationPage();
  const commandList = document.getElementById("command-schedule-list");
  const backupList = document.getElementById("backup-schedule-list");
  if (!page || (!commandList && !backupList)) return;
  try {
    const response = await fetch(
      `/api/web/servers/${page.dataset.serverId}/schedules?runs_page=${scheduleRunsPage}&runs_per_page=10`,
    );
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Unable to load schedules");
    const tasks = (data.tasks || []).filter((task) => task.enabled);
    serverScheduleState = tasks;
    const taskNames = new Map((data.tasks || []).map((task) => [Number(task.id), task.name]));
    const weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
    const remoteOptions = document.getElementById("rclone-remotes");
    if (remoteOptions) {
      remoteOptions.innerHTML = (data.offsite_remotes || []).map((remote) => `<option value="${escapeHtml(remote)}:"></option>`).join("");
    }
    const offsiteAvailability = document.getElementById("offsite-availability");
    if (offsiteAvailability) {
      offsiteAvailability.textContent = data.offsite_error
        ? `Off-site copies unavailable: ${data.offsite_error}`
        : (data.offsite_remotes || []).length
          ? `Available remotes: ${data.offsite_remotes.join(", ")}`
          : "No rclone remotes are configured.";
    }
    const describeWhen = (task) => {
      if (task.frequency === "hourly") return "Every hour";
      const timezone = task.schedule_timezone || localScheduleTimezone();
      const time = `${String(task.run_hour ?? 0).padStart(2, "0")}:00 ${timezone}`;
      if (task.frequency === "daily") return `Every day at ${time}`;
      if (task.frequency === "weekly") return `Every ${weekdays[task.run_weekday] || "week"} at ${time}`;
      if (task.frequency === "monthly") return `The first day of every month at ${time}`;
      if (task.frequency === "custom") return `Custom (${escapeHtml(task.cron_expression || "")}) · ${timezone}`;
      return `Every ${task.interval_minutes} minutes`;
    };
    const canManage = page.dataset.canManage === "true";
    const activeJobs = data.backup_jobs || [];
    const backupRunning = activeJobs.length > 0;
    const renderTasks = (type) => {
      const matches = tasks.filter((task) => task.task_type === type);
      return matches.length ? matches.map((task) => `
            <div class="schedule-row"><div><strong>${
        escapeHtml(task.name)
      }</strong><br>
            <small>${task.task_type === "backup" ? `${describeWhen(task)} · ` : ""}${
        task.task_type === "backup"
          ? `Keeps ${task.retention_count || "all"} backup${Number(task.retention_count) === 1 ? "" : "s"} on this server${
            task.remote_destination
              ? ` and copies each one to ${escapeHtml(task.remote_destination)}, keeping ${task.remote_retention_count || "all"} there`
              : ""
          }`
          : escapeHtml(task.command)
      }${task.task_type === "command" ? ` · ${describeWhen(task)}` : ""}</small></div>
            ${canManage ? `<div class="schedule-row-actions">
              ${type === "backup" ? `<button class="button" onclick="runServerScheduleNow(${Number(task.id)}, this)" ${backupRunning ? "disabled" : ""}>${backupRunning ? "Backup running" : "Run now"}</button>` : ""}
              <button class="button" onclick="editServerSchedule(${Number(task.id)})">Edit</button>
              <button class="button" onclick="deleteServerSchedule(${Number(task.id)})">Delete</button>
            </div>` : ""}</div>`).join("")
        : `<div class="empty-message">No ${type} jobs yet.</div>`;
    };
    if (commandList) commandList.innerHTML = renderTasks("command");
    if (backupList) backupList.innerHTML = renderTasks("backup");
    const progress = document.getElementById("scheduled-backup-progress");
    if (progress) progress.innerHTML = activeJobs.map((job) => {
      const uploading = job.status === "uploading";
      const percent = Number(job.progress || 0);
      return `<div class="scheduled-backup-job"><div class="backup-job-header"><div><strong>${uploading ? "Copying backup off-site" : "Backup in progress"}</strong><small>${escapeHtml(job.message || job.status)}</small></div><strong>${Number.isFinite(percent) ? `${percent}%` : "In progress"}</strong></div><div class="upload-progress-track"><div class="upload-progress-bar" style="width: ${Number.isFinite(percent) ? percent : 0}%"></div></div></div>`;
    }).join("");
    const runs = document.getElementById("schedule-runs");
    const recentRuns = [...(data.runs || [])].sort(
      (left, right) => parseUtcTimestamp(right.started_at) - parseUtcTimestamp(left.started_at),
    );
    const activityTitle = (run) => {
      const name = taskNames.get(Number(run.task_id)) || run.task_type;
      if (run.task_type === "command" && run.status === "complete") {
        return `Sent command “${name}”`;
      }
      const actions = {
        complete: "Completed",
        failed: "Could not complete",
        running: "Started",
      };
      const action = actions[run.status] || `${run.status.charAt(0).toUpperCase()}${run.status.slice(1)}`;
      return `${action} ${run.task_type} “${name}”`;
    };
    runs.innerHTML = recentRuns.length ? recentRuns.map((run) => {
      const startedAt = parseUtcTimestamp(run.started_at);
      const activityTimezone = localScheduleTimezone();
      return `<div class="schedule-run">
        <time datetime="${escapeHtml(run.started_at)}">
          <strong>${escapeHtml(startedAt.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", timeZone: activityTimezone }))}</strong>
          <span>${escapeHtml(startedAt.toLocaleDateString([], { day: "numeric", month: "short", year: "numeric", timeZone: activityTimezone }))}</span>
        </time>
        <div class="schedule-run-detail">
          <strong>${escapeHtml(activityTitle(run))}</strong>
          ${run.detail ? `<small>${escapeHtml(run.detail)}</small>` : ""}
        </div>
      </div>`;
    }).join("") : '<div class="empty-message">No recent activity yet.</div>';
    const pagination = data.runs_pagination || { page: 1, pages: 1, total: recentRuns.length };
    scheduleRunsPage = Number(pagination.page || 1);
    const paginationElement = document.getElementById("schedule-runs-pagination");
    if (paginationElement) {
      paginationElement.hidden = Number(pagination.pages || 1) <= 1;
      paginationElement.querySelector("button:first-child").disabled = scheduleRunsPage <= 1;
      paginationElement.querySelector("button:last-child").disabled = scheduleRunsPage >= Number(pagination.pages || 1);
      document.getElementById("schedule-runs-page-label").textContent = `Page ${scheduleRunsPage} of ${Number(pagination.pages || 1)} · ${Number(pagination.total || 0)} entries`;
    }
  } catch (error) {
    if (commandList) commandList.textContent = error.message;
    if (backupList) backupList.textContent = error.message;
  }
}

function changeScheduleRunsPage(direction) {
  scheduleRunsPage = Math.max(1, scheduleRunsPage + Number(direction));
  loadServerSchedules();
}

function friendlyScheduleSummary(frequency, runHour = 0, runWeekday = 6, cronExpression = "", timezone = localScheduleTimezone()) {
  const time = `${String(runHour ?? 0).padStart(2, "0")}:00`;
  const weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
  if (frequency === "hourly") return `At the start of every hour · ${timezone}`;
  if (frequency === "daily") return `Every day at ${time} · ${timezone}`;
  if (frequency === "weekly") return `Every ${weekdays[runWeekday] || "Sunday"} at ${time} · ${timezone}`;
  if (frequency === "monthly") return `On the first day of every month at ${time} · ${timezone}`;
  if (frequency === "custom") return `Custom ${cronExpression || "schedule"} · ${timezone}`;
  return `Scheduled time · ${timezone}`;
}

function updateScheduleWhen(select) {
  const fields = select.closest(".schedule-when-fields");
  if (!fields) return;
  fields.querySelector("[name=run_hour]").value = "0";
  fields.querySelector("[name=run_weekday]").value = "6";
  const summary = fields.querySelector(".selected-schedule-summary");
  if (select.value === "custom") {
    openCustomSchedule(select);
  } else {
    fields.querySelector("[name=cron_expression]").value = "";
    summary.textContent = friendlyScheduleSummary(select.value, 0, 6);
  }
}

let customScheduleSelect = null;

function customCronValue(id) {
  return document.getElementById(id).value.trim();
}

function customWeekdayValue() {
  const checked = [...document.querySelectorAll("#custom-cron-weekday input:checked")].map((item) => item.value);
  return checked.length === 7 ? "*" : checked.join(",");
}

function updateCustomSchedulePreview() {
  const expression = [customCronValue("custom-cron-minute"), customCronValue("custom-cron-hour"), customCronValue("custom-cron-monthday"), customCronValue("custom-cron-month"), customWeekdayValue()].join(" ");
  document.getElementById("custom-cron-preview").textContent = expression;
  document.getElementById("custom-cron-description").textContent = `Custom schedule in ${localScheduleTimezone()}`;
  return expression;
}

function openCustomSchedule(select) {
  customScheduleSelect = select;
  const saved = select.closest(".schedule-when-fields").querySelector("[name=cron_expression]").value;
  if (saved) {
    const [minute, hour, monthday, month, weekday] = saved.split(" ");
    document.getElementById("custom-cron-minute").value = minute;
    document.getElementById("custom-cron-hour").value = hour;
    document.getElementById("custom-cron-monthday").value = monthday;
    document.getElementById("custom-cron-month").value = month;
    const selected = weekday === "*" ? null : new Set(weekday.split(","));
    document.querySelectorAll("#custom-cron-weekday input").forEach((item) => item.checked = !selected || selected.has(item.value));
  }
  updateCustomSchedulePreview();
  document.getElementById("custom-schedule-modal").hidden = false;
}

function closeCustomSchedule(keepCustom) {
  document.getElementById("custom-schedule-modal").hidden = true;
  if (!keepCustom && customScheduleSelect) {
    const hidden = customScheduleSelect.closest(".schedule-when-fields").querySelector("[name=cron_expression]");
    if (!hidden.value) {
      const form = customScheduleSelect.closest("form");
      customScheduleSelect.value = form?.elements.task_type.value === "backup" ? "daily" : "hourly";
      updateScheduleWhen(customScheduleSelect);
    }
  }
  customScheduleSelect = null;
}

function saveCustomSchedule() {
  if (!customScheduleSelect) return;
  const expression = updateCustomSchedulePreview();
  if (expression.split(" ").some((part) => !part)) return alert("Choose at least one day and complete every field.");
  const fields = customScheduleSelect.closest(".schedule-when-fields");
  fields.querySelector("[name=cron_expression]").value = expression;
  fields.querySelector(".selected-schedule-summary").innerHTML = `Custom <code>${escapeHtml(expression)}</code> · ${escapeHtml(localScheduleTimezone())}`;
  closeCustomSchedule(true);
}

document.querySelectorAll("#custom-schedule-modal input").forEach((input) => input.addEventListener("input", updateCustomSchedulePreview));

async function createServerSchedule(event) {
  event.preventDefault();
  const page = automationPage();
  const form = event.currentTarget;
  const payload = Object.fromEntries(new FormData(form));
  const scheduleId = payload.schedule_id;
  delete payload.schedule_id;
  const response = await fetch(
    `/api/web/servers/${page.dataset.serverId}/schedules${scheduleId ? `/${scheduleId}` : ""}`,
    {
      method: scheduleId ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
  const data = await response.json();
  if (!response.ok) return alert(data.error || "Unable to add schedule");
  closeServerScheduleModal();
  await loadServerSchedules();
}

function openServerScheduleModal(taskType) {
  const modal = document.getElementById(`${taskType}-schedule-modal`);
  const form = modal?.querySelector(".friendly-schedule-form");
  if (!modal || !form) return;
  resetServerScheduleForm(form);
  modal.querySelector("h2").textContent = `Add ${taskType}`;
  modal.hidden = false;
  form.elements.name.focus();
}

function closeServerScheduleModal(event) {
  if (event && event.target !== event.currentTarget) return;
  document.querySelectorAll("#command-schedule-modal, #backup-schedule-modal").forEach((modal) => {
    modal.hidden = true;
    const form = modal.querySelector(".friendly-schedule-form");
    if (form) resetServerScheduleForm(form);
  });
}

function editServerSchedule(taskId) {
  const task = serverScheduleState.find((item) => Number(item.id) === Number(taskId));
  if (!task) return;
  const form = [...document.querySelectorAll(".friendly-schedule-form")].find((item) => item.elements.task_type.value === task.task_type);
  if (!form) return;
  form.elements.schedule_id.value = task.id;
  form.elements.name.value = task.name || "";
  if (form.elements.command) form.elements.command.value = task.command || "";
  form.elements.frequency.value = task.frequency || "hourly";
  form.elements.run_hour.value = task.run_hour ?? 0;
  form.elements.run_weekday.value = task.run_weekday ?? 6;
  form.elements.cron_expression.value = task.cron_expression || "";
  form.elements.schedule_timezone.value = localScheduleTimezone();
  if (form.elements.retention_count) form.elements.retention_count.value = task.retention_count || 7;
  if (form.elements.remote_destination) form.elements.remote_destination.value = task.remote_destination || "";
  if (form.elements.remote_retention_count) form.elements.remote_retention_count.value = task.remote_retention_count || 30;
  const summary = form.querySelector(".selected-schedule-summary");
  if (summary) summary.textContent = friendlyScheduleSummary(
    task.frequency || "hourly",
    task.run_hour ?? 0,
    task.run_weekday ?? 6,
    task.cron_expression || "",
    localScheduleTimezone(),
  );
  form.querySelector(".schedule-submit-button").textContent = `Save ${task.task_type}`;
  const modal = form.closest(".modal-backdrop");
  modal.querySelector("h2").textContent = `Edit ${task.task_type}`;
  modal.hidden = false;
  form.elements.name.focus();
}

function resetServerScheduleForm(form) {
  form.reset();
  form.elements.schedule_id.value = "";
  form.elements.schedule_timezone.value = localScheduleTimezone();
  form.elements.frequency.value = form.elements.task_type.value === "backup" ? "daily" : "hourly";
  const submit = form.querySelector(".schedule-submit-button");
  submit.textContent = submit.dataset.createLabel;
  updateScheduleWhen(form.elements.frequency);
}

function cancelServerScheduleEdit(form) {
  resetServerScheduleForm(form);
  closeServerScheduleModal();
}

async function runServerScheduleNow(taskId, button) {
  const page = automationPage();
  button.disabled = true;
  button.textContent = "Starting…";
  const response = await fetch(`/api/web/servers/${page.dataset.serverId}/schedules/${taskId}/run`, { method: "POST" });
  const data = await response.json();
  if (!response.ok) {
    button.disabled = false;
    button.textContent = "Run now";
    return alert(data.error || "Unable to start backup");
  }
  const progress = document.getElementById("scheduled-backup-progress");
  if (progress) progress.innerHTML = '<div class="scheduled-backup-job"><strong>Starting backup…</strong></div>';
  window.setTimeout(loadServerSchedules, 300);
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

setInterval(loadServerSchedules, 2500);
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) loadServerSchedules();
});
