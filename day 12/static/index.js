document.addEventListener('DOMContentLoaded', () => {
    // --- Element Selectors ---
    // Elements for the revamped Dhwani Voice UI
    const agentVoiceSelect = document.getElementById('agent-voice-select');
    const aetherRecordBtn = document.getElementById('aether-record-btn'); // Note: ID from previous step is reused
    const agentStatus = document.getElementById('agent-status');
    const agentClearBtn = document.getElementById('agent-clear-btn');
    const chatHistoryContainer = document.getElementById('chat-history-container');
    const emptyChatMessage = document.getElementById('empty-chat-message');
    const agentErrorBox = document.getElementById('agent-error-box');
    const agentErrorText = document.getElementById('agent-error-text');
    const audioPlaybackContainer = document.getElementById('audio-playback-container');

    // Hidden functional buttons
    const agentStartBtn = document.getElementById('agent-start-btn');
    const agentStopBtn = document.getElementById('agent-stop-btn');


    // --- State Variables ---
    let agentMediaRecorder;
    let agentAudioChunks = [];
    let isAgentRecording = false;
    let sessionId = null;
    
    // --- SVG Icons for the record button ---
    const micIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/></svg>`;
    const stopIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1"><rect width="8" height="8" x="8" y="8" rx="1"/></svg>`;


    // --- Helper Functions ---
    const showAgentError = (message) => {
        agentErrorText.textContent = message;
        agentErrorBox.classList.remove('hidden');
    };

    const hideAgentError = () => {
        agentErrorBox.classList.add('hidden');
    };

    const fetchVoices = async () => {
        try {
            const response = await fetch('/voices');
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to fetch voices.');
            }
            const voices = await response.json();
            
            agentVoiceSelect.innerHTML = '';

            const defaultVoiceId = "en-US-katie";
            voices.forEach(voice => {
                if (!voice.displayName.includes('child')) { // Filter out child voices for cleaner list
                    const option = document.createElement('option');
                    option.value = voice.voiceId;
                    option.textContent = `${voice.displayName} (${voice.gender})`;
                    if (voice.voiceId === defaultVoiceId) option.selected = true;
                    agentVoiceSelect.appendChild(option);
                }
            });
        } catch (error) {
            console.error('Error fetching voices:', error);
            showAgentError(`Could not load voices.`);
        }
    };
    
    // --- AI Voice Chat Logic ---
    const renderChatHistory = (history) => {
        chatHistoryContainer.innerHTML = '';
        if (!history || history.length === 0) {
            emptyChatMessage.classList.remove('hidden');
            return;
        }
        emptyChatMessage.classList.add('hidden');
        history.forEach((message) => {
            const turnContainer = document.createElement('div');
            if (message.role === 'user') {
                turnContainer.innerHTML = `<p><span class="font-bold text-gray-300">You:</span> <span class="text-gray-200">${message.text}</span></p>`;
            } else if (message.role === 'model') {
                turnContainer.innerHTML = `<p><span class="font-bold text-purple-400">Dhwani:</span> <span class="text-gray-200">${message.text}</span></p>`;
            }
            chatHistoryContainer.appendChild(turnContainer);
        });
        chatHistoryContainer.scrollTop = chatHistoryContainer.scrollHeight;
    };

    const initSession = async () => {
        const urlParams = new URLSearchParams(window.location.search);
        sessionId = urlParams.get('session_id');
        if (!sessionId) {
            sessionId = crypto.randomUUID();
            window.history.replaceState({ path: `/?session_id=${sessionId}` }, '', `/?session_id=${sessionId}`);
            renderChatHistory([]);
        } else {
            try {
                const response = await fetch(`/agent/chat/${sessionId}`);
                if (response.ok) {
                    const data = await response.json();
                    renderChatHistory(data.history);
                } else {
                   throw new Error("Failed to load chat history.");
                }
            } catch (error) {
                showAgentError("Could not load history.");
                console.error(error);
            }
        }
    };

    const clearAgentChat = async () => {
        if (!sessionId) return;
        try {
            await fetch(`/agent/chat/${sessionId}`, { method: 'DELETE' });
            renderChatHistory([]);
            agentStatus.textContent = 'Ready';
            hideAgentError();
            sessionId = crypto.randomUUID();
            window.history.replaceState({ path: `/?session_id=${sessionId}` }, '', `/?session_id=${sessionId}`);
        } catch (error) {
            showAgentError("Error clearing chat.");
        }
    };

    const startAgentRecording = async () => {
        if (isAgentRecording) return;
        hideAgentError();
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            agentMediaRecorder = new MediaRecorder(stream);
            agentAudioChunks = [];
            isAgentRecording = true;
            agentMediaRecorder.addEventListener('dataavailable', e => agentAudioChunks.push(e.data));
            
            agentMediaRecorder.addEventListener('stop', async () => {
                const audioBlob = new Blob(agentAudioChunks, { type: 'audio/webm' });
                stream.getTracks().forEach(track => track.stop());
                isAgentRecording = false;

                if (audioBlob.size < 500) {
                    agentStatus.textContent = 'Did not hear anything. Try again.';
                    aetherRecordBtn.disabled = false;
                    aetherRecordBtn.innerHTML = micIcon;
                    aetherRecordBtn.classList.remove('is-recording');
                    return;
                }

                agentStatus.textContent = 'Thinking...';
                aetherRecordBtn.disabled = true;
                aetherRecordBtn.classList.remove('is-recording');

                const formData = new FormData();
                formData.append('audio_file', audioBlob, "user_audio.webm");
                formData.append('voiceId', agentVoiceSelect.value);

                try {
                    const response = await fetch(`/agent/chat/${sessionId}`, { method: 'POST', body: formData });
                    const data = await response.json(); 

                    renderChatHistory(data.history);
                    
                    const finishInteraction = () => {
                        agentStatus.textContent = 'Ready';
                        aetherRecordBtn.disabled = false;
                        aetherRecordBtn.innerHTML = micIcon;
                    };

                    if (data.audio_url) {
                        const audio = new Audio(data.audio_url);
                        audioPlaybackContainer.appendChild(audio);
                        audio.play();
                        agentStatus.textContent = 'Playing response...';
                        audio.onended = () => {
                            finishInteraction();
                            audio.remove();
                        };
                         audio.onerror = () => {
                            finishInteraction();
                            audio.remove();
                        };
                    } else {
                        finishInteraction();
                    }
                    
                    if (!response.ok) {
                        showAgentError(data.error || 'An unknown error occurred.');
                    }

                } catch (error) {
                    showAgentError(`Network error: ${error.message}`);
                    agentStatus.textContent = 'Connection Error';
                    aetherRecordBtn.disabled = false;
                    aetherRecordBtn.innerHTML = micIcon;
                }
            });

            agentMediaRecorder.start();
            agentStatus.textContent = 'Listening...';
            aetherRecordBtn.innerHTML = stopIcon;
            aetherRecordBtn.classList.add('is-recording');

        } catch (error) {
            showAgentError('Microphone access denied. Please allow microphone permissions in your browser.');
            agentStatus.textContent = 'Mic Error';
            console.error(error);
        }
    };

    const stopAgentRecording = () => {
        if (agentMediaRecorder?.state === 'recording') {
            agentMediaRecorder.stop();
            agentStatus.textContent = 'Processing...';
            aetherRecordBtn.disabled = true;
            aetherRecordBtn.classList.remove('is-recording');
        }
    };

    // --- Initializations and Event Listeners ---
    fetchVoices();
    initSession();
    if(aetherRecordBtn) aetherRecordBtn.innerHTML = micIcon; // Set initial icon

    // Listener for the main record button
    aetherRecordBtn?.addEventListener('click', () => {
        if (isAgentRecording) {
            stopAgentRecording();
        } else {
            startAgentRecording();
        }
    });
    
    // Listener for the clear chat button
    agentClearBtn?.addEventListener('click', clearAgentChat);
});