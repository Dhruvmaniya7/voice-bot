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
    let audioChunkIndex = 0;

    const recordBtn = document.getElementById("recordBtn");
    const statusDisplay = document.getElementById("statusDisplay");
    const chatDisplay = document.getElementById("chatDisplay");
    const chatContainer = document.getElementById("chatContainer");
    const clearBtnContainer = document.getElementById("clearBtnContainer");
    const clearBtn = document.getElementById("clearBtn");

    const stopCurrentPlayback = () => {
        console.log("🤫 Diva: Oops, you interrupted me! Stopping my current response.");
        audioQueue = []; 
        isPlaying = false;
        
        if (audioContext && audioContext.state !== 'closed') {
            audioContext.close();
            audioContext = null;
        }
    };

    const playNextChunk = () => {
        if (!audioQueue.length || !audioContext || audioContext.state === "closed") {
            if (isPlaying) {
                console.log("✅ Diva: That's everything from me for now! All audio chunks have been played.");
            }
            isPlaying = false;
            return;
        }
        
        console.log(`➡️ Diva: Playing audio chunk. ${audioQueue.length - 1} remaining in the queue.`);
        isPlaying = true;
        const chunk = audioQueue.shift(); 
        
        audioContext.decodeAudioData(chunk,
            (buffer) => {
                const sourceNode = audioContext.createBufferSource();
                sourceNode.buffer = buffer;
                sourceNode.connect(audioContext.destination);
                sourceNode.start();

                sourceNode.onended = () => {
                    playNextChunk();
                };
            },
            (error) => {
                console.error("Error decoding audio data:", error);
                playNextChunk();
            }
        );
    };

    const startRecording = async () => {
        console.log("🎤 Diva: Let's talk! Initializing the audio session.");
        if (!navigator.mediaDevices?.getUserMedia) {
            alert("Audio recording is not supported in this browser.");
            return;
        }
        try {
            if (!audioContext || audioContext.state === 'closed') {
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
            }
            if (audioContext.state === 'suspended') {
                await audioContext.resume();
            }
        } catch (error) {
            alert("Could not initialize audio. Your browser might not be supported.");
            console.error("Error initializing AudioContext:", error);
            return;
        }

        isRecording = true;
        updateUIForRecording(true);

        try {
            const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
            socket = new WebSocket(`${wsProtocol}//${window.location.host}/ws`);

            socket.onopen = async () => {
                console.log("🔌 Diva: WebSocket connection established. I'm all ears!");
                heartbeatInterval = setInterval(() => {
                    if (socket?.readyState === WebSocket.OPEN) {
                        socket.send(JSON.stringify({ type: "ping" }));
                    }
                }, 25000);

                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    source = audioContext.createMediaStreamSource(stream);
                    processor = audioContext.createScriptProcessor(4096, 1, 1);

                    processor.onaudioprocess = (event) => {
                        const inputData = event.inputBuffer.getChannelData(0);
                        const targetSampleRate = 16000;
                        const sourceSampleRate = audioContext.sampleRate;
                        const ratio = sourceSampleRate / targetSampleRate;
                        const newLength = Math.floor(inputData.length / ratio);
                        const downsampledData = new Float32Array(newLength);
                        for (let i = 0; i < newLength; i++) {
                            downsampledData[i] = inputData[Math.floor(i * ratio)];
                        }
                        const pcmData = new Int16Array(downsampledData.length);
                        for (let i = 0; i < pcmData.length; i++) {
                            const sample = Math.max(-1, Math.min(1, downsampledData[i]));
                            pcmData[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
                        }
                        if (socket?.readyState === WebSocket.OPEN) {
                            socket.send(pcmData.buffer);
                        }
                    };

                    source.connect(processor);
                    processor.connect(audioContext.destination);
                    recordBtn.mediaStream = stream;
                } catch (micError) {
                    alert("Could not access the microphone. Please check your browser permissions.");
                    console.error("Microphone access error:", micError.name, micError.message);
                    stopRecording();
                }
            };

            socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    
                    if (data.type !== 'audio' && data.type !== 'pong') {
                        console.log(`📬 Diva: Message from server -> Type: ${data.type}`, data);
                    }

                    switch (data.type) {
                        case "pong":
                            break;
                        case "status":
                            statusDisplay.textContent = data.message;
                            break;
                        case "transcription":
                            if (data.end_of_turn && data.text) {
                                addToChatLog(data.text, 'user');
                                statusDisplay.textContent = "Diva is thinking...";
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
                            statusDisplay.textContent = "Receiving audio response...";
                            console.log("🎶 Diva: Okay, I've started receiving the audio stream. Getting ready to speak!");
                            audioQueue = [];
                            audioChunkIndex = 0;
                            break;
                        case "audio_interrupt":
                            stopCurrentPlayback();
                            statusDisplay.textContent = "Interrupted. Listening...";
                            break;
                        case "audio": {
                            if (data.data) {
                                const audioData = atob(data.data);
                                const byteNumbers = new Array(audioData.length);
                                for (let i = 0; i < audioData.length; i++) {
                                    byteNumbers[i] = audioData.charCodeAt(i);
                                }
                                const byteArray = new Uint8Array(byteNumbers);
                                
                                console.log(`🎵 Diva: Processing audio chunk ${audioChunkIndex + 1}. Size: ${byteArray.buffer.byteLength} bytes. Queueing it up!`);
                                audioChunkIndex++;
                                
                                audioQueue.push(byteArray.buffer);
                                
                                if (!isPlaying) {
                                    console.log(`▶️ Diva: Let's play the first chunk! I have ${audioQueue.length} pieces of my response ready.`);
                                    playNextChunk();
                                }
                            }
                            break;
                        }
                        case "audio_end":
                            statusDisplay.textContent = "Audio playback finished.";
                            console.log("🏁 Diva: The server has confirmed the audio stream is complete.");
                            break;
                        case "error":
                            statusDisplay.textContent = `Error: ${data.message}`;
                            statusDisplay.classList.add("text-red-400");
                            break;
                    }
                } catch (err) { console.error("Error parsing message:", err); }
            };

            socket.onclose = () => {
                statusDisplay.textContent = "Connection closed.";
                console.log("💔 Diva: Connection closed. Hope we can talk again soon!");
                stopRecording(false);
            };
            socket.onerror = (error) => {
                console.error("WebSocket Error:", error);
                statusDisplay.textContent = "A connection error occurred.";
                statusDisplay.classList.add("text-red-400");
                stopRecording();
            };

        } catch (err) {
            alert("Failed to start the recording session.");
            console.error("Session start error:", err);
            stopRecording();
        }
    };
    
    const stopRecording = (sendEOF = true) => {
        if (!isRecording) return;
        console.log("🛑 Diva: Recording stopped. Closing the connection now. Talk to you later!");
        isRecording = false;

        audioQueue = [];
        isPlaying = false;

        if (heartbeatInterval) {
            clearInterval(heartbeatInterval);
            heartbeatInterval = null;
        }

        if (processor) processor.disconnect();
        if (source) source.disconnect();
        if (recordBtn.mediaStream) {
            recordBtn.mediaStream.getTracks().forEach(track => track.stop());
            recordBtn.mediaStream = null;
        }

        if (audioContext) {
            audioContext.close();
            audioContext = null;
        }

        if (socket?.readyState === WebSocket.OPEN) {
            socket.close();
        }
        socket = null;
        updateUIForRecording(false);
    };

    const updateUIForRecording = (isRec) => {
        if (isRec) {
            recordBtn.classList.add("recording", "bg-red-600", "hover:bg-red-700");
            recordBtn.classList.remove("bg-violet-600", "hover:bg-violet-700");
            statusDisplay.textContent = "Connecting...";
            chatDisplay.classList.remove("hidden");
            chatContainer.innerHTML = '';
            clearBtnContainer.classList.add("hidden");
        } else {
            recordBtn.classList.remove("recording", "bg-red-600", "hover:bg-red-700");
            recordBtn.classList.add("bg-violet-600", "hover:bg-violet-700");
            statusDisplay.textContent = "Ready";
            statusDisplay.classList.remove("text-red-400");
        }
    };

    const addToChatLog = (text, sender) => {
        const messageElement = document.createElement("div");
        messageElement.className = 'chat-message';

        const prefixSpan = document.createElement('span');
        const contentSpan = document.createElement('span');
        contentSpan.className = 'message-content';

        if (sender === 'user') {
            prefixSpan.className = 'user-prefix';
            prefixSpan.textContent = 'You: ';
        } else {
            prefixSpan.className = 'ai-prefix';
            // Changed name back to Diva
            prefixSpan.textContent = 'Diva: ';
        }
        
        contentSpan.textContent = text;
        
        messageElement.appendChild(prefixSpan);
        messageElement.appendChild(contentSpan);
        chatContainer.appendChild(messageElement);

        if (chatContainer.children.length > 0) {
            clearBtnContainer.classList.remove("hidden");
        }
        chatContainer.scrollTop = chatContainer.scrollHeight;
        
        return contentSpan; 
    };

    clearBtn.addEventListener("click", () => {
        chatContainer.innerHTML = '';
        clearBtnContainer.classList.add("hidden");
    });

    recordBtn.addEventListener("click", () => {
        isRecording ? stopRecording() : startRecording();
    });

    window.addEventListener('beforeunload', () => {
        if (isRecording) stopRecording();
    });
});