const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
let pdfPages = [];
let currentPage = 0;
let drawing = false;
let undoStack = [], redoStack = [];

function loadPage(index) {
  if (!pdfPages[index]) return;
  const img = new Image();
  img.src = pdfPages[index];
  img.onload = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
  };
}

canvas.addEventListener("mousedown", () => {
  drawing = true;
  undoStack.push(ctx.getImageData(0, 0, canvas.width, canvas.height));
  ctx.globalCompositeOperation = "destination-out"; // erase
  ctx.lineWidth = 20;
  ctx.lineCap = "round";
});

canvas.addEventListener("mouseup", () => {
  drawing = false;
  ctx.globalCompositeOperation = "source-over";
});

canvas.addEventListener("mousemove", (e) => {
  if (!drawing) return;
  const rect = canvas.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  ctx.lineTo(x, y);
  ctx.stroke();
});

document.getElementById("undo").onclick = () => {
  if (undoStack.length > 0) {
    redoStack.push(ctx.getImageData(0, 0, canvas.width, canvas.height));
    ctx.putImageData(undoStack.pop(), 0, 0);
  }
};

document.getElementById("redo").onclick = () => {
  if (redoStack.length > 0) {
    undoStack.push(ctx.getImageData(0, 0, canvas.width, canvas.height));
    ctx.putImageData(redoStack.pop(), 0, 0);
  }
};

document.getElementById("prevPage").onclick = () => {
  if (currentPage > 0) currentPage--;
  loadPage(currentPage);
};

document.getElementById("nextPage").onclick = () => {
  if (currentPage < pdfPages.length - 1) currentPage++;
  loadPage(currentPage);
};

document.getElementById("pdfInput").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch("/upload", { method: "POST", body: formData });
  const data = await res.json();
  const total = data.pages;
  pdfPages = [];
  for (let i = 0; i < total; i++) pdfPages.push(`/edited/page_${i}.png`);
  loadPage(0);
});

document.getElementById("save").onclick = async () => {
  const dataURL = canvas.toDataURL("image/png");
  const res = await fetch("/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pages: [dataURL] }),
  });
  const data = await res.json();
  window.location.href = data.path;
};
