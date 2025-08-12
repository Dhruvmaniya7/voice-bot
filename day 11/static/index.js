document.addEventListener('DOMContentLoaded', () => {
    // --- Element Selectors ---
    // Text-to-Speech
    const ttsForm = document.getElementById('tts-form');
    const textInput = document.getElementById('text-input');
    const voiceSelect = document.getElementById('voice-select');
    const generateButton = document.getElementById('generate-button');
    const loadingIndicator = document.getElementById('loading-indicator');
    const messageBox = document.getElementById('message-box');
    const audioPlayerContainer = document.getElementById('audio-player-container');
    const audioPlayer = document.getElementById('audio-player');

    // Echo Bot
    const llmStartRecordingBtn = document.getElementById('llm-start-recording-btn');
    const llmStopRecordingBtn = document.getElementById('llm-stop-recording-btn');
    const llmRecordingStatus = document.getElementById('llm-recording-status');
    const llmLoadingIndicator = document.getElementById('llm-loading-indicator');
    const llmTranscriptionResult = document.getElementById('llm-transcription-result');
    const llmTranscriptionContainer = document.getElementById('llm-transcription-container');
    const llmAudioContainer = document.getElementById('llm-audio-container');
    const llmAudioPlayer = document.getElementById('llm-audio-player');

    // AI Voice Chat
    const agentStartBtn = document.getElementById('agent-start-btn');
    const agentStopBtn = document.getElementById('agent-stop-btn');
    const agentStatus = document.getElementById('agent-status');
    const agentClearBtn = document.getElementById('agent-clear-btn');
    const chatHistoryContainer = document.getElementById('chat-history-container');
    const emptyChatMessage = document.getElementById('empty-chat-message');
    // New selectors for the error box
    const agentErrorBox = document.getElementById('agent-error-box');
    const agentErrorText = document.getElementById('agent-error-text');


    // --- State Variables ---
    let mediaRecorder;
    let audioChunks = [];
    let agentMediaRecorder;
    let agentAudioChunks = [];
    let isAgentRecording = false;
    let sessionId = null;

    // --- Helper Functions ---
    const showMessage = (message, type = 'success') => {
        messageBox.textContent = message;
        messageBox.className = 'p-4 rounded-lg text-center font-semibold mb-4';
        if (type === 'success') {
            messageBox.classList.add('bg-green-900', 'text-green-300');
        } else if (type === 'error') {
            messageBox.classList.add('bg-red-900', 'text-red-300');
        }
        messageBox.classList.remove('hidden');
    };
    
    // New helper functions for the agent error box
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
            voiceSelect.innerHTML = '';
            const defaultVoiceId = "en-US-katie";
            voices.forEach(voice => {
                const option = document.createElement('option');
                option.value = voice.voiceId;
                option.textContent = `${voice.displayName} (${voice.gender}, ${voice.locale})`;
                if (voice.voiceId === defaultVoiceId) option.selected = true;
                voiceSelect.appendChild(option);
            });
        } catch (error) {
            console.error('Error fetching voices:', error);
            showMessage(`Could not load voices: ${error.message}`, 'error');
        }
    };

    // --- Text-to-Speech Logic (Unchanged from your original) ---
    ttsForm?.addEventListener('submit', async (event) => {
        event.preventDefault();
        const text = textInput.value.trim();
        if (!text) {
            showMessage("Please enter some text.", "error");
            return;
        }
        loadingIndicator.classList.remove('hidden');
        generateButton.disabled = true;
        generateButton.textContent = 'Generating...';
        messageBox.classList.add('hidden');
        audioPlayerContainer.classList.add('hidden');

        try {
            const formData = new FormData();
            formData.append('text', text);
            formData.append('voiceId', voiceSelect.value);
            const response = await fetch('/tts', { method: 'POST', body: formData });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.details || data.error || 'TTS generation failed.');
            }
            audioPlayer.src = data.audio_url;
            audioPlayerContainer.classList.remove('hidden');
            showMessage("Audio generated successfully!");
        } catch (error) {
            showMessage(`Error: ${error.message}`, "error");
        } finally {
            loadingIndicator.classList.add('hidden');
            generateButton.disabled = false;
            generateButton.textContent = 'Generate & Play';
        }
    });

    // --- Echo Bot Logic (Unchanged from your original) ---
    llmStartRecordingBtn?.addEventListener('click', async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];
            mediaRecorder.addEventListener('dataavailable', e => audioChunks.push(e.data));
            mediaRecorder.addEventListener('stop', async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                llmRecordingStatus.classList.add('hidden');
                llmLoadingIndicator.classList.remove('hidden');
                llmTranscriptionContainer.classList.add('hidden');
                llmAudioContainer.classList.add('hidden');
                try {
                    const formData = new FormData();
                    formData.append('audio_file', audioBlob, "user_audio.webm");
                    formData.append('voiceId', voiceSelect.value);

                    const response = await fetch('/llm/query', { method: 'POST', body: formData });
                    const data = await response.json();
                    if (!response.ok) {
                         throw new Error(data.details || data.error || 'Failed to get LLM response.');
                    }
                    llmTranscriptionResult.textContent = data.llm_response_text;
                    llmTranscriptionContainer.classList.remove('hidden');
                    llmAudioPlayer.src = data.llm_audio_url;
                    llmAudioContainer.classList.remove('hidden');
                } catch (error) {
                    showMessage(`Echo Bot Error: ${error.message}`, 'error');
                } finally {
                    llmLoadingIndicator.classList.add('hidden');
                    stream.getTracks().forEach(track => track.stop());
                }
            });
            mediaRecorder.start();
            llmStartRecordingBtn.disabled = true;
            llmStopRecordingBtn.disabled = false;
            llmRecordingStatus.classList.remove('hidden');
        } catch (error) {
            showMessage('Microphone access denied or an error occurred.', 'error');
        }
    });

    llmStopRecordingBtn?.addEventListener('click', () => {
        if (mediaRecorder?.state === 'recording') {
            mediaRecorder.stop();
            llmStartRecordingBtn.disabled = false;
            llmStopRecordingBtn.disabled = true;
        }
    });

    // --- AI Voice Chat Logic (THIS PART IS NOW ROBUST) ---
    const renderChatHistory = (history) => {
        chatHistoryContainer.innerHTML = '';
        if (!history || history.length === 0) {
            emptyChatMessage.classList.remove('hidden');
            return;
        }
        emptyChatMessage.classList.add('hidden');
        history.forEach((message, index) => {
            const turnContainer = document.createElement('div');
            turnContainer.className = 'response-card';
            if (message.role === 'user') {
                turnContainer.innerHTML = `<h3 class="font-bold text-lg mb-2 text-indigo-300">Your speech</h3><p class="text-gray-300">${message.text}</p>`;
            } else if (message.role === 'model') {
                turnContainer.innerHTML = `<h3 class="font-bold text-lg mb-2 text-purple-300">dhwani reply</h3><p class="text-gray-300 mb-4">${message.text}</p><audio id="agent-audio-player-${index}" class="w-full" controls></audio>`;
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
                agentStatus.textContent = "Could not load history.";
                console.error(error);
            }
        }
    };

    const clearAgentChat = async () => {
        if (!sessionId) return;
        try {
            await fetch(`/agent/chat/${sessionId}`, { method: 'DELETE' });
            renderChatHistory([]);
            agentStatus.textContent = 'Ready to listen...';
            hideAgentError(); // Hide error on clear
        } catch (error) {
            showAgentError("Error clearing chat.");
        }
    };

    const startAgentRecording = async () => {
        if (isAgentRecording) return;
        hideAgentError(); // Hide any previous errors
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

                if (audioBlob.size < 500) { // Check for silence
                    agentStatus.textContent = 'Did not hear anything. Try again.';
                    agentStartBtn.classList.remove('hidden');
                    agentStopBtn.classList.add('hidden');
                    return;
                }

                agentStatus.textContent = 'Thinking...';
                const formData = new FormData();
                formData.append('audio_file', audioBlob, "user_audio.webm");
                formData.append('voiceId', voiceSelect.value);

                try {
                    const response = await fetch(`/agent/chat/${sessionId}`, { method: 'POST', body: formData });
                    const data = await response.json(); 

                    renderChatHistory(data.history);

                    const lastAudioPlayer = document.getElementById(`agent-audio-player-${data.history.length - 1}`);

                    if (response.ok) { // SUCCESS case
                        if (data.audio_url && lastAudioPlayer) {
                            lastAudioPlayer.src = data.audio_url;
                            lastAudioPlayer.play();
                            agentStatus.textContent = 'Playing response...';
                            lastAudioPlayer.onended = () => {
                                agentStatus.textContent = 'Response finished. Ready to listen...';
                                agentStartBtn.classList.remove('hidden');
                                agentStopBtn.classList.add('hidden');
                            };
                        } else {
                            agentStatus.textContent = 'Ready to listen...';
                            agentStartBtn.classList.remove('hidden');
                            agentStopBtn.classList.add('hidden');
                        }
                    } else { // ERROR case
                        showAgentError(data.error || 'An unknown error occurred.');
                        if (data.audio_url && lastAudioPlayer) {
                            lastAudioPlayer.src = data.audio_url;
                            lastAudioPlayer.play();
                            agentStatus.textContent = 'Playing error message...';
                            lastAudioPlayer.onended = () => {
                                agentStatus.textContent = 'An error occurred. Ready to listen...';
                                agentStartBtn.classList.remove('hidden');
                                agentStopBtn.classList.add('hidden');
                            };
                        } else {
                            agentStatus.textContent = 'An error occurred. Please try again.';
                            agentStartBtn.classList.remove('hidden');
                            agentStopBtn.classList.add('hidden');
                        }
                    }
                } catch (error) { // NETWORK error
                    showAgentError(`Network error: ${error.message}`);
                    agentStatus.textContent = 'Connection Error';
                    agentStartBtn.classList.remove('hidden');
                    agentStopBtn.classList.add('hidden');
                }
            });

            agentMediaRecorder.start();
            agentStatus.textContent = 'Listening...';
            agentStartBtn.classList.add('hidden');
            agentStopBtn.classList.remove('hidden');
            agentStopBtn.disabled = false;
        } catch (error) {
            showAgentError('Microphone access denied. Please allow microphone permissions in your browser.');
            agentStatus.textContent = 'Mic Error';
            console.error(error);
        }
    };

    const stopAgentRecording = () => {
        if (agentMediaRecorder?.state === 'recording') {
            agentMediaRecorder.stop();
            agentStopBtn.disabled = true;
            agentStatus.textContent = 'Processing...';
        }
    };

    fetchVoices();
    initSession();
    agentStartBtn?.addEventListener('click', startAgentRecording);
    agentStopBtn?.addEventListener('click', stopAgentRecording);
    agentClearBtn?.addEventListener('click', clearAgentChat);
});