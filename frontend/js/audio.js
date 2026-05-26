let recognition = null;
let isRecording = false;
let recordingTimeout = null;

/* ==================== SPEECH RECOGNITION (LIVE TRANSCRIPTION) ==================== */

function initSpeechRecognition() {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
        showToast('Speech recognition not supported in this browser. Use Chrome or Edge.', 'error');
        return null;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recog = new SpeechRecognition();

    recog.continuous = true;
    recog.interimResults = true;
    recog.lang = 'en-US';

    recog.onstart = () => {
        isRecording = true;
        document.getElementById('mic-btn').classList.add('recording');
        document.getElementById('recording-status').classList.remove('hidden');

        // Auto-stop after 60 seconds
        recordingTimeout = setTimeout(() => {
            stopRecording();
        }, 60000);
    };

    recog.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;

            if (event.results[i].isFinal) {
                finalTranscript += transcript + ' ';
            } else {
                interimTranscript += transcript;
            }
        }

        const input = document.getElementById('message-input');
        if (!input) return;

        // Store base text (what was there before recording started)
        if (!input.dataset.baseText) {
            input.dataset.baseText = input.value;
        }

        // Update input with base + new transcription
        const baseText = input.dataset.baseText || '';
        const newText = finalTranscript || interimTranscript;

        input.value = (baseText + ' ' + newText).trim();
        autoResizeTextarea();

        // Save final results to base
        if (finalTranscript) {
            input.dataset.baseText = input.value;
        }

        // Update recording status
        const status = document.getElementById('recording-text');
        if (status) {
            status.textContent = interimTranscript ? 'Listening...' : 'Speak now...';
        }
    };

    recog.onerror = (event) => {
        console.error('Speech recognition error:', event.error);

        if (event.error === 'not-allowed') {
            showToast('Microphone permission denied', 'error');
        } else if (event.error === 'no-speech') {
            showToast('No speech detected', 'error');
        } else {
            showToast(`Speech error: ${event.error}`, 'error');
        }

        stopRecording();
    };

    recog.onend = () => {
        isRecording = false;
        document.getElementById('mic-btn').classList.remove('recording');
        document.getElementById('recording-status').classList.add('hidden');

        const input = document.getElementById('message-input');
        if (input) {
            delete input.dataset.baseText;
        }

        if (recordingTimeout) {
            clearTimeout(recordingTimeout);
            recordingTimeout = null;
        }
    };

    return recog;
}

function startRecording() {
    if (isRecording) {
        stopRecording();
        return;
    }

    if (!recognition) {
        recognition = initSpeechRecognition();
    }

    if (!recognition) return;

    try {
        recognition.start();
    } catch (err) {
        console.error('Failed to start recording:', err);
        showToast('Could not start recording', 'error');
    }
}

function stopRecording() {
    if (recognition && isRecording) {
        recognition.stop();
    }
}

/* ==================== TEXT-TO-SPEECH ==================== */

let currentUtterance = null;
let availableVoices = [];

function loadVoices() {
    if (!('speechSynthesis' in window)) return;

    availableVoices = window.speechSynthesis.getVoices();

    const select = document.getElementById('voice-select');
    if (!select) return;

    select.innerHTML = '';

    // Filter to English voices
    const englishVoices = availableVoices.filter(v => v.lang.startsWith('en'));

    if (englishVoices.length === 0) {
        select.innerHTML = '<option value="">No voices available</option>';
        return;
    }

    englishVoices.forEach((voice, index) => {
        const option = document.createElement('option');
        option.value = index;
        option.textContent = `${voice.name} (${voice.lang})`;
        select.appendChild(option);
    });

    // Load saved voice
    const savedVoice = localStorage.getItem('nova_voice_index');
    if (savedVoice && englishVoices[savedVoice]) {
        select.value = savedVoice;
    }
}

function loadVoiceSettings() {
    // Load voices
    loadVoices();

    // Load rate
    const savedRate = localStorage.getItem('nova_speech_rate');
    if (savedRate) {
        document.getElementById('speech-rate').value = savedRate;
        updateRateDisplay(savedRate);
    }

    // Load pitch
    const savedPitch = localStorage.getItem('nova_speech_pitch');
    if (savedPitch) {
        document.getElementById('speech-pitch').value = savedPitch;
        updatePitchDisplay(savedPitch);
    }

    // Load auto-read setting
    const autoRead = localStorage.getItem('nova_auto_read') === 'true';
    document.getElementById('auto-read-toggle').checked = autoRead;
}

function saveVoiceSettings() {
    const voiceIndex = document.getElementById('voice-select').value;
    const rate = document.getElementById('speech-rate').value;
    const pitch = document.getElementById('speech-pitch').value;
    const autoRead = document.getElementById('auto-read-toggle').checked;

    localStorage.setItem('nova_voice_index', voiceIndex);
    localStorage.setItem('nova_speech_rate', rate);
    localStorage.setItem('nova_speech_pitch', pitch);
    localStorage.setItem('nova_auto_read', autoRead ? 'true' : 'false');

    showToast('Voice settings saved', 'success');
}

function updateRateDisplay(value) {
    document.getElementById('rate-display').textContent = `${parseFloat(value).toFixed(1)}x`;
}

function updatePitchDisplay(value) {
    document.getElementById('pitch-display').textContent = `${parseFloat(value).toFixed(1)}x`;
}

function isAutoReadEnabled() {
    return localStorage.getItem('nova_auto_read') === 'true';
}

function speakText(text) {
    if (!('speechSynthesis' in window)) {
        showToast('Text-to-speech not supported', 'error');
        return;
    }

    // Stop any ongoing speech
    stopSpeaking();

    // Clean markdown from text
    const cleanText = text
        .replace(/```[\s\S]*?```/g, ' code block ')
        .replace(/`([^`]+)`/g, '$1')
        .replace(/[*_~>#]/g, '')
        .replace(/\[(.*?)\]\(.*?\)/g, '$1')
        .replace(/\n+/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();

    if (!cleanText) return;

    currentUtterance = new SpeechSynthesisUtterance(cleanText);

    // Apply saved settings
    const voiceIndex = localStorage.getItem('nova_voice_index');
    const englishVoices = availableVoices.filter(v => v.lang.startsWith('en'));

    if (voiceIndex && englishVoices[voiceIndex]) {
        currentUtterance.voice = englishVoices[voiceIndex];
    } else if (englishVoices.length > 0) {
        // Default to first female voice or any English voice
        const femaleVoice = englishVoices.find(v => v.name.toLowerCase().includes('female'));
        currentUtterance.voice = femaleVoice || englishVoices[0];
    }

    currentUtterance.rate = parseFloat(localStorage.getItem('nova_speech_rate') || '1');
    currentUtterance.pitch = parseFloat(localStorage.getItem('nova_speech_pitch') || '1');
    currentUtterance.volume = 1;

    currentUtterance.onerror = (event) => {
        console.error('Speech error:', event);
    };

    window.speechSynthesis.speak(currentUtterance);
}

function stopSpeaking() {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
    }
    currentUtterance = null;
}

function testVoice() {
    const testText = "Hello! This is a test of your selected voice settings. How do I sound?";
    speakText(testText);
}

/* ==================== INITIALIZE VOICES ==================== */

if ('speechSynthesis' in window) {
    // Load voices when they become available
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
        window.speechSynthesis.onvoiceschanged = loadVoices;
    }

    // Try loading immediately
    setTimeout(loadVoices, 100);
}