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
const microphoneSelect = document.getElementById("record_device_id");
const refreshMicrophonesButton = document.getElementById("refresh-microphones");
const echoCancellationToggle = document.getElementById("record_echo_cancellation");
const noiseSuppressionToggle = document.getElementById("record_noise_suppression");
const autoGainControlToggle = document.getElementById("record_auto_gain_control");
const diagDevice = document.getElementById("diag-device");
const diagMicrophone = document.getElementById("diag-microphone");
const diagGpu = document.getElementById("diag-gpu");
const diagFfmpeg = document.getElementById("diag-ffmpeg");
const diagInputGate = document.getElementById("diag-input-gate");
const endpoints = {
  transcribeUpload: appRoot?.dataset.apiTranscribeUpload || "/api/transcribe-upload",
  browserRecording: appRoot?.dataset.apiTranscribeBrowserRecording || "/api/transcribe-browser-recording",
  recordingChunk: appRoot?.dataset.apiRecordingChunk || "/api/recording-chunk",
  eventsIngest: appRoot?.dataset.apiEventsIngest || "/api/events/ingest",
  events: appRoot?.dataset.apiEvents || "/api/events",
  agentHandoffLatest: appRoot?.dataset.apiAgentHandoffLatest || "/api/agent-handoff-latest",
  doctor: appRoot?.dataset.apiDoctor || "/api/doctor",
  inputGate: appRoot?.dataset.apiInputGate || "/api/input-gate",
};
const apiToken = appRoot?.dataset.apiToken || "";
const WEB_OPTIONS_STORAGE_KEY = "ai_talk_core.web_options.v1";
const RECORDING_CHUNK_TIMESLICE_MS = 500;
const PREFERRED_RECORDING_MIME_TYPES = [
  "audio/webm;codecs=opus",
  "audio/webm",
];
const TRUE_OPTION_VALUES = new Set(["1", "true", "yes", "on"]);
const FALSE_OPTION_VALUES = new Set(["0", "false", "no", "off"]);
const OPTION_PROFILES = {
  integration: {
    record_gate_auto: "1",
    record_save_handoff: "1",
    upload_save_handoff: "1",
  },
};
const OPTION_PROFILE_ALIASES = {
  dify: "integration",
};
const MANAGED_OPTION_IDS = [
  "upload_model",
  "upload_language",
  "upload_save_handoff",
  "record_model",
  "record_language",
  "record_gate_auto",
  "record_save_handoff",
  "record_echo_cancellation",
  "record_noise_suppression",
  "record_auto_gain_control",
];
const QUERY_OPTION_ALIASES = {
  gate_auto: "record_gate_auto",
  input_gate: "record_gate_auto",
  input_gate_auto: "record_gate_auto",
  save_handoff: ["upload_save_handoff", "record_save_handoff"],
};
let mediaRecorder = null;
let activeStream = null;
let recorderState = "idle";
let chunks = [];
let lastBlobSize = 0;
let activeTurnId = "";
let chunkSequence = 0;
let pendingChunkUploads = [];
let lastInputGateEnabled = null;
let gateAutoStartBlocked = false;
let lastServerDebug = null;
let lastSupportedAudioConstraints = {};
let lastRequestedAudioConstraints = true;
let lastTrackSettings = {};
let lastTrackConstraints = {};
let lastOptionDefaultDebug = {
  profile: "",
  noPersist: false,
  reset: false,
  fallback: "html",
  sources: {},
};
let optionPersistenceEnabled = true;

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

const createTurnId = () => {
  if (window.crypto?.randomUUID) {
    return `web_${window.crypto.randomUUID().replaceAll("-", "")}`;
  }
  return `web_${Date.now().toString(36)}_${Math.random().toString(36).slice(2)}`;
};

const buildClientTiming = () => ({
  client_timestamp_wall: new Date().toISOString(),
  client_timestamp_monotonic: performance.now() / 1000,
  client_performance_now: performance.now(),
});

const buildMediaRecorderOptions = () => {
  if (!window.MediaRecorder?.isTypeSupported) {
    return {};
  }
  const mimeType = PREFERRED_RECORDING_MIME_TYPES.find((candidate) =>
    MediaRecorder.isTypeSupported(candidate)
  );
  return mimeType ? { mimeType } : {};
};

const emitTurnEvent = async (eventName, payload = {}) => {
  const turnId = activeTurnId || createTurnId();
  try {
    await localFetch(endpoints.eventsIngest, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "fetch",
      },
      body: JSON.stringify({
        event: eventName,
        turn_id: turnId,
        source: "web-ui",
        payload,
        ...buildClientTiming(),
      }),
    });
  } catch (error) {
    renderDebug(`event emit failed ${eventName}: ${error}`);
  }
};

const appendDebugValue = (lines, key, value) => {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    Object.entries(value).forEach(([childKey, childValue]) => {
      appendDebugValue(lines, `${key}.${childKey}`, childValue);
    });
    return;
  }
  lines.push(`${key}=${value ?? ""}`);
};

const normalizeProfileName = (profile) => {
  const normalized = (profile || "").trim().toLowerCase();
  return OPTION_PROFILE_ALIASES[normalized] || normalized;
};

const parseOptionBool = (value) => {
  if (value === null || value === undefined) {
    return null;
  }
  const normalized = String(value).trim().toLowerCase();
  if (!normalized) {
    return true;
  }
  if (TRUE_OPTION_VALUES.has(normalized)) {
    return true;
  }
  if (FALSE_OPTION_VALUES.has(normalized)) {
    return false;
  }
  return null;
};

const getManagedOptionElement = (id) => document.getElementById(id);

const setManagedOption = (id, value, source) => {
  const element = getManagedOptionElement(id);
  if (!element) {
    return;
  }
  if (element.type === "checkbox") {
    const parsed = parseOptionBool(value);
    if (parsed === null) {
      return;
    }
    element.checked = parsed;
  } else if (element.tagName === "SELECT") {
    const options = Array.from(element.options || []);
    if (!options.some((option) => option.value === value)) {
      return;
    }
    element.value = value;
  } else {
    element.value = String(value ?? "");
  }
  lastOptionDefaultDebug.sources[id] = source;
};

const getManagedOptionValue = (id) => {
  const element = getManagedOptionElement(id);
  if (!element) {
    return "";
  }
  if (element.type === "checkbox") {
    return element.checked ? "1" : "0";
  }
  return element.value;
};

const getCurrentManagedOptions = () => {
  const options = {};
  MANAGED_OPTION_IDS.forEach((id) => {
    const element = getManagedOptionElement(id);
    if (element) {
      options[id] = getManagedOptionValue(id);
    }
  });
  return options;
};

const loadPersistedOptions = () => {
  try {
    const rawOptions = localStorage.getItem(WEB_OPTIONS_STORAGE_KEY);
    return rawOptions ? JSON.parse(rawOptions) : {};
  } catch (error) {
    return {};
  }
};

const persistManagedOptions = () => {
  if (!optionPersistenceEnabled) {
    return;
  }
  try {
    localStorage.setItem(WEB_OPTIONS_STORAGE_KEY, JSON.stringify(getCurrentManagedOptions()));
  } catch (error) {
    renderDebug(`option persist failed: ${error}`);
  }
};

const removePersistedOptions = () => {
  try {
    localStorage.removeItem(WEB_OPTIONS_STORAGE_KEY);
  } catch (error) {
    renderDebug(`option reset failed: ${error}`);
  }
};

const applyOptionMap = (options, source) => {
  Object.entries(options || {}).forEach(([id, value]) => {
    if (MANAGED_OPTION_IDS.includes(id)) {
      setManagedOption(id, value, source);
    }
  });
};

const applyQueryOptions = (searchParams) => {
  MANAGED_OPTION_IDS.forEach((id) => {
    if (searchParams.has(id)) {
      setManagedOption(id, searchParams.get(id), "query");
    }
  });
  Object.entries(QUERY_OPTION_ALIASES).forEach(([alias, target]) => {
    if (!searchParams.has(alias)) {
      return;
    }
    const value = searchParams.get(alias);
    const targets = Array.isArray(target) ? target : [target];
    targets.forEach((id) => setManagedOption(id, value, `query:${alias}`));
  });
};

const applyStartupOptions = () => {
  const searchParams = new URLSearchParams(window.location.search);
  const requestedProfile = searchParams.has("profile")
    ? searchParams.get("profile")
    : appRoot?.dataset.webPreset || "";
  const profile = normalizeProfileName(requestedProfile);
  const noPersist = parseOptionBool(searchParams.get("no_persist")) === true;
  const reset = parseOptionBool(searchParams.get("reset_options")) === true;
  optionPersistenceEnabled = !noPersist;
  lastOptionDefaultDebug = {
    profile,
    noPersist,
    reset,
    fallback: "html",
    sources: {},
  };
  if (reset) {
    removePersistedOptions();
  }
  if (!noPersist && !reset) {
    applyOptionMap(loadPersistedOptions(), "localStorage");
  }
  if (profile && OPTION_PROFILES[profile]) {
    applyOptionMap(OPTION_PROFILES[profile], `profile:${profile}`);
  }
  applyQueryOptions(searchParams);
};

const bindManagedOptionPersistence = () => {
  MANAGED_OPTION_IDS.forEach((id) => {
    const element = getManagedOptionElement(id);
    if (!element) {
      return;
    }
    element.addEventListener("change", persistManagedOptions);
  });
};

const setSelectOptions = (select, options, selectedValue = "") => {
  if (!select) {
    return;
  }
  select.replaceChildren();
  options.forEach(({ label, value }) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.appendChild(option);
  });
  const hasSelectedValue = Array.from(select.options).some((option) => option.value === selectedValue);
  select.value = hasSelectedValue ? selectedValue : "";
};

const getSelectedMicrophoneLabel = () => microphoneSelect?.selectedOptions?.[0]?.textContent || "";

const getSupportedAudioConstraints = () => {
  if (!navigator.mediaDevices?.getSupportedConstraints) {
    return {};
  }
  const supported = navigator.mediaDevices.getSupportedConstraints();
  return {
    deviceId: Boolean(supported.deviceId),
    echoCancellation: Boolean(supported.echoCancellation),
    noiseSuppression: Boolean(supported.noiseSuppression),
    autoGainControl: Boolean(supported.autoGainControl),
    sampleRate: Boolean(supported.sampleRate),
    channelCount: Boolean(supported.channelCount),
  };
};

const buildAudioConstraints = () => {
  const supported = getSupportedAudioConstraints();
  const constraints = {};
  const selectedDeviceId = microphoneSelect?.value || "";
  if (selectedDeviceId && supported.deviceId) {
    constraints.deviceId = { exact: selectedDeviceId };
  }
  if (supported.echoCancellation) {
    constraints.echoCancellation = Boolean(echoCancellationToggle?.checked);
  }
  if (supported.noiseSuppression) {
    constraints.noiseSuppression = Boolean(noiseSuppressionToggle?.checked);
  }
  if (supported.autoGainControl) {
    constraints.autoGainControl = Boolean(autoGainControlToggle?.checked);
  }
  lastSupportedAudioConstraints = supported;
  lastRequestedAudioConstraints = Object.keys(constraints).length > 0 ? constraints : true;
  return lastRequestedAudioConstraints;
};

const loadMicrophoneDevices = async () => {
  if (!microphoneSelect || !navigator.mediaDevices?.enumerateDevices) {
    return;
  }
  const selectedValue = microphoneSelect.value;
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const audioInputs = devices.filter((device) => device.kind === "audioinput");
    const options = [
      { label: "既定マイク", value: "" },
      ...audioInputs.map((device, index) => ({
        label: device.label || `マイク ${index + 1}`,
        value: device.deviceId,
      })),
    ];
    setSelectOptions(microphoneSelect, options, selectedValue);
    const selectedLabel = getSelectedMicrophoneLabel();
    if (recorderState === "idle" && !activeStream && selectedLabel) {
      setActiveMicrophone(selectedLabel);
    }
    renderDebug(`microphones loaded count=${audioInputs.length}`);
  } catch (error) {
    renderDebug(`microphone list failed: ${error}`);
  }
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
    `turnId=${activeTurnId}`,
    `chunkSequence=${chunkSequence}`,
    `pendingChunkUploads=${pendingChunkUploads.length}`,
    `chunkTimesliceMs=${RECORDING_CHUNK_TIMESLICE_MS}`,
    `lastBlobSize=${lastBlobSize}`,
    `gateAuto=${isInputGateAutoRecordingEnabled()}`,
    `selectedMicrophone=${getSelectedMicrophoneLabel()}`,
  ];
  if (note) {
    lines.push(`note=${note}`);
  }
  appendDebugValue(lines, "options.startup", lastOptionDefaultDebug);
  appendDebugValue(lines, "browser.supportedAudioConstraints", lastSupportedAudioConstraints);
  appendDebugValue(lines, "browser.requestedAudioConstraints", lastRequestedAudioConstraints);
  appendDebugValue(lines, "browser.trackSettings", lastTrackSettings);
  appendDebugValue(lines, "browser.trackConstraints", lastTrackConstraints);
  if (lastServerDebug) {
    Object.entries(lastServerDebug).forEach(([key, value]) => {
      appendDebugValue(lines, `server.${key}`, value);
    });
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
  const gateManaged = isInputGateAutoRecordingEnabled();
  startButton.disabled = recorderState !== "idle" || gateManaged;
  startButton.title = gateManaged ? "入力ゲート制御中はゲート信号で自動開始します。" : "";
  startButton.setAttribute("aria-disabled", String(startButton.disabled));
  stopButton.disabled = recorderState !== "recording";
  stopButton.setAttribute("aria-disabled", String(stopButton.disabled));
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

const uploadRecordingChunk = (chunkBlob) => {
  if (!chunkBlob?.size || !activeTurnId) {
    return;
  }
  const sequence = chunkSequence;
  chunkSequence += 1;
  const formData = new FormData();
  formData.append("audio_chunk", chunkBlob, `chunk_${String(sequence).padStart(6, "0")}.webm`);
  formData.append("turn_id", activeTurnId);
  formData.append("sequence", String(sequence));
  formData.append("is_final", "false");
  const upload = localFetch(endpoints.recordingChunk, {
    method: "POST",
    body: formData,
    headers: { "X-Requested-With": "fetch" },
  })
    .then(async (response) => {
      if (!response.ok) {
        const text = await response.text();
        throw new Error(`chunk upload ${response.status}: ${text}`);
      }
      return response.json();
    })
    .catch((error) => {
      renderDebug(`chunk upload failed sequence=${sequence}: ${error}`);
    });
  pendingChunkUploads.push(upload);
  upload.finally(() => {
    pendingChunkUploads = pendingChunkUploads.filter((candidate) => candidate !== upload);
    renderDebug(`chunk upload settled sequence=${sequence}`);
  });
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
  lastServerDebug = null;
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
    lastServerDebug = payload.debug || null;
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
  if (trigger === "manual" && isInputGateAutoRecordingEnabled()) {
    setStatus("入力ゲート制御中はゲート信号で録音を開始します。");
    renderDebug("manual start blocked while input gate control is enabled");
    return false;
  }
  if (recorderState !== "idle") {
    renderDebug("start ignored because recorder is not idle");
    return false;
  }
  chunks = [];
  lastBlobSize = 0;
  activeTurnId = createTurnId();
  chunkSequence = 0;
  pendingChunkUploads = [];
  try {
    const audioConstraints = buildAudioConstraints();
    renderDebug("requesting microphone");
    activeStream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
    const audioTrack = activeStream.getAudioTracks()[0];
    lastTrackSettings = audioTrack?.getSettings?.() || {};
    lastTrackConstraints = audioTrack?.getConstraints?.() || {};
    setActiveMicrophone(audioTrack?.label || getSelectedMicrophoneLabel() || "ブラウザの既定マイク");
    await loadMicrophoneDevices();
    const recorder = new MediaRecorder(activeStream, buildMediaRecorderOptions());
    mediaRecorder = recorder;
    renderDebug("getUserMedia ok; recorder created");
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunks.push(event.data);
        uploadRecordingChunk(event.data);
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
      await emitTurnEvent("record_stop", {
        chunk_count: recordedChunks.length,
        chunk_sequence: chunkSequence,
        blob_size_bytes: lastBlobSize,
      });
      const stoppedTurnId = activeTurnId;
      resetRecorderState();
      if (!recorder || recordedChunks.length === 0) {
        activeTurnId = "";
        setStatus("録音データが空です。もう一度試してください。");
        setCurrentStatus("error");
        renderDebug("no recorded chunks after stop");
        return;
      }
      const blob = new Blob(recordedChunks, { type: recorder.mimeType || "audio/webm" });
      lastBlobSize = blob.size;
      const uploadFilename = "browser_recording.webm";
      const recordModel = document.getElementById("record_model").value;
      const recordLanguage = document.getElementById("record_language").value;
      renderDebug(`blob ready size=${blob.size} filename=${uploadFilename} model=${recordModel} language=${recordLanguage}`);
      const formData = new FormData();
      formData.append("audio_blob", blob, uploadFilename);
      formData.append("turn_id", stoppedTurnId);
      formData.append("model", recordModel);
      formData.append("language", recordLanguage);
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
      activeTurnId = "";
    };
    recorder.onerror = () => {
      resetRecorderState();
      setStatus("録音中にエラーが発生しました。");
      setCurrentStatus("error");
      renderDebug("recorder error");
    };
    recorder.start(RECORDING_CHUNK_TIMESLICE_MS);
    recorderState = "recording";
    setCurrentStatus("recording");
    setRecorderButtons();
    if (trigger === "input_gate") {
      setStatus("入力ゲートにより録音中です。ゲートが閉じると送信します。");
    } else {
      setStatus("録音中です。停止後にアップロードして文字起こしします。");
    }
    renderDebug(`recording started trigger=${trigger}`);
    await emitTurnEvent("record_start", {
      trigger,
      timeslice_ms: RECORDING_CHUNK_TIMESLICE_MS,
      mime_type: recorder.mimeType || "",
    });
    return true;
  } catch (error) {
    resetRecorderState();
    activeTurnId = "";
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
  setRecorderButtons();
  if (isInputGateAutoRecordingEnabled() && recorderState === "idle") {
    setStatus("入力ゲート制御中です。手動開始は無効になり、ゲート信号で録音します。");
  }
  await loadInputGate();
});

refreshMicrophonesButton?.addEventListener("click", async () => {
  await loadMicrophoneDevices();
});

microphoneSelect?.addEventListener("change", () => {
  setActiveMicrophone(getSelectedMicrophoneLabel() || "既定マイク");
  renderDebug("microphone selection changed");
});

[echoCancellationToggle, noiseSuppressionToggle, autoGainControlToggle].forEach((toggle) => {
  toggle?.addEventListener("change", () => {
    buildAudioConstraints();
    renderDebug("audio constraints changed");
  });
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

applyStartupOptions();
bindManagedOptionPersistence();
buildAudioConstraints();
setCurrentStatus("idle");
setRecorderButtons();
copyTranscriptButton.disabled = !pageResult.textContent;
copyCommandButton.disabled = !pageCommand.textContent;
renderDebug("ready");
loadDiagnostics();
loadMicrophoneDevices();
navigator.mediaDevices?.addEventListener?.("devicechange", loadMicrophoneDevices);
loadInputGate();
setInterval(loadInputGate, 1000);
