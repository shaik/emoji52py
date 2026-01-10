/* global Cropper */
const fileInput = document.getElementById('fileInput');
const cropImage = document.getElementById('cropImage');
const cropPlaceholder = document.getElementById('cropPlaceholder');
const previewImage = document.getElementById('previewImage');
const previewPlaceholder = document.getElementById('previewPlaceholder');
const convertBtn = document.getElementById('convertBtn');
const statusEl = document.getElementById('status');
const gridInfo = document.getElementById('gridInfo');
const hashInfo = document.getElementById('hashInfo');
const warningsEl = document.getElementById('warnings');

const maxDimEl = document.getElementById('maxDim');
const gridWEl = document.getElementById('gridW');
const gridHEl = document.getElementById('gridH');
const lockAspectEl = document.getElementById('lockAspect');
const deterministicEl = document.getElementById('deterministic');
const ditheringEl = document.getElementById('dithering');
const bgModeEl = document.getElementById('bgMode');
const bgColorEl = document.getElementById('bgColor');
const weightColorEl = document.getElementById('weightColor');
const weightEdgeEl = document.getElementById('weightEdge');
const weightAlphaEl = document.getElementById('weightAlpha');

const exportTextBtn = document.getElementById('exportText');
const exportTextSpacedBtn = document.getElementById('exportTextSpaced');
const exportPngBtn = document.getElementById('exportPng');
const exportJpgBtn = document.getElementById('exportJpg');

let cropper = null;
let lastHash = null;
let imageReady = false;
let lastImageSize = { width: 0, height: 0 };

function setStatus(message) {
  statusEl.textContent = message;
}

function setWarnings(warnings) {
  warningsEl.innerHTML = '';
  if (!warnings || warnings.length === 0) {
    return;
  }
  warningsEl.innerHTML = warnings.map((warning) => `<div>• ${warning}</div>`).join('');
}

function updatePreview(base64) {
  if (base64) {
    previewImage.src = `data:image/png;base64,${base64}`;
    previewImage.style.display = 'block';
    previewPlaceholder.style.display = 'none';
  } else {
    previewImage.src = '';
    previewImage.style.display = 'none';
    previewPlaceholder.style.display = 'flex';
  }
}

function setExportState(enabled) {
  exportTextBtn.disabled = !enabled;
  exportTextSpacedBtn.disabled = !enabled;
  exportPngBtn.disabled = !enabled;
  exportJpgBtn.disabled = !enabled;
}

fileInput.addEventListener('change', () => {
  const file = fileInput.files[0];
  if (!file) {
    return;
  }
  imageReady = false;
  const url = URL.createObjectURL(file);
  cropImage.src = url;
  cropImage.onload = () => {
    cropPlaceholder.style.display = 'none';
    imageReady = true;
    lastImageSize = {
      width: cropImage.naturalWidth || 0,
      height: cropImage.naturalHeight || 0,
    };
    if (cropper) {
      cropper.destroy();
    }
    if (typeof Cropper === 'undefined') {
      cropper = null;
      console.warn('Cropper.js is not available; falling back to full-image crop.');
      setStatus('Cropper unavailable; using full-image crop.');
      return;
    }
    try {
      cropper = new Cropper(cropImage, {
        viewMode: 1,
        autoCropArea: 0.9,
        background: false,
        responsive: true,
      });
    } catch (err) {
      cropper = null;
      console.error('Failed to initialize cropper.', err);
      setStatus('Cropper failed to initialize; using full-image crop.');
    }
  };
});

convertBtn.addEventListener('click', async () => {
  const file = fileInput.files[0];
  if (!file) {
    setStatus('Upload an image first.');
    return;
  }
  if (!imageReady) {
    setStatus('Image still loading. Try again in a moment.');
    return;
  }

  setStatus('Converting…');
  setWarnings([]);
  setExportState(false);

  let cropPayload;
  if (cropper) {
    const cropData = cropper.getData(true);
    cropPayload = {
      x: Math.round(cropData.x),
      y: Math.round(cropData.y),
      w: Math.round(cropData.width),
      h: Math.round(cropData.height),
    };
  } else {
    console.info('Using full-image crop because cropper is unavailable.');
    cropPayload = {
      x: 0,
      y: 0,
      w: lastImageSize.width || cropImage.naturalWidth || 0,
      h: lastImageSize.height || cropImage.naturalHeight || 0,
    };
  }

  const settingsPayload = {
    max_dim: Number(maxDimEl.value) || 120,
    grid_w: gridWEl.value ? Number(gridWEl.value) : null,
    grid_h: gridHEl.value ? Number(gridHEl.value) : null,
    lock_aspect: lockAspectEl.checked,
    dithering: ditheringEl.checked,
    deterministic: deterministicEl.checked,
    bg_mode: bgModeEl.value,
    bg_color: bgColorEl.value,
    weights: {
      color: Number(weightColorEl.value) || 1.0,
      edge: Number(weightEdgeEl.value) || 0.2,
      alpha: Number(weightAlphaEl.value) || 0.1,
    },
  };

  const formData = new FormData();
  formData.append('file', file);
  formData.append('crop', JSON.stringify(cropPayload));
  formData.append('settings', JSON.stringify(settingsPayload));

  try {
    const response = await fetch('/api/convert', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Conversion failed');
    }

    const data = await response.json();
    lastHash = data.hash;
    gridInfo.textContent = `${data.grid_w} × ${data.grid_h}`;
    hashInfo.textContent = data.hash;
    setWarnings(data.warnings || []);
    updatePreview(data.preview_png_base64);
    setExportState(true);
    setStatus('Ready to export.');
  } catch (err) {
    setStatus(err.message || 'Conversion failed.');
    setExportState(false);
  }
});

exportTextBtn.addEventListener('click', () => {
  if (!lastHash) return;
  window.location.href = `/api/export/text?hash=${encodeURIComponent(lastHash)}&spaced=0`;
});

exportTextSpacedBtn.addEventListener('click', () => {
  if (!lastHash) return;
  window.location.href = `/api/export/text?hash=${encodeURIComponent(lastHash)}&spaced=1`;
});

exportPngBtn.addEventListener('click', () => {
  if (!lastHash) return;
  const bg = bgModeEl.value;
  const color = encodeURIComponent(bgColorEl.value);
  window.location.href = `/api/export/png?hash=${encodeURIComponent(lastHash)}&bg=${bg}&color=${color}`;
});

exportJpgBtn.addEventListener('click', () => {
  if (!lastHash) return;
  const color = encodeURIComponent(bgColorEl.value);
  window.location.href = `/api/export/jpg?hash=${encodeURIComponent(lastHash)}&color=${color}`;
});
