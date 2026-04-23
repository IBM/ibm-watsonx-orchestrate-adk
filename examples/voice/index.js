const SAMPLE_RATE = 16000;

// The websocket connection.
let ws = null;
let wavStreamPlayer = null;
let wavRecorder = null;
let source = null;

// Whether we should be playing audio.
let isPlaying = false;

let startBtn = document.getElementById('startAudioButton');
let stopBtn = document.getElementById('stopAudioButton');
const dtmfDisplay = document.getElementById('dtmfDisplay');

const fields = ['agent_id', 'environment_id', 'access_token', 'url', 'thread_id'];

function getWebSocketProtocol() {
    return window.location.protocol === 'https:' ? 'wss:' : 'ws:';
}

function getDefaultVoiceRuntimeUrl() {
    return `${getWebSocketProtocol()}//${window.location.host}/v1/conversation`;
}

const RECORDING_API_BASE = `${window.location.origin}/api`;
const RECORDING_SERVER_URL = `${getWebSocketProtocol()}//${window.location.host}/record`;

// Initialize Carbon tabs
function initializeTabs() {
    const tabItems = document.querySelectorAll('.bx--tabs__nav-item');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabItems.forEach((item, index) => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            
            // Remove active class from all tabs and contents
            tabItems.forEach(tab => {
                tab.classList.remove('bx--tabs__nav-item--selected');
                const link = tab.querySelector('.bx--tabs__nav-link');
                if (link) {
                    link.setAttribute('aria-selected', 'false');
                    link.setAttribute('tabindex', '-1');
                }
            });
            
            tabContents.forEach(content => {
                content.classList.remove('active');
            });
            
            // Add active class to clicked tab
            item.classList.add('bx--tabs__nav-item--selected');
            const link = item.querySelector('.bx--tabs__nav-link');
            if (link) {
                link.setAttribute('aria-selected', 'true');
                link.setAttribute('tabindex', '0');
            }
            
            // Show corresponding content
            const targetId = item.getAttribute('data-target');
            const targetContent = document.querySelector(targetId);
            if (targetContent) {
                targetContent.classList.add('active');
                
                // If switching to recordings tab, load recordings
                if (targetId === '#recordings-tab') {
                    loadRecordings();
                }
                
                // If switching to CDR logs tab, load CDR reports
                if (targetId === '#cdr-logs-tab') {
                    loadCDRReports();
                    // Start auto-refresh
                    if (window.cdrRefreshInterval) {
                        clearInterval(window.cdrRefreshInterval);
                    }
                    window.cdrRefreshInterval = setInterval(loadCDRReports, 5000);
                } else {
                    // Stop auto-refresh when leaving CDR tab
                    if (window.cdrRefreshInterval) {
                        clearInterval(window.cdrRefreshInterval);
                        window.cdrRefreshInterval = null;
                    }
                }
            }
        });
    });
}

window.onload = function() {
    initializeTabs();
    
    fields.forEach(id => {
      const val = localStorage.getItem(id);
      if (val !== null) {
        document.getElementById(id).value = val;
      } else if (id === 'url') {
        document.getElementById(id).value = getDefaultVoiceRuntimeUrl();
      }
    });
    
    // Display the recording server URL
    const recordingServerUrl = document.getElementById('recordingServerUrl');
    if (recordingServerUrl) {
      recordingServerUrl.textContent = RECORDING_SERVER_URL;
    }
    
    // Display the CDR webhook URL
    const cdrWebhookUrl = document.getElementById('cdrWebhookUrl');
    if (cdrWebhookUrl) {
      cdrWebhookUrl.textContent = `${window.location.origin}/cdr-webhook`;
    }
    
    // Add event listeners for DTMF buttons
    document.querySelectorAll('.dtmf-btn').forEach(btn => {
      btn.addEventListener('mousedown', () => {
        const tone = btn.getAttribute('data-tone');
        sendDTMFTone(tone);
        dtmfDisplay.textContent = tone;
      });
      
      btn.addEventListener('mouseup', () => {
        dtmfDisplay.textContent = '';
      });
      
      btn.addEventListener('mouseleave', () => {
        dtmfDisplay.textContent = '';
      });
    });
    
    // Also support keyboard input
    document.addEventListener('keydown', (e) => {
      const key = e.key;
      const validKeys = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '#'];
      
      if (validKeys.includes(key)) {
        sendDTMFTone(key);
        dtmfDisplay.textContent = key;
        
        // Highlight the corresponding button
        const btn = document.querySelector(`.dtmf-btn[data-tone="${key}"]`);
        if (btn) {
          btn.classList.add('bx--btn--primary');
          btn.classList.remove('bx--btn--secondary');
        }
      }
    });
    
    document.addEventListener('keyup', (e) => {
      const key = e.key;
      const validKeys = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '#'];
      
      if (validKeys.includes(key)) {
        dtmfDisplay.textContent = '';
        
        // Remove highlight from the button
        const btn = document.querySelector(`.dtmf-btn[data-tone="${key}"]`);
        if (btn) {
          btn.classList.remove('bx--btn--primary');
          btn.classList.add('bx--btn--secondary');
        }
      }
    });
  };

setTimeout(() => {
    const progressText = document.getElementById('progressText');
    progressText.textContent = 'We are ready! Make sure to run the server and then click `Start Audio`.';
    startBtn.disabled = false;
    stopBtn.disabled = true;
});

function buildQueryParams() {
    const params = new URLSearchParams();
    fields.forEach(id => {
    if (id === "url") {
        return;
    }
      const val = localStorage.getItem(id);
      if (val) {
        params.set(id, val);
      }
    });
    
    // Add the target URL as a parameter for the proxy
    const targetUrl = localStorage.getItem('url') || getDefaultVoiceRuntimeUrl();
    params.set('target_url', targetUrl);
    
    return params.toString();
}

function initWebSocket() {
    // Connect to the local proxy endpoint instead of directly to voice runtime
    const proxyUrl = `${getWebSocketProtocol()}//${window.location.host}/v1/conversation`;
    console.log(`Connecting to local proxy: ${proxyUrl}`);
    console.log(`Target voice runtime: ${localStorage.getItem('url') || getDefaultVoiceRuntimeUrl()}`);
    
    ws = new WebSocket(`${proxyUrl}?${buildQueryParams()}`);

    // This is so `event.data` is already an ArrayBuffer.
    ws.binaryType = 'arraybuffer';

    ws.addEventListener('open', handleWebSocketOpen);
    ws.addEventListener('message', handleWebSocketMessage);
    ws.addEventListener('close', (event) => {
        console.log('WebSocket connection closed.', event.code, event.reason);
        stopAudio(false);
    });
    ws.addEventListener('error', (event) => {
        console.error('WebSocket error:', event);
    });
}

async function handleWebSocketOpen(event) {
    console.log('WebSocket connection established.', event)
    const startMessage = {
        "type": "start",
        "event_id": "407ed57a-4d70-4425-be80-ce315164b547",
        "audio": {
            "input": {
                "encoding": "audio/l16",
                "sample_rate": 16000,
            },
            "output": {
                "encoding": "audio/l16",
                "sample_rate": 16000
            }
        }
    };
    
    if (localStorage.getItem('thread_id')) {
        startMessage.thread_id = localStorage.getItem('thread_id')
    }
    ws.send(JSON.stringify(startMessage))
    wavRecorder = new WavRecorder({ sampleRate: SAMPLE_RATE });
    await wavRecorder.begin();

    // Start recording
    // This callback will be triggered in chunks of 8192 samples by default
    // { mono, raw } are Int16Array (PCM16) mono & full channel data
    await wavRecorder.record((data) => {
        if (isPlaying) {
            const { mono, raw } = data;
            ws.send(mono);
        }
    });
}

function handleWebSocketMessage(event) {
    if (typeof event.data === "string") {
        console.log("Text frame received:", event.data);
    } else {
        const arrayBuffer = event.data;
        if (isPlaying && wavStreamPlayer) {
            wavStreamPlayer.add16BitPCM(arrayBuffer, 'my-track');
        }
    }
}

// Scaffolding code if we wanted to send send real binary audio to voice controller
function generateDTMFTone(tone, durationMs = 200, sampleRate = SAMPLE_RATE) {
    // DTMF frequencies (Hz)
    const dtmfFrequencies = {
        '1': { f1: 697, f2: 1209 },
        '2': { f1: 697, f2: 1336 },
        '3': { f1: 697, f2: 1477 },
        '4': { f1: 770, f2: 1209 },
        '5': { f1: 770, f2: 1336 },
        '6': { f1: 770, f2: 1477 },
        '7': { f1: 852, f2: 1209 },
        '8': { f1: 852, f2: 1336 },
        '9': { f1: 852, f2: 1477 },
        '*': { f1: 941, f2: 1209 },
        '0': { f1: 941, f2: 1336 },
        '#': { f1: 941, f2: 1477 }
    };

    if (!dtmfFrequencies[tone]) {
        console.error('Invalid DTMF tone:', tone);
        return null;
    }

    const { f1, f2 } = dtmfFrequencies[tone];
    const numSamples = Math.floor(durationMs * sampleRate / 1000);
    const samples = new Int16Array(numSamples);

    for (let i = 0; i < numSamples; i++) {
        const t = i / sampleRate;
        // Generate two sine waves and mix them
        const sample1 = Math.sin(2 * Math.PI * f1 * t);
        const sample2 = Math.sin(2 * Math.PI * f2 * t);
        // Mix and scale to 16-bit range
        const mixed = 0.5 * (sample1 + sample2);
        samples[i] = Math.round(mixed * 32767 * 0.5); // Reduce volume to avoid clipping
    }

    return samples;
}

function sendDTMFTone(tone) {
    if (!isPlaying || !ws) {
        console.log('Not connected, cannot send DTMF tone');
        return;
    }


    console.log(`Sending tone: ${ tone } to voice controller.`);
    const dtmfMessage = JSON.stringify({
        "type": "dtmf",
        "digit": tone
    });

    console.log(`Message: ${dtmfMessage}`);
    ws.send(dtmfMessage);
/*
    TBD -- call generateDTMFTone for plaaying the audio back in the browser, and sending audio to V/C
    const dtmfSamples = generateDTMFTone(tone);
    if (dtmfSamples) {
        ws.send(dtmfSamples.buffer);
    }
*/
}
async function startAudioButtonHandler() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert('getUserMedia is not supported in your browser.');
        return;
    }

    fields.forEach(id => {
        localStorage.setItem(id, document.getElementById(id).value);
    });

    startBtn.disabled = true;
    stopBtn.disabled = false;

    wavStreamPlayer = new WavStreamPlayer({
        sampleRate: SAMPLE_RATE
    });

    await wavStreamPlayer.connect();

    isPlaying = true;

    initWebSocket();
}

function stopAudio(closeWebsocket) {
    isPlaying = false;
    startBtn.disabled = false;
    stopBtn.disabled = true;

    if (ws && closeWebsocket) {
        ws.close();
        ws = null;
    }

    if (wavRecorder) {
        wavRecorder.pause();
    }

    if (source) {
        source.disconnect();
    }
}

function stopAudioBtnHandler() {
    stopAudio(true);
}

startBtn.addEventListener('click', startAudioButtonHandler);
stopBtn.addEventListener('click', stopAudioBtnHandler);
startBtn.disabled = true;

// ============================================================================
// Recording Viewer Functionality
// ============================================================================

let currentRecordingId = null;

// Initialize recording viewer
document.addEventListener('DOMContentLoaded', () => {
    const refreshBtn = document.getElementById('refreshRecordingsBtn');
    const viewerTabs = document.querySelectorAll('.viewer-tab-btn');
    
    if (refreshBtn) {
        refreshBtn.addEventListener('click', loadRecordings);
    }
    
    // Setup tab switching
    viewerTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.getAttribute('data-tab');
            switchViewerTab(tabName);
        });
    });
    
    // Load recordings on page load
    loadRecordings();
});

async function loadRecordings() {
    const recordingsList = document.getElementById('recordingsList');
    
    try {
        recordingsList.innerHTML = '<div class="no-data">Loading recordings...</div>';
        
        const response = await fetch(`${RECORDING_API_BASE}/recordings`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (!data.recordings || data.recordings.length === 0) {
            recordingsList.innerHTML = '<div class="no-data">No recordings found. Start a call with recording enabled to create recordings.</div>';
            return;
        }
        
        // Clear and populate recordings list
        recordingsList.innerHTML = '';
        data.recordings.forEach(recording => {
            const item = createRecordingItem(recording);
            recordingsList.appendChild(item);
        });
        
    } catch (error) {
        console.error('Error loading recordings:', error);
        recordingsList.innerHTML = `<div class="no-data">Error loading recordings: ${error.message}<br>Make sure the recording service is reachable at ${RECORDING_API_BASE}.</div>`;
    }
}

function createRecordingItem(recording) {
    const item = document.createElement('div');
    item.className = 'recording-card';
    item.setAttribute('data-recording-id', recording.id);
    
    const metadata = recording.metadata || {};
    const duration = metadata.duration_ms ? `${(metadata.duration_ms / 1000).toFixed(1)}s` : 'N/A';
    const startTime = metadata.start_time ? new Date(metadata.start_time).toLocaleString() : 'N/A';
    
    item.innerHTML = `
        <div class="recording-header">
            <div class="recording-name">${recording.name}</div>
            <div class="recording-duration">${duration}</div>
        </div>
        <div class="recording-meta">
            Started: ${startTime}
        </div>
        <div class="recording-meta">
            User frames: ${metadata.user_frames || 0} | Agent frames: ${metadata.agent_frames || 0}
        </div>
        <div class="recording-actions">
            <button class="delete-btn" data-recording-id="${recording.id}">🗑️ Delete</button>
        </div>
    `;
    
    // Add click handler for the card (but not the delete button)
    item.addEventListener('click', (e) => {
        if (!e.target.classList.contains('delete-btn')) {
            selectRecording(recording.id);
        }
    });
    
    // Add delete button handler
    const deleteBtn = item.querySelector('.delete-btn');
    deleteBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        deleteRecording(recording.id);
    });
    
    return item;
}

async function selectRecording(recordingId) {
    // Update UI selection
    document.querySelectorAll('.recording-item').forEach(item => {
        item.classList.remove('selected');
    });
    
    const selectedItem = document.querySelector(`[data-recording-id="${recordingId}"]`);
    if (selectedItem) {
        selectedItem.classList.add('selected');
    }
    
    currentRecordingId = recordingId;
    
    // Show viewer section
    const viewerSection = document.getElementById('viewerSection');
    viewerSection.classList.add('active');
    
    const viewerTitle = document.getElementById('viewerTitle');
    viewerTitle.textContent = `Recording: ${recordingId}`;
    
    // Load metadata
    await loadMetadata(recordingId);
    
    // Prepare audio players
    prepareAudioPlayer('user', recordingId);
    prepareAudioPlayer('agent', recordingId);
    prepareInterleavedAudioPlayer(recordingId);
}

async function loadMetadata(recordingId) {
    const metadataJson = document.getElementById('metadataJson');
    
    try {
        const response = await fetch(`${RECORDING_API_BASE}/recordings/${recordingId}/metadata`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const metadata = await response.json();
        metadataJson.textContent = JSON.stringify(metadata, null, 2);
        
    } catch (error) {
        console.error('Error loading metadata:', error);
        metadataJson.textContent = `Error loading metadata: ${error.message}`;
    }
}

function prepareAudioPlayer(role, recordingId) {
    const audioPlayer = document.getElementById(`${role}AudioPlayer`);
    const noDataDiv = document.getElementById(`${role}AudioNoData`);
    
    // Set the audio source
    const audioUrl = `${RECORDING_API_BASE}/recordings/${recordingId}/audio/${role}`;
    
    // Check if audio exists by trying to load it
    fetch(audioUrl, { method: 'HEAD' })
        .then(response => {
            if (response.ok) {
                // Audio exists, show player
                audioPlayer.style.display = 'block';
                noDataDiv.style.display = 'none';
                
                // We need to convert raw PCM to WAV for browser playback
                loadAndConvertAudio(audioUrl, audioPlayer);
            } else {
                // No audio available
                audioPlayer.style.display = 'none';
                noDataDiv.style.display = 'block';
            }
        })
        .catch(error => {
            console.error(`Error checking ${role} audio:`, error);
            audioPlayer.style.display = 'none';
            noDataDiv.style.display = 'block';
        });
}

async function loadAndConvertAudio(audioUrl, audioElement) {
    try {
        const response = await fetch(audioUrl);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const rawPcmData = await response.arrayBuffer();
        
        // Convert raw PCM16 to WAV
        const wavBlob = pcmToWav(rawPcmData, 16000, 1, 16);
        const wavUrl = URL.createObjectURL(wavBlob);
        
        audioElement.src = wavUrl;
        
        // Clean up the blob URL when audio is done
        audioElement.addEventListener('ended', () => {
            URL.revokeObjectURL(wavUrl);
        }, { once: true });
        
    } catch (error) {
        console.error('Error loading audio:', error);
        audioElement.style.display = 'none';
        const role = audioElement.id.includes('user') ? 'user' : 'agent';
        document.getElementById(`${role}AudioNoData`).style.display = 'block';
        document.getElementById(`${role}AudioNoData`).textContent = `Error loading audio: ${error.message}`;
    }
}

async function loadAndConvertStereoAudio(audioUrl, audioElement) {
    try {
        const response = await fetch(audioUrl);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const rawPcmData = await response.arrayBuffer();
        
        // Convert raw stereo PCM16 to WAV (2 channels)
        const wavBlob = pcmToWav(rawPcmData, 16000, 2, 16);
        const wavUrl = URL.createObjectURL(wavBlob);
        
        audioElement.src = wavUrl;
        
        // Clean up the blob URL when audio is done
        audioElement.addEventListener('ended', () => {
            URL.revokeObjectURL(wavUrl);
        }, { once: true });
        
    } catch (error) {
        console.error('Error loading stereo audio:', error);
        audioElement.style.display = 'none';
        document.getElementById('interleavedAudioNoData').style.display = 'block';
        document.getElementById('interleavedAudioNoData').textContent = `Error loading audio: ${error.message}`;
    }
}

function pcmToWav(pcmData, sampleRate, numChannels, bitDepth) {
    const dataLength = pcmData.byteLength;
    const buffer = new ArrayBuffer(44 + dataLength);
    const view = new DataView(buffer);
    
    // WAV header
    // "RIFF" chunk descriptor
    writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + dataLength, true);
    writeString(view, 8, 'WAVE');
    
    // "fmt " sub-chunk
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true); // Subchunk1Size (16 for PCM)
    view.setUint16(20, 1, true); // AudioFormat (1 for PCM)
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * numChannels * bitDepth / 8, true); // ByteRate
    view.setUint16(32, numChannels * bitDepth / 8, true); // BlockAlign
    view.setUint16(34, bitDepth, true);
    
    // "data" sub-chunk
    writeString(view, 36, 'data');
    view.setUint32(40, dataLength, true);
    
    // Copy PCM data
    const pcmView = new Uint8Array(pcmData);
    const wavView = new Uint8Array(buffer);
    wavView.set(pcmView, 44);
    
    return new Blob([buffer], { type: 'audio/wav' });
}

function writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
    }
}

function switchViewerTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.viewer-tab-btn').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    // Update content sections
    document.querySelectorAll('.viewer-content').forEach(content => {
        content.classList.remove('active');
    });
    
    if (tabName === 'metadata') {
        document.getElementById('metadataContent').classList.add('active');
    } else if (tabName === 'user-audio') {
        document.getElementById('userAudioContent').classList.add('active');
    } else if (tabName === 'agent-audio') {
        document.getElementById('agentAudioContent').classList.add('active');
    } else if (tabName === 'interleaved-audio') {
        document.getElementById('interleavedAudioContent').classList.add('active');
    }
}

function prepareInterleavedAudioPlayer(recordingId) {
    const audioPlayer = document.getElementById('interleavedAudioPlayer');
    const noDataDiv = document.getElementById('interleavedAudioNoData');
    
    // Set the audio source
    const audioUrl = `${RECORDING_API_BASE}/recordings/${recordingId}/audio/interleaved`;
    
    // Check if audio exists by trying to load it
    fetch(audioUrl, { method: 'HEAD' })
        .then(response => {
            if (response.ok) {
                // Audio exists, show player
                audioPlayer.style.display = 'block';
                noDataDiv.style.display = 'none';
                
                // Convert raw stereo PCM to WAV for browser playback
                // Interleaved audio is stereo: left=user, right=agent
                loadAndConvertStereoAudio(audioUrl, audioPlayer);
            } else {
                // No audio available
                audioPlayer.style.display = 'none';
                noDataDiv.style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Error checking interleaved audio:', error);
            audioPlayer.style.display = 'none';
            noDataDiv.style.display = 'block';
        });
}
// ============================================================================
// Delete Recording Functionality
// ============================================================================

// Custom confirmation modal to avoid browser dialog blocking
function showConfirmModal(title, message) {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirmModal');
        const titleEl = document.getElementById('confirmModalTitle');
        const bodyEl = document.getElementById('confirmModalBody');
        const confirmBtn = document.getElementById('confirmModalConfirm');
        const cancelBtn = document.getElementById('confirmModalCancel');
        
        titleEl.textContent = title;
        bodyEl.textContent = message;
        modal.classList.add('active');
        
        const handleConfirm = () => {
            cleanup();
            resolve(true);
        };
        
        const handleCancel = () => {
            cleanup();
            resolve(false);
        };
        
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                handleCancel();
            }
        };
        
        const cleanup = () => {
            modal.classList.remove('active');
            confirmBtn.removeEventListener('click', handleConfirm);
            cancelBtn.removeEventListener('click', handleCancel);
            document.removeEventListener('keydown', handleEscape);
        };
        
        confirmBtn.addEventListener('click', handleConfirm);
        cancelBtn.addEventListener('click', handleCancel);
        document.addEventListener('keydown', handleEscape);
        
        // Close modal when clicking outside
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                handleCancel();
            }
        });
    });
}

async function deleteRecording(recordingId) {
    const confirmed = await showConfirmModal(
        'Delete Recording',
        `Are you sure you want to delete recording "${recordingId}"?\n\nThis action cannot be undone.`
    );
    
    if (!confirmed) {
        return;
    }
    
    try {
        const response = await fetch(`${RECORDING_API_BASE}/recordings/${recordingId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || `HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('Recording deleted:', result);
        
        // Show success message
        alert(`Recording "${recordingId}" deleted successfully!`);
        
        // Hide viewer if this recording was selected
        if (currentRecordingId === recordingId) {
            const viewerSection = document.getElementById('viewerSection');
            viewerSection.classList.remove('active');
            currentRecordingId = null;
        }
        
        // Reload recordings list
        await loadRecordings();
        
    } catch (error) {
        console.error('Error deleting recording:', error);
        alert(`Error deleting recording: ${error.message}`);
    }
}


stopBtn.disabled = true;

// ============================================================================
// CDR Logs Functionality
// ============================================================================

// Initialize CDR viewer
document.addEventListener('DOMContentLoaded', () => {
    const refreshCDRBtn = document.getElementById('refreshCDRBtn');
    const clearCDRBtn = document.getElementById('clearCDRBtn');
    
    if (refreshCDRBtn) {
        refreshCDRBtn.addEventListener('click', loadCDRReports);
    }
    
    if (clearCDRBtn) {
        clearCDRBtn.addEventListener('click', clearCDRReports);
    }
    
    // Load CDR reports on page load
    loadCDRReports();
});

async function loadCDRReports() {
    try {
        console.log('Loading CDR reports from:', `${RECORDING_API_BASE}/cdr/reports`);
        const response = await fetch(`${RECORDING_API_BASE}/cdr/reports`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('CDR reports received:', data);
        console.log('Data type:', Array.isArray(data) ? 'array' : typeof data);
        console.log('Data length:', Array.isArray(data) ? data.length : 'N/A');
        
        // The API returns an array directly, not an object with reports property
        const reports = Array.isArray(data) ? data : [];
        updateCDRStats(reports);
        updateCDRTable(reports);
        
    } catch (error) {
        console.error('Error loading CDR reports:', error);
        const container = document.getElementById('cdrTableContainer');
        if (container) {
            container.innerHTML = `<div class="no-data">Error loading CDR reports: ${error.message}</div>`;
        }
    }
}

function updateCDRStats(reports) {
    console.log('Updating CDR stats with', reports.length, 'reports');
    const total = reports.length;
    const successful = reports.filter(r => !r.failure_occurred && !r.system_error).length;
    const failed = reports.filter(r => r.failure_occurred || r.system_error).length;
    
    document.getElementById('cdrStatTotal').textContent = total;
    document.getElementById('cdrStatOk').textContent = successful;
    document.getElementById('cdrStatErr').textContent = failed;
    
    if (reports.length > 0) {
        const lastReport = reports[0]; // Reports are in reverse order (newest first)
        const date = new Date(lastReport.received_at);
        document.getElementById('cdrStatLast').textContent = date.toLocaleTimeString();
    } else {
        document.getElementById('cdrStatLast').textContent = '—';
    }
}

function updateCDRTable(reports) {
    const container = document.getElementById('cdrTableContainer');
    console.log('Updating CDR table with', reports.length, 'reports');
    
    if (!reports || reports.length === 0) {
        console.log('No reports to display');
        container.innerHTML = `
            <div class="no-data">
                <div class="no-data-icon">📡</div>
                <div>No CDR reports received yet</div>
                <div style="margin-top: 0.5rem; font-size: 0.75rem;">Configure your voice runtime to send CDR webhooks</div>
            </div>
        `;
        return;
    }
    
    let tableHTML = `
        <table class="bx--data-table bx--data-table--compact">
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Transaction ID</th>
                    <th>Agent ID</th>
                    <th>Duration</th>
                    <th>Turns</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    reports.forEach((report, index) => {
        console.log(`Report ${index}:`, report);
        const time = new Date(report.received_at).toLocaleTimeString();
        const duration = report.milliseconds_elapsed ? `${(report.milliseconds_elapsed / 1000).toFixed(1)}s` : '—';
        const turns = report.turn_count || 0;
        const status = report.failure_occurred || report.system_error ?
            '<span style="color: #da1e28;">⚠️ Failed</span>' :
            '<span style="color: #24a148;">✓ Success</span>';
        
        tableHTML += `
            <tr class="cdr-row" data-report-id="${report.id}" style="cursor: pointer;">
                <td>${time}</td>
                <td style="font-family: 'IBM Plex Mono', monospace; font-size: 0.75rem;">${report.transaction_id || '—'}</td>
                <td style="font-family: 'IBM Plex Mono', monospace; font-size: 0.75rem;">${report.agent_id ? report.agent_id.substring(0, 8) + '...' : '—'}</td>
                <td>${duration}</td>
                <td>${turns}</td>
                <td>${status}</td>
            </tr>
        `;
    });
    
    tableHTML += `
            </tbody>
        </table>
    `;
    
    container.innerHTML = tableHTML;
    
    // Add click handlers to rows
    document.querySelectorAll('.cdr-row').forEach(row => {
        row.addEventListener('click', () => {
            const reportId = row.getAttribute('data-report-id');
            selectCDRReport(reportId);
        });
    });
}

async function selectCDRReport(reportId) {
    try {
        const response = await fetch(`${RECORDING_API_BASE}/cdr/reports/${reportId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const report = await response.json();
        
        // Show viewer section
        const viewerSection = document.getElementById('cdrViewerSection');
        viewerSection.classList.add('active');
        viewerSection.style.display = 'block';
        
        const viewerTitle = document.getElementById('cdrViewerTitle');
        viewerTitle.textContent = `CDR Report: ${reportId.substring(0, 8)}...`;
        
        const detailJson = document.getElementById('cdrDetailJson');
        detailJson.textContent = JSON.stringify(report, null, 2);
        
        // Highlight selected row
        document.querySelectorAll('.cdr-row').forEach(row => {
            row.style.backgroundColor = '';
        });
        const selectedRow = document.querySelector(`[data-report-id="${reportId}"]`);
        if (selectedRow) {
            selectedRow.style.backgroundColor = '#e0e0e0';
        }
        
    } catch (error) {
        console.error('Error loading CDR report:', error);
        alert(`Error loading CDR report: ${error.message}`);
    }
}

async function clearCDRReports() {
    const confirmed = await showConfirmModal(
        'Clear CDR Reports',
        'Are you sure you want to clear all CDR reports?\n\nThis action cannot be undone.'
    );
    
    if (!confirmed) {
        return;
    }
    
    try {
        const response = await fetch(`${RECORDING_API_BASE}/cdr/reports`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Reload the reports
        await loadCDRReports();
        
        // Hide viewer
        const viewerSection = document.getElementById('cdrViewerSection');
        viewerSection.classList.remove('active');
        viewerSection.style.display = 'none';
        
    } catch (error) {
        console.error('Error clearing CDR reports:', error);
        alert(`Error clearing CDR reports: ${error.message}`);
    }
}
