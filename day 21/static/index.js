document.addEventListener("DOMContentLoaded", () => {
    let audioContext = null;
    let source = null;
    let processor = null;
    let isRecording = false;
    let socket = null;
    let audioChunks = []; // Array to store incoming audio chunks

    const recordBtn = document.getElementById("recordBtn");
    const statusDisplay = document.getElementById("statusDisplay");
    const transcriptionDisplay = document.getElementById("transcriptionDisplay");
    const transcriptionHistory = document.getElementById("transcriptionHistory");
    const clearBtnContainer = document.getElementById("clearBtnContainer");
    const clearBtn = document.getElementById("clearBtn");
    const responseAudio = document.getElementById("responseAudio"); // Get the audio element

    const startRecording = async () => {
        if (!navigator.mediaDevices?.getUserMedia) {
            alert("Audio recording is not supported in this browser.");
            return;
        }

        isRecording = true;
        audioChunks = []; // Clear chunks from previous session
        updateUIForRecording(true);

        try {
            const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
            socket = new WebSocket(`${wsProtocol}//${window.location.host}/ws`);

            socket.onopen = async () => {
                statusDisplay.textContent = "Connected. Speak now...";
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
                    source = audioContext.createMediaStreamSource(stream);
                    processor = audioContext.createScriptProcessor(4096, 1, 1);

                    processor.onaudioprocess = (event) => {
                        const inputData = event.inputBuffer.getChannelData(0);
                        const pcmData = new Int16Array(inputData.length);
                        for (let i = 0; i < inputData.length; i++) {
                            const sample = Math.max(-1, Math.min(1, inputData[i]));
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
                    console.error("Microphone error:", micError);
                    stopRecording();
                }
            };


            socket.onmessage = (event) => {
                let a = 0;
                try {
                    const data = JSON.parse(event.data);
                    switch (data.type) {
                        case "transcription":
                            if (data.end_of_turn && data.text) {
                                addToTranscriptionHistory(data.text);
                                statusDisplay.textContent = "Turn detected. Generating response...";
                            }
                            break;
                        // --- NEW: HANDLE INCOMING AUDIO DATA ---
                        case "audio":
                            console.log("✅ Audio chunk received from server.");
                            if(data.data) {
                                audioChunks.push(data.data);
                            }
                            break;
                        // --- NEW: HANDLE END OF AUDIO STREAM ---
                        case "audio_end":
                            a++;
                            console.log("▶️ All audio chunks received. Playing audio. Count:", a);
                            if (audioChunks.length > 0) {
                                const fullBase64 = audioChunks.join('');
                                
                                // Convert base64 to a Blob
                                const byteCharacters = atob(fullBase64);
                                const byteNumbers = new Array(byteCharacters.length);
                                for (let i = 0; i < byteCharacters.length; i++) {
                                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                                }
                                const byteArray = new Uint8Array(byteNumbers);
                                const blob = new Blob([byteArray], {type: 'audio/wav'});

                                const audioUrl = URL.createObjectURL(blob);
                                responseAudio.src = audioUrl;
                                responseAudio.play();
                                
                                audioChunks = []; // Clear the chunks for the next response
                                
                                responseAudio.onended = () => {
                                      if(isRecording) {
                                          statusDisplay.textContent = "Listening for the next turn...";
                                      }
                                }
                            }
                            break;
                        case "error":
                            statusDisplay.textContent = `Error: ${data.message}`;
                            statusDisplay.classList.add("text-red-400");
                            break;
                        case "status":
                            statusDisplay.textContent = data.message;
                            break;
                    }
                } catch (err) {
                    console.error("Error parsing message:", err);
                }
            };

            socket.onclose = () => {
                statusDisplay.textContent = "Connection closed.";
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
        isRecording = false;
        updateUIForRecording(false);

        if (processor) processor.disconnect();
        if (source) source.disconnect();
        if (audioContext) audioContext.close();
        if (recordBtn.mediaStream) {
            recordBtn.mediaStream.getTracks().forEach(track => track.stop());
            recordBtn.mediaStream = null;
        }
        
        // CORRECTED CODE BLOCK
        if (socket?.readyState === WebSocket.OPEN) {
            // The "socket.send('EOF')" line has been removed.
            socket.close();
        }
        socket = null;
    };

    const updateUIForRecording = (isRec) => {
        if (isRec) {
            recordBtn.classList.add("recording", "bg-red-600", "hover:bg-red-700");
            recordBtn.classList.remove("bg-violet-600", "hover:bg-violet-700");
            statusDisplay.textContent = "Connecting...";
            transcriptionDisplay.classList.remove("hidden");
            transcriptionHistory.innerHTML = '';
            clearBtnContainer.classList.add("hidden");
        } else {
            recordBtn.classList.remove("recording", "bg-red-600", "hover:bg-red-700");
            recordBtn.classList.add("bg-violet-600", "hover:bg-violet-700");
            statusDisplay.textContent = "Ready";
            statusDisplay.classList.remove("text-red-400");
        }
    };

    const addToTranscriptionHistory = (text) => {
        const historyItem = document.createElement("div");
        historyItem.className = "p-2 text-lg transcript-item";
        historyItem.textContent = text;
        historyItem.classList.add("latest");
        const lastItem = transcriptionHistory.lastElementChild;
        if (lastItem) {
            lastItem.classList.remove("latest");
        }
        transcriptionHistory.appendChild(historyItem);
        if (clearBtnContainer.classList.contains("hidden")) {
            clearBtnContainer.classList.remove("hidden");
        }
        transcriptionHistory.scrollTop = transcriptionHistory.scrollHeight;
    };

    clearBtn.addEventListener("click", () => {
        transcriptionHistory.innerHTML = '';
        clearBtnContainer.classList.add("hidden");
    });

    recordBtn.addEventListener("click", () => {
        isRecording ? stopRecording() : startRecording();
    });

    window.addEventListener('beforeunload', () => {
        if (isRecording) stopRecording();
    });
});