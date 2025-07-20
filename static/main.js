const pdfInput = document.getElementById("pdfInput");
const pdfPreview = document.getElementById("pdfPreview");
const loader = document.getElementById("loader");
const uploadForm = document.getElementById("uploadForm");
const dropZone = document.getElementById("dropZone");
const submitButton = uploadForm.querySelector("button[type='submit']");
let downloadButton;

// Add download button dynamically after cleaning
function createDownloadButton(url) {
  console.log("Creating download button for:", url); // Debug

  if (downloadButton) downloadButton.remove();

  downloadButton = document.createElement("a");
  downloadButton.href = url;
  downloadButton.download = "cleaned.pdf";
  downloadButton.textContent = "Download Cleaned PDF";
  downloadButton.className =
    "mt-4 px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 block text-center";

  // Hide button after click (after download starts)
  downloadButton.addEventListener("click", () => {
    setTimeout(() => {
      downloadButton.remove();
    }, 1500);
  });

  document.body.appendChild(downloadButton);
}

pdfInput.addEventListener("change", handleFileSelect);

// Allow clicking on drop zone to open file picker
dropZone.addEventListener("click", () => pdfInput.click());

// Handle drag & drop events
dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("dragover");
});
dropZone.addEventListener("dragleave", () =>
  dropZone.classList.remove("dragover")
);
dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("dragover");
  if (e.dataTransfer.files.length > 0) {
    pdfInput.files = e.dataTransfer.files;
    handleFileSelect();
  }
});

function handleFileSelect() {
  const file = pdfInput.files[0];
  if (!file) return;

  // Show file name in drop zone
  dropZone.querySelector("p").textContent = `Selected: ${file.name}`;

  const fileReader = new FileReader();
  fileReader.onload = function () {
    const typedarray = new Uint8Array(this.result);
    renderPDFtoCanvas(typedarray);
  };
  fileReader.readAsArrayBuffer(file);
}

function renderPDFtoCanvas(pdfData) {
  pdfjsLib.getDocument(pdfData).promise.then(function (pdf) {
    pdf.getPage(1).then(function (page) {
      const viewport = page.getViewport({ scale: 1 });
      const canvas = pdfPreview;
      const context = canvas.getContext("2d");
      canvas.height = viewport.height;
      canvas.width = viewport.width;
      page.render({ canvasContext: context, viewport: viewport });
    });
  });
}

uploadForm.addEventListener("submit", function (e) {
  e.preventDefault();
  e.stopImmediatePropagation(); // stops any default form POST

  if (!pdfInput.files.length) {
    alert("Please upload a PDF first.");
    return;
  }

  submitButton.disabled = true;
  submitButton.classList.add("opacity-50", "cursor-not-allowed");
  loader.style.display = "block";

  const formData = new FormData(uploadForm);
  fetch("/", { method: "POST", body: formData })
    .then(async (response) => {
      const contentType = response.headers.get("content-type");
      const text = await response.text();
      console.log("Server raw response:", text);

      if (!contentType || !contentType.includes("application/json")) {
        throw new Error("Server did not return JSON. Got: " + contentType);
      }

      const data = JSON.parse(text);
      return data;
    })
    .then(async (data) => {
      console.log("Parsed server response:", data);

      submitButton.disabled = false;
      submitButton.classList.remove("opacity-50", "cursor-not-allowed");
      loader.style.display = "none";

      const url = data.download_url;

      const res = await fetch(url);
      const buffer = await res.arrayBuffer();
      const typedarray = new Uint8Array(buffer);

      renderPDFtoCanvas(typedarray);
      createDownloadButton(url);

      pdfInput.value = "";
      dropZone.querySelector("p").textContent =
        "Drag & Drop PDF's or Click to Upload";
    });
  // .catch((err) => {
  //   alert("Error processing PDF. Check console.");
  //   console.error("Processing error:", err);
  //   submitButton.disabled = false;
  //   submitButton.classList.remove("opacity-50", "cursor-not-allowed");
  //   loader.style.display = "none";
  // });
});
