const fileInput = document.getElementById("pdfFiles");
const fileList = document.getElementById("fileList");
const fileCount = document.getElementById("fileCount");
const emptyState = document.getElementById("emptyState");
const combineButton = document.getElementById("combineDownloadBtn");
const clearButton = document.getElementById("clearFilesBtn");
const dropZone = document.getElementById("dropZone");
const statusText = document.getElementById("status");

const MAX_FILE_SIZE = Number(dropZone.dataset.maxFileSize) || 25 * 1024 * 1024;
let files = [];
let isBusy = false;
let draggedId = null;
let statusTimer;

function setStatus(message, type = "info", timeout = 0) {
  clearTimeout(statusTimer);
  statusText.textContent = message;
  statusText.className = `status ${type}`;
  if (timeout) {
    statusTimer = setTimeout(() => {
      statusText.textContent = "";
      statusText.className = "status";
    }, timeout);
  }
}

async function getError(response, fallback) {
  try {
    const body = await response.json();
    return body.error || fallback;
  } catch (_error) {
    return fallback;
  }
}

function updateControls() {
  fileCount.textContent = files.length;
  emptyState.hidden = files.length > 0;
  combineButton.disabled = isBusy || files.length < 2;
  clearButton.disabled = isBusy || files.length === 0;
  dropZone.classList.toggle("disabled", isBusy);
}

function renderFiles() {
  fileList.replaceChildren();
  files.forEach((file, index) => {
    const row = document.createElement("li");
    row.className = "file-row";
    row.draggable = !isBusy;
    row.dataset.fileId = file.id;
    row.innerHTML = `
      <span class="drag-handle" aria-hidden="true"><span></span><span></span><span></span></span>
      <span class="file-number">${index + 1}</span>
      <span class="pdf-icon" aria-hidden="true">PDF</span>
      <span class="file-details"><strong></strong><small></small></span>
      <span class="file-row-actions">
        <button class="move-file move-up" type="button" aria-label="Move file up" title="Move up">↑</button>
        <button class="move-file move-down" type="button" aria-label="Move file down" title="Move down">↓</button>
        <button class="remove-file" type="button" aria-label="Remove file" title="Remove file">×</button>
      </span>
    `;
    const nameElement = row.querySelector("strong");
    nameElement.textContent = file.name;
    nameElement.title = file.name;
    row.querySelector("small").textContent = formatFileSize(file.size);
    row.querySelector(".move-up").disabled = index === 0 || isBusy;
    row.querySelector(".move-down").disabled = index === files.length - 1 || isBusy;
    row.querySelector(".move-up").addEventListener("click", () => moveFile(file.id, -1));
    row.querySelector(".move-down").addEventListener("click", () => moveFile(file.id, 1));
    row.querySelector(".remove-file").setAttribute("aria-label", `Remove ${file.name}`);
    row.querySelector(".remove-file").addEventListener("click", () => removeFile(file.id));
    row.addEventListener("dragstart", (event) => {
      draggedId = file.id;
      event.dataTransfer.effectAllowed = "move";
      row.classList.add("dragging");
    });
    row.addEventListener("dragend", () => {
      draggedId = null;
      row.classList.remove("dragging");
    });
    row.addEventListener("dragover", (event) => {
      event.preventDefault();
      row.classList.add("drag-over");
    });
    row.addEventListener("dragleave", () => row.classList.remove("drag-over"));
    row.addEventListener("drop", (event) => {
      event.preventDefault();
      row.classList.remove("drag-over");
      reorderFiles(draggedId, file.id);
    });
    fileList.appendChild(row);
  });
  updateControls();
}

function moveFile(fileId, offset) {
  const currentIndex = files.findIndex((file) => file.id === fileId);
  const targetIndex = currentIndex + offset;
  if (currentIndex < 0 || targetIndex < 0 || targetIndex >= files.length) return;
  const [moved] = files.splice(currentIndex, 1);
  files.splice(targetIndex, 0, moved);
  renderFiles();
  setStatus("Merge order updated.", "success", 2500);
}

function reorderFiles(fromId, toId) {
  if (!fromId || fromId === toId) return;
  const fromIndex = files.findIndex((file) => file.id === fromId);
  const toIndex = files.findIndex((file) => file.id === toId);
  if (fromIndex < 0 || toIndex < 0) return;
  const [moved] = files.splice(fromIndex, 1);
  files.splice(toIndex, 0, moved);
  renderFiles();
  setStatus("Merge order updated.", "success", 2500);
}

function formatFileSize(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const unitIndex = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** unitIndex).toFixed(unitIndex ? 1 : 0)} ${units[unitIndex]}`;
}

async function uploadFiles(selectedFiles) {
  const candidates = Array.from(selectedFiles);
  const pdfFiles = candidates.filter((file) => file.name.toLowerCase().endsWith(".pdf"));
  const oversized = pdfFiles.filter((file) => file.size > MAX_FILE_SIZE);
  const duplicateKey = (file) => `${file.name}:${file.size}`;
  const existingKeys = new Set(files.map((file) => `${file.name}:${file.size}`));
  const uniqueFiles = pdfFiles.filter((file) => !existingKeys.has(duplicateKey(file)) && file.size <= MAX_FILE_SIZE);

  if (candidates.length !== pdfFiles.length) setStatus("Non-PDF files were skipped.", "warning");
  if (oversized.length) setStatus(`${oversized.length} file(s) exceed the 25 MB limit.`, "warning");
  if (!uniqueFiles.length) {
    if (!candidates.length) setStatus("Choose at least one PDF file.", "warning");
    else if (!oversized.length) setStatus("Those files are already in your workspace.", "warning");
    return;
  }

  const formData = new FormData();
  uniqueFiles.forEach((file) => formData.append("pdfs", file));
  isBusy = true;
  updateControls();
  setStatus("Checking and uploading your PDFs…", "info");

  try {
    const response = await fetch("/upload", { method: "POST", body: formData });
    const body = await response.json();
    if (!response.ok) throw new Error(body.error || "Upload failed.");
    files = [...files, ...(body.files || [])];
    renderFiles();
    const rejectedCount = (body.rejected || []).length;
    setStatus(rejectedCount ? `${body.files.length} uploaded; ${rejectedCount} skipped.` : `${body.files.length} PDF(s) ready to merge.`, rejectedCount ? "warning" : "success", 5000);
  } catch (error) {
    setStatus(error.message || "Upload failed. Please try again.", "error");
  } finally {
    isBusy = false;
    updateControls();
  }
}

async function removeFile(fileId) {
  if (isBusy) return;
  isBusy = true;
  updateControls();
  try {
    const response = await fetch("/remove-file", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ file_id: fileId }) });
    if (!response.ok) throw new Error(await getError(response, "That file could not be removed."));
    files = files.filter((file) => file.id !== fileId);
    renderFiles();
    setStatus("File removed from the workspace.", "success", 2500);
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    isBusy = false;
    renderFiles();
  }
}

async function combineAndDownload() {
  if (files.length < 2 || isBusy) {
    setStatus("Add at least two PDFs to combine.", "warning");
    return;
  }
  isBusy = true;
  updateControls();
  setStatus("Combining your PDFs…", "info");
  try {
    const response = await fetch("/combine-and-download", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ file_ids: files.map((file) => file.id) }) });
    if (!response.ok) throw new Error(await getError(response, "The PDFs could not be combined."));
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "combined.pdf";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setStatus("Your combined PDF is ready to use.", "success", 6000);
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    isBusy = false;
    updateControls();
  }
}

async function clearWorkspace() {
  if (!files.length || isBusy || !window.confirm("Remove all PDFs from this workspace?")) return;
  isBusy = true;
  updateControls();
  setStatus("Clearing workspace…", "info");
  try {
    const response = await fetch("/clear-files", { method: "POST" });
    if (!response.ok) throw new Error(await getError(response, "The workspace could not be cleared."));
    files = [];
    renderFiles();
    setStatus("Workspace cleared.", "success", 3000);
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    isBusy = false;
    updateControls();
  }
}

async function loadWorkspace() {
  try {
    const response = await fetch("/files");
    if (!response.ok) throw new Error("Could not restore workspace.");
    const body = await response.json();
    files = body.files || [];
    renderFiles();
  } catch (error) {
    setStatus(error.message, "error");
  }
}

fileInput.addEventListener("change", (event) => {
  uploadFiles(event.target.files);
  fileInput.value = "";
});
combineButton.addEventListener("click", combineAndDownload);
clearButton.addEventListener("click", clearWorkspace);
dropZone.addEventListener("click", (event) => {
  if (event.target !== fileInput && event.target.tagName !== "LABEL" && !isBusy) fileInput.click();
});
dropZone.addEventListener("keydown", (event) => {
  if ((event.key === "Enter" || event.key === " ") && !isBusy) {
    event.preventDefault();
    fileInput.click();
  }
});
dropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  if (!isBusy) dropZone.classList.add("dragover");
});
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropZone.classList.remove("dragover");
  if (!isBusy) uploadFiles(event.dataTransfer.files);
});

renderFiles();
loadWorkspace();