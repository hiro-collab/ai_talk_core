const appRoot = document.getElementById("app");
const uploadForm = document.getElementById("upload-form");
const startButton = document.getElementById("start-record");
const stopButton = document.getElementById("stop-record");
const statusBox = document.getElementById("record-status");
const debugBox = document.getElementById("record-debug");
const pageStatus = document.getElementById("page-status");
const pageResult = document.getElementById("page-result");
const pageCommand = document.getElementById("page-command");
const pageMeta = document.getElementById("page-meta");
const pageError = document.getElementById("page-error");
const resultActions = document.getElementById("result-actions");
const copyTranscriptButton = document.getElementById("copy-transcript");
const copyCommandButton = document.getElementById("copy-command");
const refreshHandoffButton = document.getElementById("refresh-handoff");
const actionFeedback = document.getElementById("action-feedback");
const statusPill = document.getElementById("record-status-pill");
const activeMicrophone = document.getElementById("active-microphone");
const gateAutoRecord = document.getElementById("record_gate_auto");
const diagDevice = document.getElementById("diag-device");
const diagMicrophone = document.getElementById("diag-microphone");
const diagGpu = document.getElementById("diag-gpu");
const diagFfmpeg = document.getElementById("diag-ffmpeg");
const diagInputGate = document.getElementById("diag-input-gate");
const endpoints = {
  transcribeUpload: appRoot?.dataset.apiTranscribeUpload || "/api/transcribe-upload",
  browserRecording: appRoot?.dataset.apiTranscribeBrowserRecording || "/api/transcribe-browser-recording",
  agentHandoffLatest: appRoot?.dataset.apiAgentHandoffLatest || "/api/agent-handoff-latest",
  doctor: appRoot?.dataset.apiDoctor || "/api/doctor",
  inputGate: appRoot?.dataset.apiInputGate || "/api/input-gate",
};
const apiToken = appRoot?.dataset.apiToken || "";
let mediaRecorder = null;
let activeStream = null;
let recorderState = "idle";
let chunks = [];
let lastBlobSize = 0;
let lastInputGateEnabled = null;
let gateAutoStartBlocked = false;

const showActionFeedback = (text) => {
  actionFeedback.textContent = text;
};

const setText = (node, text) => {
  if (node) {
    node.textContent = text;
    node.title = text;
  }
};

const formatUnknownMicrophone = (backend = "") => {
  if (!backend || backend === "unsupported" || backend === "unavailable") {
    return "未検出";
  }
  return `${backend} の既定マイク`;
};

const setActiveMicrophone = (label) => {
  setText(activeMicrophone, label || "未確認");
};

const localFetch = (url, options = {}) => {
  const headers = new Headers(options.headers || {});
  if (apiToken) {
    headers.set("X-AI-Core-Token", apiToken);
  }
  return fetch(url, { ...options, headers });
};

const loadDiagnostics = async () => {
  try {
    const response = await localFetch(endpoints.doctor);
    const payload = await response.json();
    const runtime = payload.runtime || {};
    const microphone = payload.microphone || {};
    const microphoneBackend = microphone.selected_microphone_backend_available
      ? microphone.selected_microphone_backend
      : "unavailable";
    const microphoneDevice = microphone.selected_microphone_device || "";
    setText(diagDevice, runtime.transcription_device || "unknown");
    setText(diagMicrophone, microphoneDevice || microphoneBackend);
    setActiveMicrophone(microphoneDevice || formatUnknownMicrophone(microphoneBackend));
    if (runtime.torch_cuda_available) {
      setText(diagGpu, runtime.nvidia_gpu_name || "cuda");
    } else if (runtime.nvidia_smi_available) {
      setText(diagGpu, "GPU visible / Torch CPU");
    } else {
      setText(diagGpu, "cpu");
    }
    setText(diagFfmpeg, runtime.ffmpeg_available ? "available" : "missing");
  } catch (error) {
    setText(diagDevice, "unknown");
    setText(diagMicrophone, "unknown");
    setText(diagGpu, "unknown");
    setText(diagFfmpeg, "unknown");
    setActiveMicrophone("未確認");
  }
};

const loadInputGate = async () => {
  try {
    const response = await localFetch(endpoints.inputGate);
    const payload = await response.json();
    const gate = payload.input_gate || {};
    const label = gate.input_enabled ? "enabled" : "disabled";
    const reason = gate.reason ? ` (${gate.reason})` : "";
    setText(diagInputGate, `${label}${reason}`);
    await handleInputGateRecording(gate);
  } catch (error) {
    setText(diagInputGate, "unknown");
  }
};

document.querySelectorAll(".mode-switch").forEach((switchNode) => {
  const buttons = Array.from(switchNode.querySelectorAll(".tab-toggle"));
  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      const targetId = button.dataset.target;
      const panel = document.getElementById(targetId);
      const panelGroup = switchNode.parentElement;
      buttons.forEach((candidate) => {
        const isActive = candidate === button;
        candidate.classList.toggle("active", isActive);
        candidate.setAttribute("aria-selected", String(isActive));
      });
      panelGroup.querySelectorAll(".mode-panel").forEach((candidate) => {
        candidate.hidden = candidate !== panel;
      });
    });
  });
});

const renderDebug = (note = "") => {
  const lines = [
    `state=${recorderState}`,
    `mediaRecorder=${mediaRecorder ? mediaRecorder.state : "none"}`,
    `chunks=${chunks.length}`,
    `lastBlobSize=${lastBlobSize}`,
  ];
  if (note) {
    lines.push(`note=${note}`);
  }
  debugBox.textContent = lines.join("\n");
};

const setStatus = (text) => {
  statusBox.hidden = !text;
  statusBox.textContent = text;
};

const setCurrentStatus = (stepName) => {
  const labels = {
    idle: "待機中",
    recording: "録音中",
    stopping: "停止処理中",
    uploading: "アップロード中",
    processing: "文字起こし中",
    done: "完了",
    error: "エラー",
  };
  statusPill.textContent = labels[stepName] || "待機中";
};

const setRecorderButtons = () => {
  startButton.disabled = recorderState !== "idle";
  stopButton.disabled = recorderState !== "recording";
  renderDebug("buttons updated");
};

const stopActiveStream = () => {
  if (!activeStream) {
    return;
  }
  activeStream.getTracks().forEach((track) => track.stop());
  activeStream = null;
};

const resetRecorderState = () => {
  stopActiveStream();
  if (mediaRecorder) {
    mediaRecorder.ondataavailable = null;
    mediaRecorder.onstop = null;
    mediaRecorder.onerror = null;
  }
  mediaRecorder = null;
  chunks = [];
  recorderState = "idle";
  setCurrentStatus("idle");
  setRecorderButtons();
};

const isInputGateAutoRecordingEnabled = () => Boolean(gateAutoRecord?.checked);

const handleInputGateRecording = async (gate) => {
  const inputEnabled = Boolean(gate.input_enabled);
  if (!isInputGateAutoRecordingEnabled()) {
    lastInputGateEnabled = inputEnabled;
    return;
  }

  if (!inputEnabled) {
    gateAutoStartBlocked = false;
  }

  const changed = lastInputGateEnabled !== inputEnabled;
  lastInputGateEnabled = inputEnabled;

  if (inputEnabled && recorderState === "idle" && !gateAutoStartBlocked) {
    await startRecording("input_gate");
    return;
  }
  if (!inputEnabled && changed && recorderState === "recording") {
    requestStopRecording("input_gate");
  }
};

const updateOutput = ({ message = "", transcript = "", command = "", command_path = "", command_text_path = "", error = "" }) => {
  pageStatus.hidden = !message;
  pageStatus.textContent = message;
  pageResult.hidden = !transcript;
  pageResult.textContent = transcript;
  pageCommand.hidden = !command;
  pageCommand.textContent = command ? `指示草案:\n${command}` : "";
  pageMeta.hidden = !command_path && !command_text_path;
  pageMeta.textContent = [
    command_path ? `handoff 保存先:\n${command_path}` : "",
    command_text_path ? `プロンプト保存先:\n${command_text_path}` : "",
  ].filter(Boolean).join("\n");
  pageError.hidden = !error;
  pageError.textContent = error;
  resultActions.hidden = !transcript && !command && !command_path && !command_text_path;
  copyTranscriptButton.disabled = !transcript;
  copyCommandButton.disabled = !command;
  refreshHandoffButton.disabled = !command_path && !command_text_path;
};

const submitForTranscription = async (url, formData, processingText, { updateRecorderStatus = false } = {}) => {
  if (updateRecorderStatus) {
    recorderState = "uploading";
    setCurrentStatus("uploading");
    setRecorderButtons();
    setStatus(processingText);
  }
  updateOutput({ message: processingText, transcript: "", command: "", command_path: "", command_text_path: "", error: "" });
  showActionFeedback("");
  renderDebug(`upload start -> ${url}`);
  try {
    if (updateRecorderStatus) {
      setCurrentStatus("processing");
    }
    const response = await localFetch(url, {
      method: "POST",
      body: formData,
      headers: { "X-Requested-With": "fetch" },
    });
    const payload = await response.json();
    updateOutput(payload);
    if (payload.error) {
      if (updateRecorderStatus) {
        setStatus("処理に失敗しました。");
        setCurrentStatus("error");
      }
    } else {
      if (updateRecorderStatus) {
        setStatus("処理完了");
        setCurrentStatus("done");
      }
    }
    renderDebug(`upload done status=${response.status}`);
  } catch (error) {
    const message = "通信に失敗しました: " + error;
    updateOutput({ error: message });
    if (updateRecorderStatus) {
      setStatus(message);
      setCurrentStatus("error");
    }
    renderDebug(`upload failed: ${error}`);
  } finally {
    if (updateRecorderStatus) {
      recorderState = "idle";
      setRecorderButtons();
    }
  }
};

uploadForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(uploadForm);
  await submitForTranscription(
    endpoints.transcribeUpload,
    formData,
    "アップロードした音声を処理中..."
  );
});

const startRecording = async (trigger = "manual") => {
  if (recorderState !== "idle") {
    renderDebug("start ignored because recorder is not idle");
    return false;
  }
  chunks = [];
  lastBlobSize = 0;
  try {
    activeStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const audioTrack = activeStream.getAudioTracks()[0];
    setActiveMicrophone(audioTrack?.label || "ブラウザの既定マイク");
    const recorder = new MediaRecorder(activeStream);
    mediaRecorder = recorder;
    renderDebug("getUserMedia ok; recorder created");
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunks.push(event.data);
      }
      renderDebug(`dataavailable size=${event.data.size}`);
    };
    recorder.onstop = async () => {
      if (mediaRecorder !== recorder) {
        renderDebug("onstop ignored because recorder changed");
        return;
      }
      const recordedChunks = [...chunks];
      lastBlobSize = recordedChunks.reduce((total, chunk) => total + chunk.size, 0);
      resetRecorderState();
      if (!recorder || recordedChunks.length === 0) {
        setStatus("録音データが空です。もう一度試してください。");
        setCurrentStatus("error");
        renderDebug("no recorded chunks after stop");
        return;
      }
      const blob = new Blob(recordedChunks, { type: recorder.mimeType || "audio/webm" });
      lastBlobSize = blob.size;
      renderDebug(`blob ready size=${blob.size}`);
      const formData = new FormData();
      formData.append("audio_blob", blob, "browser_recording.webm");
      formData.append("model", document.getElementById("record_model").value);
      formData.append("language", document.getElementById("record_language").value);
      if (document.getElementById("record_instruction_only").checked) {
        formData.append("instruction_only", "true");
      }
      if (document.getElementById("record_save_handoff").checked) {
        formData.append("save_handoff", "true");
      }
      await submitForTranscription(
        endpoints.browserRecording,
        formData,
        "録音データをアップロードして処理中...",
        { updateRecorderStatus: true }
      );
    };
    recorder.onerror = () => {
      resetRecorderState();
      setStatus("録音中にエラーが発生しました。");
      setCurrentStatus("error");
      renderDebug("recorder error");
    };
    recorder.start();
    recorderState = "recording";
    setCurrentStatus("recording");
    setRecorderButtons();
    if (trigger === "input_gate") {
      setStatus("入力ゲートにより録音中です。ゲートが閉じると送信します。");
    } else {
      setStatus("録音中です。停止後にアップロードして文字起こしします。");
    }
    renderDebug(`recording started trigger=${trigger}`);
    return true;
  } catch (error) {
    resetRecorderState();
    if (trigger === "input_gate") {
      gateAutoStartBlocked = true;
    }
    setStatus("録音開始に失敗しました: " + error);
    setCurrentStatus("error");
    renderDebug(`start failed: ${error}`);
    return false;
  }
};

const requestStopRecording = (trigger = "manual") => {
  if (!mediaRecorder || mediaRecorder.state === "inactive" || recorderState !== "recording") {
    renderDebug("stop ignored because recorder is not active");
    return;
  }
  recorderState = "stopping";
  setRecorderButtons();
  mediaRecorder.stop();
  stopButton.disabled = true;
  if (trigger === "input_gate") {
    setStatus("入力ゲートが閉じました。アップロードの準備中です。");
  } else {
    setStatus("録音停止。アップロードの準備中です。");
  }
  setCurrentStatus("stopping");
  renderDebug(`stop requested trigger=${trigger}`);
};

startButton?.addEventListener("click", async () => {
  await startRecording("manual");
});

stopButton?.addEventListener("click", () => {
  requestStopRecording("manual");
});

gateAutoRecord?.addEventListener("change", async () => {
  lastInputGateEnabled = null;
  gateAutoStartBlocked = false;
  await loadInputGate();
});

const copyText = async (text, label) => {
  if (!text) {
    showActionFeedback(`${label} はまだありません。`);
    return;
  }
  try {
    await navigator.clipboard.writeText(text);
    showActionFeedback(`${label} をコピーしました。`);
  } catch (error) {
    showActionFeedback(`${label} のコピーに失敗しました: ${error}`);
  }
};

copyTranscriptButton?.addEventListener("click", async () => {
  await copyText(pageResult.textContent, "文字起こし");
});

copyCommandButton?.addEventListener("click", async () => {
  const commandText = pageCommand.textContent.replace(/^指示草案:\n/, "");
  await copyText(commandText, "指示草案");
});

refreshHandoffButton?.addEventListener("click", async () => {
  if (refreshHandoffButton.disabled) {
    showActionFeedback("保存済み handoff がまだありません。");
    return;
  }
  try {
    const response = await localFetch(`${endpoints.agentHandoffLatest}?source=web`);
    const payload = await response.json();
    if (!response.ok) {
      showActionFeedback(payload.error || "handoff 保存先を取得できませんでした。");
      return;
    }
    updateOutput({
      message: pageStatus.textContent,
      transcript: payload.transcript || pageResult.textContent,
      command: payload.command || pageCommand.textContent.replace(/^指示草案:\n/, ""),
      command_path: payload.command_path || "",
      command_text_path: payload.command_text_path || "",
      error: "",
    });
    showActionFeedback("handoff 保存先を更新しました。");
  } catch (error) {
    showActionFeedback("handoff 保存先の確認に失敗しました: " + error);
  }
});

setCurrentStatus("idle");
setRecorderButtons();
copyTranscriptButton.disabled = !pageResult.textContent;
copyCommandButton.disabled = !pageCommand.textContent;
renderDebug("ready");
loadDiagnostics();
loadInputGate();
setInterval(loadInputGate, 1000);
