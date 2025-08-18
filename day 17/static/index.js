document.addEventListener('DOMContentLoaded', () => {
    // --- Transcription Elements ---
    const startBtn = document.getElementById('start-recording-btn');
    const stopBtn = document.getElementById('stop-recording-btn');
    const statusBox = document.getElementById('status-box');
    const transcriptResult = document.getElementById('transcription-result');

    // --- Global State ---
    let audioContext;
    let scriptProcessor;
    let microphoneStream;
    let ws;

    const startRecording = async () => {
        try {
            transcriptResult.textContent = "";
            statusBox.textContent = "Connecting...";

            // Use wss:// for secure connections in production
            const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
            ws = new WebSocket(`${wsProtocol}${window.location.host}/ws`);

            ws.onopen = async () => {
                try {
                    microphoneStream = await navigator.mediaDevices.getUserMedia({ audio: { sampleRate: 16000, channelCount: 1 } });
                    audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
                    const source = audioContext.createMediaStreamSource(microphoneStream);
                    scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);

                    scriptProcessor.onaudioprocess = (event) => {
                        if (ws.readyState !== WebSocket.OPEN) return;
                        const inputData = event.inputBuffer.getChannelData(0);
                        const pcmData = new Int16Array(inputData.length);
                        for (let i = 0; i < inputData.length; i++) {
                            pcmData[i] = Math.max(-1, Math.min(1, inputData[i])) * 0x7FFF;
                        }
                        ws.send(pcmData.buffer);
                    };

                    source.connect(scriptProcessor);
                    scriptProcessor.connect(audioContext.destination);

                    startBtn.disabled = true;
                    stopBtn.disabled = false;
                    statusBox.textContent = "🔴 Recording... Speak now!";
                    statusBox.classList.add('animate-pulse-slow');

                } catch (err) {
                    console.error('Microphone access error:', err);
                    statusBox.textContent = "Microphone permission denied or not available.";
                    ws.close(); // Close the WebSocket if microphone access fails
                }
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    // The main.py file sends a turn object, so we look for the 'transcript' key
                    if ("transcript" in data) {
                        transcriptResult.textContent = data.transcript;
                    }
                } catch (e) {
                    console.error("Failed to parse message:", event.data);
                }
            };

            ws.onclose = () => {
                console.log("WebSocket connection closed.");
                stopRecording();
            };

            ws.onerror = (err) => {
                console.error('WebSocket error:', err);
                statusBox.textContent = "Connection error.";
                stopRecording();
            };

        } catch (err) {
            console.error('General error:', err);
            statusBox.textContent = "Could not start recording.";
        }
    };

    const stopRecording = () => {
        if (scriptProcessor) scriptProcessor.disconnect();
        if (audioContext) audioContext.close();
        if (microphoneStream) microphoneStream.getTracks().forEach(track => track.stop());
        if (ws && ws.readyState === WebSocket.OPEN) ws.close();
        
        startBtn.disabled = false;
        stopBtn.disabled = true;
        statusBox.textContent = "Conversation ended.";
        statusBox.classList.remove('animate-pulse-slow');
    };

    startBtn.addEventListener('click', startRecording);
    stopBtn.addEventListener('click', stopRecording);
});