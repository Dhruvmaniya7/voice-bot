// static/index.js
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('tts-form');
    const textInput = document.getElementById('text-input');
    const voiceSelect = document.getElementById('voice-select');
    const generateButton = document.getElementById('generate-button');
    const loadingIndicator = document.getElementById('loading-indicator');
    const messageBox = document.getElementById('message-box');
    const audioPlayerContainer = document.getElementById('audio-player-container');
    const audioPlayer = document.getElementById('audio-player');

    // Echo Bot elements
    const startRecordingBtn = document.getElementById('start-recording-btn');
    const stopRecordingBtn = document.getElementById('stop-recording-btn');
    const recordingStatus = document.getElementById('recording-status');
    const uploadingStatus = document.getElementById('uploading-status');
    const echoAudioContainer = document.getElementById('echo-audio-container');
    const echoAudioPlayer = document.getElementById('echo-audio-player');
    const deleteEchoBtn = document.getElementById('delete-echo-btn');
    
    // New LLM Bot elements
    const llmStartRecordingBtn = document.getElementById('llm-start-recording-btn');
    const llmStopRecordingBtn = document.getElementById('llm-stop-recording-btn');
    const llmRecordingStatus = document.getElementById('llm-recording-status');
    const llmLoadingIndicator = document.getElementById('llm-loading-indicator');
    const llmTranscriptionResult = document.getElementById('llm-transcription-result');
    const llmTranscriptionContainer = document.getElementById('llm-transcription-container');
    const llmAudioContainer = document.getElementById('llm-audio-container');
    const llmAudioPlayer = document.getElementById('llm-audio-player');

    let mediaRecorder;
    let audioChunks = [];
    let currentEchoAudioUrl = null;

    const showMessage = (message, type = 'success') => {
        messageBox.textContent = message;
        messageBox.classList.remove('hidden', 'bg-red-900', 'text-red-300', 'bg-green-900', 'text-green-300');
        
        if (type === 'success') {
            messageBox.classList.add('bg-green-900', 'text-green-300');
        } else if (type === 'error') {
            messageBox.classList.add('bg-red-900', 'text-red-300');
        }
        messageBox.classList.remove('hidden');
    };

    const formatBytes = (bytes, decimals = 2) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    };
    
    form.addEventListener('submit', async (event) => {
        event.preventDefault(); 

        const text = textInput.value.trim();
        const voiceId = voiceSelect.value;

        audioPlayerContainer.classList.add('hidden');
        messageBox.classList.add('hidden');

        if (!text) {
            showMessage("Please enter some text.", "error");
            return;
        }

        loadingIndicator.classList.remove('hidden');
        generateButton.disabled = true;
        generateButton.textContent = 'Generating...';

        try {
            const formData = new FormData();
            formData.append('text', text);
            formData.append('voiceId', voiceId);

            const response = await fetch('/tts', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Something went wrong on the server.');
            }

            const data = await response.json();
            const audioUrl = data.audio_url;

            if (audioUrl) {
                audioPlayer.src = audioUrl;
                audioPlayer.load();
                audioPlayerContainer.classList.remove('hidden');
                showMessage("Audio generated successfully!");
            } else {
                throw new Error("No audio URL received from the server.");
            }

        } catch (error) {
            console.error('Error:', error);
            showMessage(`Error: ${error.message}`, "error");
        } finally {
            loadingIndicator.classList.add('hidden');
            generateButton.disabled = false;
            generateButton.textContent = 'Generate & Play';
        }
    });

    // Echo Bot logic
    startRecordingBtn?.addEventListener('click', async () => {
        try {
            if (currentEchoAudioUrl) {
                URL.revokeObjectURL(currentEchoAudioUrl);
                currentEchoAudioUrl = null;
                echoAudioPlayer.src = '';
            }
            echoAudioContainer.classList.add('hidden');
            // keep echo bot behavior unchanged
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.addEventListener('dataavailable', (event) => {
                audioChunks.push(event.data);
            });
            
            mediaRecorder.addEventListener('stop', async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                
                recordingStatus.classList.add('hidden');
                uploadingStatus.classList.remove('hidden');

                try {
                    const formData = new FormData();
                    formData.append('audio_file', audioBlob, `recording_${Date.now()}.webm`);
                    formData.append('voiceId', voiceSelect.value);

                    const response = await fetch('/tts/echo', {
                        method: 'POST',
                        body: formData
                    });

                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.error || 'Echo generation failed');
                    }

                    const data = await response.json();
                    
                    // keep using existing IDs used by your echo UI
                    const transcriptionContainer = document.getElementById('transcription-container');
                    const transcriptionResult = document.getElementById('transcription-result');

                    if (transcriptionContainer && transcriptionResult) {
                        transcriptionContainer.classList.remove('hidden');
                        transcriptionResult.textContent = data.transcript || '';
                    }

                    echoAudioContainer.classList.remove('hidden');
                    echoAudioPlayer.src = data.echo_audio_url || '';

                    showMessage("Echo generated successfully!", 'success');

                } catch (error) {
                    console.error('Echo generation error:', error);
                    showMessage(`Echo generation failed: ${error.message}`, 'error');
                } finally {
                    uploadingStatus.classList.add('hidden');
                    stream.getTracks().forEach(track => track.stop());
                }
            });

            mediaRecorder.start();
            startRecordingBtn.disabled = true;
            stopRecordingBtn.disabled = false;
            recordingStatus.classList.remove('hidden');

        } catch (error) {
            console.error('Error accessing microphone:', error);
            showMessage('Error accessing microphone. Please check your browser permissions.', 'error');
        }
    });

    stopRecordingBtn?.addEventListener('click', () => {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
            startRecordingBtn.disabled = false;
            stopRecordingBtn.disabled = true;
            recordingStatus.classList.add('hidden');
        }
    });

    deleteEchoBtn?.addEventListener('click', () => {
        echoAudioPlayer.src = '';
        echoAudioContainer.classList.add('hidden');
        const transcriptionResult = document.getElementById('transcription-result');
        if (transcriptionResult) transcriptionResult.textContent = '';
        const transcriptionContainer = document.getElementById('transcription-container');
        if (transcriptionContainer) transcriptionContainer.classList.add('hidden');
        showMessage('Echo recording and transcription cleared.', 'success');
    });

    // LLM Bot Logic
    llmStartRecordingBtn?.addEventListener('click', async () => {
        try {
            llmAudioContainer.classList.add('hidden');
            llmTranscriptionContainer.classList.add('hidden');
            messageBox.classList.add('hidden');

            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.addEventListener('dataavailable', (event) => {
                audioChunks.push(event.data);
            });
            
            mediaRecorder.addEventListener('stop', async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                
                llmRecordingStatus.classList.add('hidden');
                llmLoadingIndicator.classList.remove('hidden');

                try {
                    const formData = new FormData();
                    formData.append('audio_file', audioBlob, `recording_${Date.now()}.webm`);
                    formData.append('voiceId', voiceSelect.value);

                    // <-- CHANGED: post audio to unified endpoint /llm/query
                    const response = await fetch('/llm/query', {
                        method: 'POST',
                        body: formData
                    });

                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.error || 'LLM audio generation failed');
                    }

                    const data = await response.json();
                    
                    llmTranscriptionContainer.classList.remove('hidden');
                    llmTranscriptionResult.textContent = data.llm_response_text || '';

                    llmAudioContainer.classList.remove('hidden');
                    llmAudioPlayer.src = data.llm_audio_url || '';
                    try { llmAudioPlayer.play(); } catch (e) { /* autoplay may be blocked */ }

                    showMessage("LLM audio response generated successfully!", 'success');

                } catch (error) {
                    console.error('LLM audio generation error:', error);
                    showMessage(`LLM audio generation failed: ${error.message}`, 'error');
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
            console.error('Error accessing microphone:', error);
            showMessage('Error accessing microphone. Please check your browser permissions.', 'error');
        }
    });

    llmStopRecordingBtn?.addEventListener('click', () => {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
            llmStartRecordingBtn.disabled = false;
            llmStopRecordingBtn.disabled = true;
            llmRecordingStatus.classList.add('hidden');
        }
    });

    const fetchVoices = async () => {
        try {
            const response = await fetch('/voices');
            if (!response.ok) {
                throw new Error('Failed to fetch voices.');
            }
            const voices = await response.json();
            voiceSelect.innerHTML = '';
            voices.forEach(voice => {
                const option = document.createElement('option');
                option.value = voice.voiceId;
                option.textContent = `${voice.displayName} (${voice.gender}, ${voice.locale})`;
                voiceSelect.appendChild(option);
            });
        } catch (error) {
            console.error('Error fetching voices:', error);
            showMessage('Failed to load voices.', 'error');
        }
    };
    fetchVoices();
});
