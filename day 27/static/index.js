document.addEventListener("DOMContentLoaded", () => {
    let audioContext = null;
    let source = null;
    let processor = null;
    let isRecording = false;
    let socket = null;
    let heartbeatInterval = null;

    let audioQueue = [];
    let isPlaying = false;
    let currentAiMessageContentElement = null;
    let currentAudioSource = null;

    const recordBtn = document.getElementById("recordBtn");
    const statusDisplay = document.getElementById("statusDisplay");
    const chatDisplay = document.getElementById("chatDisplay");
    const chatContainer = document.getElementById("chatContainer");
    const clearBtnContainer = document.getElementById("clearBtnContainer");
    const clearBtn = document.getElementById("clearBtn");
    const settingsBtn = document.getElementById("settingsBtn");
    const sidebar = document.getElementById("apiConfigSidebar");
    const overlay = document.getElementById("overlay");
    const saveConfigBtn = document.getElementById("saveConfigBtn");
    const geminiKeyInput = document.getElementById("geminiKey");
    const assemblyaiKeyInput = document.getElementById("assemblyaiKey");
    const murfaiKeyInput = document.getElementById("murfaiKey");
    const weatherapiKeyInput = document.getElementById("weatherapiKey");
    const tavilyaiKeyInput = document.getElementById("tavilyaiKey");
    const notificationContainer = document.getElementById("notificationContainer");

    const showNotification = (message, isError = false) => {
        const toast = document.createElement('div');
        toast.className = `notification-toast ${isError ? 'error' : 'success'}`;
        toast.textContent = message;
        notificationContainer.appendChild(toast);
        setTimeout(() => toast.classList.add('show'), 10);
        setTimeout(() => {
            toast.classList.remove('show');
            toast.addEventListener('transitionend', () => toast.remove());
        }, 5000);
    };

    const toggleSidebar = (show) => {
        sidebar.classList.toggle('show', show);
        overlay.classList.toggle('show', show);
    };

    const saveApiKeys = () => {
        localStorage.setItem("geminiKey", geminiKeyInput.value);
        localStorage.setItem("assemblyaiKey", assemblyaiKeyInput.value);
        localStorage.setItem("murfaiKey", murfaiKeyInput.value);
        localStorage.setItem("weatherapiKey", weatherapiKeyInput.value);
        localStorage.setItem("tavilyaiKey", tavilyaiKeyInput.value);
        
        // --- FINAL FIX: REMOVED FORCED RELOAD ---
        // The configuration will now be applied on the next connection without a page refresh.
        showNotification("Configuration saved!", false);
        toggleSidebar(false);
    };

    const loadApiKeys = () => {
        geminiKeyInput.value = localStorage.getItem("geminiKey") || "";
        assemblyaiKeyInput.value = localStorage.getItem("assemblyaiKey") || "";
        murfaiKeyInput.value = localStorage.getItem("murfaiKey") || "";
        weatherapiKeyInput.value = localStorage.getItem("weatherapiKey") || "";
        tavilyaiKeyInput.value = localStorage.getItem("tavilyaiKey") || "";
    };

    settingsBtn.addEventListener('click', () => toggleSidebar(true));
    overlay.addEventListener('click', () => toggleSidebar(false));
    saveConfigBtn.addEventListener('click', saveApiKeys);
    
    loadApiKeys();

    const stopCurrentPlayback = () => {
        if (currentAudioSource) {
            currentAudioSource.stop();
            currentAudioSource = null;
        }
        audioQueue = [];
        isPlaying = false;
    };

    const playNextChunk = () => {
        if (!audioQueue.length || !audioContext || audioContext.state === "closed") {
            isPlaying = false;
            return;
        }
        isPlaying = true;
        const chunk = audioQueue.shift();
        audioContext.decodeAudioData(chunk, (buffer) => {
            const sourceNode = audioContext.createBufferSource();
            sourceNode.buffer = buffer;
            sourceNode.connect(audioContext.destination);
            sourceNode.start();
            currentAudioSource = sourceNode;
            sourceNode.onended = () => { currentAudioSource = null; playNextChunk(); };
        }, (error) => { console.error("Error decoding audio data:", error); playNextChunk(); });
    };

    const startRecording = async () => {
        if (isRecording) return;
        console.log("Starting recording...");

        try {
            audioContext = audioContext || new (window.AudioContext || window.webkitAudioContext)();
            if (audioContext.state === 'suspended') await audioContext.resume();
        } catch (e) { alert("Web Audio API is not supported in this browser."); return; }

        isRecording = true;
        updateUIForRecording(true);
        const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        socket = new WebSocket(`${wsProtocol}//${window.location.host}/ws`);

        socket.onopen = async () => {
            console.log("WebSocket connection established. Sending configuration.");
            const apiKeys = {
                gemini: localStorage.getItem("geminiKey"),
                assemblyai: localStorage.getItem("assemblyaiKey"),
                murf: localStorage.getItem("murfaiKey"),
                weather: localStorage.getItem("weatherapiKey"),
                tavily: localStorage.getItem("tavilyaiKey")
            };
            socket.send(JSON.stringify({ type: "config", keys: apiKeys }));
            
            heartbeatInterval = setInterval(() => { 
                if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: "ping" })); 
            }, 15000);

            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                source = audioContext.createMediaStreamSource(stream);
                processor = audioContext.createScriptProcessor(4096, 1, 1);
                
                processor.onaudioprocess = (event) => {
                    if (!isRecording) return; 

                    const inputData = event.inputBuffer.getChannelData(0);
                    const targetSampleRate = 16000;
                    const ratio = audioContext.sampleRate / targetSampleRate;
                    const newLength = Math.floor(inputData.length / ratio);
                    const downsampledData = new Float32Array(newLength);
                    for (let i = 0; i < newLength; i++) { downsampledData[i] = inputData[Math.floor(i * ratio)]; }
                    const pcmData = new Int16Array(downsampledData.length);
                    for (let i = 0; i < pcmData.length; i++) {
                        const sample = Math.max(-1, Math.min(1, downsampledData[i]));
                        pcmData[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
                    }
                    if (socket?.readyState === WebSocket.OPEN) socket.send(pcmData.buffer);
                };
                
                source.connect(processor);
                processor.connect(audioContext.destination);
                recordBtn.mediaStream = stream;
            } catch (micError) {
                alert("Could not access microphone. Please grant permission and try again.");
                console.error("Microphone access error:", micError);
                await stopRecording();
            }
        };

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'pong') return;
            console.log("RECEIVED MESSAGE:", data);
            switch (data.type) {
                case "status":
                    statusDisplay.textContent = data.message;
                    break;
                case "transcription":
                    if (data.end_of_turn && data.text) {
                        addToChatLog(data.text, 'user');
                        statusDisplay.textContent = "Diva is pondering the quest...";
                        currentAiMessageContentElement = null;
                    }
                    break;
                case "llm_chunk":
                    if (data.data) {
                        if (!currentAiMessageContentElement) {
                            currentAiMessageContentElement = addToChatLog("", 'ai');
                        }
                        currentAiMessageContentElement.textContent += data.data;
                        chatContainer.scrollTop = chatContainer.scrollHeight;
                    }
                    break;
                case "audio_start":
                    stopCurrentPlayback();
                    statusDisplay.textContent = "Receiving Diva's transmission...";
                    break;
                case "start_timer":
                    setTimeout(() => {
                        const popup = document.createElement('div');
                        popup.className = 'notification-popup show';
                        popup.textContent = '😎 Chronos Charm Complete!';
                        document.body.appendChild(popup);
                        try { new Audio('/static/notification.mp3').play(); } catch(e) { console.error("Chime audio failed", e); }
                        try { new Audio('/static/timer_complete.mp3').play(); } catch(e) { console.error("Voice line failed", e); }
                        
                        setTimeout(() => {
                            popup.classList.remove('show');
                            popup.addEventListener('transitionend', () => popup.remove());
                        }, 4000);
                    }, data.duration_seconds * 1000);
                    break;
                case "audio":
                    if (data.data) {
                        const audioData = atob(data.data);
                        const byteNumbers = new Array(audioData.length);
                        for (let i = 0; i < audioData.length; i++) byteNumbers[i] = audioData.charCodeAt(i);
                        const byteArray = new Uint8Array(byteNumbers);
                        audioQueue.push(byteArray.buffer);
                        if (!isPlaying) playNextChunk();
                    }
                    break;
                case "audio_end":
                    statusDisplay.textContent = "Diva's transmission is complete.";
                    break;
                case "error":
                    showNotification(data.message, true);
                    statusDisplay.textContent = "An error occurred. Please check the notifications.";
                    stopRecording();
                    break;
            }
        };
        socket.onclose = () => { console.log("WebSocket connection closed."); stopRecording(false); };
        socket.onerror = (error) => { console.error("WebSocket Error:", error); stopRecording(); };
    };

    const stopRecording = async (shouldUpdateStatus = true) => {
        if (!isRecording) return;
        console.log("Stopping recording.");
        isRecording = false;
        stopCurrentPlayback();
        if (heartbeatInterval) clearInterval(heartbeatInterval);
        if (processor) {
            processor.disconnect();
            processor.onaudioprocess = null;
            processor = null;
        }
        if (source) {
            source.disconnect();
            source = null;
        }
        if (recordBtn.mediaStream) recordBtn.mediaStream.getTracks().forEach(track => track.stop());
        if (socket?.readyState === WebSocket.OPEN) socket.close();
        socket = null;
        updateUIForRecording(false, shouldUpdateStatus);
    };

    const updateUIForRecording = (isRec, shouldUpdateStatus = true) => {
        if (isRec) {
            recordBtn.classList.add("recording", "bg-red-600", "hover:bg-red-700");
            recordBtn.classList.remove("bg-violet-600", "hover:bg-violet-700");
            statusDisplay.textContent = "Establishing connection...";
            chatDisplay.classList.remove("hidden");
        } else {
            recordBtn.classList.remove("recording", "bg-red-600", "hover:bg-red-700");
            recordBtn.classList.add("bg-violet-600", "hover:bg-violet-700");
            if (shouldUpdateStatus) {
                statusDisplay.textContent = "Ready for a new quest!";
            }
            statusDisplay.classList.remove("text-red-400");
        }
    };

    const addToChatLog = (text, sender) => {
        const messageElement = document.createElement("div");
        messageElement.className = 'chat-message';
        const prefixSpan = document.createElement('span');
        const contentSpan = document.createElement('span');
        contentSpan.className = 'message-content';
        prefixSpan.className = sender === 'user' ? 'user-prefix' : 'ai-prefix';
        prefixSpan.textContent = sender === 'user' ? 'Explorer: ' : 'Diva: ';
        contentSpan.textContent = text;
        messageElement.append(prefixSpan, contentSpan);
        chatContainer.appendChild(messageElement);
        if (chatContainer.children.length > 0) clearBtnContainer.classList.remove("hidden");
        chatContainer.scrollTop = chatContainer.scrollHeight;
        return contentSpan;
    };

    clearBtn.addEventListener("click", () => { chatContainer.innerHTML = ''; clearBtnContainer.classList.add("hidden"); });
    recordBtn.addEventListener("click", () => { if (isRecording) stopRecording(); else startRecording(); });
    window.addEventListener('beforeunload', () => { if (isRecording) stopRecording(); });
});