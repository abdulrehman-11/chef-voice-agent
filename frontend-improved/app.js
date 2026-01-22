/**
 * Chef Voice AI - Frontend Application
 * Professional Landing Page + Voice Interface
 */

// Configuration
const TOKEN_SERVER_URL = 'https://chef-voice-agent-production.up.railway.app/get-token';
const LIVEKIT_URL = 'wss://chef-live-voice-agent-n6istvo9.livekit.cloud';

// State
let room = null;
let isConnected = false;
let isRecording = false;
let currentSlide = 0;

// DOM Elements (will be initialized on load)
let landingPage, appInterface, voiceButton, conversationArea, recipePreview;
let connectionStatus, voiceVisualizer;

// Session Storage Constants
const STORAGE_KEY = 'chef_conversation';
const MAX_MESSAGES = 100; // Prevent localStorage overflow

/**
 * Storage Helper Functions
 */
function saveMessageToStorage(text, role) {
    try {
        const messages = getConversationFromStorage();
        messages.push({
            text,
            role,
            timestamp: Date.now()
        });

        // Keep only last MAX_MESSAGES
        const trimmed = messages.slice(-MAX_MESSAGES);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
    } catch (e) {
        console.warn('⚠️ Failed to save message to localStorage:', e);
        // Graceful degradation - app still works
    }
}

function getConversationFromStorage() {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        return stored ? JSON.parse(stored) : [];
    } catch (e) {
        console.warn('⚠️ Failed to load conversation from localStorage:', e);
        // Clear corrupted data
        localStorage.removeItem(STORAGE_KEY);
        return [];
    }
}

function clearConversationStorage() {
    try {
        localStorage.removeItem(STORAGE_KEY);
        console.log('✅ Conversation storage cleared');
    } catch (e) {
        console.warn('⚠️ Failed to clear conversation storage:', e);
    }
}

/**
 * Initialize Application
 */
function init() {
    console.log('🎨 Initializing Chef AI Voice Assistant...');

    // Get DOM elements
    landingPage = document.getElementById('landingPage');
    appInterface = document.getElementById('appInterface');
    voiceButton = document.getElementById('voiceButton');
    conversationArea = document.getElementById('conversationArea');
    recipePreview = document.getElementById('recipePreview');
    connectionStatus = document.getElementById('connectionStatus');
    voiceVisualizer = document.getElementById('voiceVisualizer');

    // Start carousel auto-play
    startCarousel();

    // Setup voice button
    if (voiceButton) {
        voiceButton.addEventListener('click', handleVoiceClick);
    }

    // Restore conversation from localStorage
    restoreConversation();

    console.log('✅ Application initialized');
}

/**
 * Restore Conversation from localStorage
 */
function restoreConversation() {
    const messages = getConversationFromStorage();

    if (messages.length > 0) {
        console.log(`📜 Restoring ${messages.length} messages from storage`);

        // Restore each message WITHOUT saving again
        messages.forEach(msg => {
            addMessageDOMOnly(msg.text, msg.role);
        });
    }
}

/**
 * Carousel Management
 */
function startCarousel() {
    setInterval(() => {
        currentSlide = (currentSlide + 1) % 3;
        updateCarousel();
    }, 5000); // Auto-slide every 5 seconds
}

function goToSlide(index) {
    currentSlide = index;
    updateCarousel();
}

function updateCarousel() {
    const track = document.querySelector('.carousel-track');
    const dots = document.querySelectorAll('.dot');

    if (track) {
        track.style.transform = `translateX(-${currentSlide * 100}%)`;
    }

    dots.forEach((dot, index) => {
        dot.classList.toggle('active', index === currentSlide);
    });
}

/**
 * Navigation Functions
 */
function scrollToApp() {
    // Show app interface
    if (landingPage) landingPage.style.display = 'none';
    if (appInterface) {
        appInterface.classList.remove('hidden');
    }
    if (voiceButton) {
        voiceButton.classList.remove('hidden');
    }
}

function showLanding() {
    // Disconnect if connected
    if (isConnected) {
        disconnectFromRoom();
    }

    // Show landing page
    if (landingPage) landingPage.style.display = 'block';
    if (appInterface) {
        appInterface.classList.add('hidden');
    }
    if (voiceButton) {
        voiceButton.classList.add('hidden');
    }
}

/**
 * Switch between Recipe and Transcript views (Mobile/Tablet)
 */
function switchView(view) {
    const recipePanel = document.getElementById('recipeBuilderPanel');
    const conversationPanel = document.getElementById('conversationPanel');
    const tabs = document.querySelectorAll('.view-tab');

    // Update active states
    tabs.forEach(tab => {
        if (tab.dataset.view === view) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });

    // Show/hide panels
    if (view === 'recipe') {
        recipePanel?.classList.add('active');
        conversationPanel?.classList.remove('active');
    } else {
        conversationPanel?.classList.add('active');
        recipePanel?.classList.remove('active');
    }

    console.log(`📱 Switched to ${view} view`);
}

/**
 * Voice Button Click Handler
 */
async function handleVoiceClick() {
    if (!isConnected) {
        await connectToRoom();
    } else {
        await disconnectFromRoom();
    }
}

/**
 * Connect to Live Kit Room
 */
async function connectToRoom() {
    try {
        console.log('🔗 Connecting to LiveKit...');
        console.log('📍 Server URL:', LIVEKIT_URL);
        console.log('🔑 Token server:', TOKEN_SERVER_URL);

        voiceButton.classList.add('active');
        updateConnectionUI('Connecting...', false);

        // Get access token from server
        console.log('🎫 Requesting access token...');
        const token = await getAccessToken();
        console.log('✅ Token received');

        // Create room
        const LiveKitNS = window.LiveKit || window.LivekitClient;
        if (!LiveKitNS) {
            throw new Error('LiveKit client library not loaded');
        }

        console.log('🏗️ Creating LiveKit room...');
        room = new LiveKitNS.Room({
            adaptiveStream: true,
            dynacast: true,
        });

        // Store namespace for later use
        window.LiveKitNS = LiveKitNS;

        // Set up event handlers
        console.log('📡 Setting up event handlers...');
        setupRoomHandlers();

        // Connect
        console.log('🔌 Connecting to room...');
        await room.connect(LIVEKIT_URL, token);
        console.log('✅ Connected to LiveKit room!');

        // Enable microphone
        console.log('🎤 Enabling microphone...');
        await room.localParticipant.setMicrophoneEnabled(true);
        console.log('✅ Microphone enabled');

        isConnected = true;
        isRecording = true;

        updateConnectionUI('Connected', true);
        showVoiceVisualizer(true);
        showToast('Connected! Start speaking...', 'success');

        console.log('🎉 Ready to listen!');

    } catch (error) {
        console.error('❌ Connection failed:', error);
        console.error('Error details:', error.message, error.stack);
        voiceButton.classList.remove('active');
        updateConnectionUI('Connection failed', false);
        showToast(`Failed to connect: ${error.message}`, 'error');
    }
}

/**
 * Disconnect from room
 */
async function disconnectFromRoom() {
    try {
        if (room) {
            await room.disconnect();
        }

        isConnected = false;
        isRecording = false;

        voiceButton.classList.remove('active');
        updateConnectionUI('Ready', false);
        showVoiceVisualizer(false);
        showToast('Disconnected', 'info');

        console.log('👋 Disconnected');

    } catch (error) {
        console.error('Disconnect error:', error);
    }
}

/**
 * Setup LiveKit Room Event Handlers
 */
function setupRoomHandlers() {
    const LiveKitNS = window.LiveKitNS || window.LiveKit || window.LivekitClient;

    // Handle incoming audio tracks - ONLY from REMOTE participants (not our own mic!)
    room.on(LiveKitNS.RoomEvent.TrackSubscribed, (track, publication, participant) => {
        console.log('🎵 Track subscribed:', track.kind, 'from:', participant.identity);

        // Skip if this is our own track (local participant) - prevents echo!
        if (participant === room.localParticipant) {
            console.log('⚠️ Skipping local participant track (prevents echo)');
            return;
        }

        // Only attach and play audio tracks from REMOTE participants (the agent)
        if (track.kind === LiveKitNS.Track.Kind.Audio) {
            console.log('🔊 Playing agent audio from:', participant.identity);
            const audioElement = track.attach();
            audioElement.id = `audio-${participant.identity}`;
            audioElement.autoplay = true;  // Enable autoplay
            audioElement.volume = 1.0;     // Full volume
            document.body.appendChild(audioElement);

            // Force play with user gesture context (since mic button was clicked)
            audioElement.play()
                .then(() => console.log('✅ Audio playing successfully'))
                .catch(e => {
                    console.error('❌ Audio play failed:', e);
                    // Try again after a short delay
                    setTimeout(() => audioElement.play(), 500);
                });
        }
    });

    // Handle transcription events from LiveKit agents (STT/TTS transcripts)
    room.on(LiveKitNS.RoomEvent.TranscriptionReceived, (segments, participant, publication) => {
        console.log('📝 Transcription received from:', participant?.identity || 'unknown');
        console.log('📝 Segments:', segments);

        for (const segment of segments) {
            console.log(`📝 Segment: "${segment.text}" | Final: ${segment.final} | ID: ${segment.id}`);

            // Determine if this is from the agent or user
            const isAgent = participant && participant.identity && participant.identity.startsWith('agent-');
            const role = isAgent ? 'assistant' : 'user';

            if (segment.final) {
                // Add final transcript to conversation
                addMessage(segment.text, role);
            } else {
                // Show interim transcript
                if (!isAgent) {
                    showInterimTranscript(segment.text);
                }
            }
        }
    });

    // Handle data messages (legacy format, recipe updates)
    room.on(LiveKitNS.RoomEvent.DataReceived, (payload, participant) => {

        try {
            console.log('📨 Raw data received:', payload);
            const decoder = new TextDecoder();
            const dataStr = decoder.decode(payload);
            console.log('📝 Decoded string:', dataStr);

            // Try to parse as JSON
            let data;
            try {
                data = JSON.parse(dataStr);
            } catch (e) {
                // If not JSON, try to eval (Python dict format)
                console.log('⚠️ Not JSON, trying Python dict format...');
                // Convert Python dict to JSON by replacing single quotes
                const jsonStr = dataStr.replace(/'/g, '"').replace(/True/g, 'true').replace(/False/g, 'false');
                data = JSON.parse(jsonStr);
            }

            console.log('✅ Parsed data:', data);

            // Handle recipe events
            if (data.type === 'recipe_event') {
                console.log('🎨 Recipe event received:', data.event);

                // Route to Recipe Builder
                if (window.RecipeBuilder) {
                    window.RecipeBuilder.handleRecipeEvent(data);
                }

                // Auto-switch to recipe view on mobile/tablet when recipe starts
                if (data.event === 'recipe_saving' && window.innerWidth < 1025) {
                    switchView('recipe');
                }
            }
            // Handle legacy transcript events
            else if (data.type === 'transcript') {
                console.log(`💬 [${data.role.toUpperCase()}] ${data.interim ? '[INTERIM]' : ''} ${data.text}`);

                // Only add final transcripts to conversation
                if (!data.interim) {
                    addMessage(data.text, data.role);
                }

                // Show interim transcripts as overlays or typing indicators
                if (data.interim && data.role === 'user') {
                    showInterimTranscript(data.text);
                }
            }
            // Handle legacy recipe updates
            else if (data.type === 'recipe_update') {
                console.log('📋 Legacy recipe update received:', data.recipe);
                updateRecipePreview(data.recipe);
            }
        } catch (error) {
            console.error('❌ Error parsing data:', error, 'Payload:', payload);
        }
    });

    // Handle disconnection
    room.on(LiveKitNS.RoomEvent.Disconnected, () => {
        console.log('🔌 Room disconnected');
        isConnected = false;
        updateConnectionUI('Disconnected', false);
        voiceButton.classList.remove('active');
        showVoiceVisualizer(false);
    });

    // Handle participant speaking
    room.on(LiveKitNS.RoomEvent.ParticipantConnected, (participant) => {
        console.log('👤 Participant connected:', participant.identity);
    });
}

/**
 * Get Access Token from Server
 */
async function getAccessToken() {
    try {
        // Generate unique room name for each session - this triggers agent dispatch
        const uniqueRoomId = 'chef-' + Date.now() + '-' + Math.random().toString(36).substring(7);

        const response = await fetch(TOKEN_SERVER_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                room: uniqueRoomId,  // Unique room per session
                identity: 'chef-' + Math.random().toString(36).substring(7),
            }),
        });

        if (!response.ok) {
            throw new Error(`Token server returned ${response.status}`);
        }

        const data = await response.json();
        return data.token;

    } catch (error) {
        console.error('❌ Failed to get token:', error);
        throw new Error('Could not connect to token server. Make sure it\'s running on port 5000.');
    }
}

/**
 * Show Interim Transcript (what user is currently saying)
 */
let interimElement = null;

function showInterimTranscript(text) {
    if (!conversationArea) return;

    // Create or update interim transcript element
    if (!interimElement) {
        interimElement = document.createElement('div');
        interimElement.className = 'interim-transcript';
        interimElement.style.cssText = `
            opacity: 0.6;
            font-style: italic;
            color: #808080;
            padding: 0.5rem 1rem;
            margin: 0.5rem 0;
            border-left: 3px solid #FF6B35;
        `;
        conversationArea.appendChild(interimElement);
    }

    interimElement.textContent = `🎤 ${text}...`;
    conversationArea.scrollTop = conversationArea.scrollHeight;
}

function clearInterimTranscript() {
    if (interimElement) {
        interimElement.remove();
        interimElement = null;
    }
}

/**
 * Add Message to Conversation
 */
function addMessage(text, role = 'ai') {
    if (!conversationArea) return;

    // Clear interim transcript when adding final message
    clearInterimTranscript();

    console.log(`💬 Adding message [${role}]:`, text);

    // Save to localStorage
    saveMessageToStorage(text, role);

    // Add to DOM
    addMessageDOMOnly(text, role);
}

/**
 * Add Message to DOM Only (no localStorage save)
 * Used for restoring messages from storage
 */
function addMessageDOMOnly(text, role = 'ai') {
    if (!conversationArea) return;

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = (role === 'ai' || role === 'assistant') ? 'AI' : 'You';

    const content = document.createElement('div');
    content.className = 'message-content';

    const p = document.createElement('p');
    p.textContent = text;

    content.appendChild(p);
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);

    conversationArea.appendChild(messageDiv);
    conversationArea.scrollTop = conversationArea.scrollHeight;
}

/**
 * Update Recipe Preview
 */
function updateRecipePreview(recipe) {
    if (!recipePreview) return;

    recipePreview.classList.remove('hidden');

    const nameEl = document.getElementById('recipeName');
    const typeEl = document.getElementById('recipeType');
    const contentEl = document.getElementById('recipeContent');

    if (nameEl && recipe.name) {
        nameEl.textContent = recipe.name;
    }

    if (typeEl && recipe.type) {
        typeEl.textContent = recipe.type;
    }

    if (contentEl) {
        let html = '';

        if (recipe.description) {
            html += `<p>${recipe.description}</p>`;
        }

        if (recipe.ingredients && recipe.ingredients.length > 0) {
            html += '<h4>Ingredients:</h4><ul>';
            recipe.ingredients.forEach(ing => {
                html += `<li>${ing.quantity} ${ing.unit} ${ing.name}</li>`;
            });
            html += '</ul>';
        }

        contentEl.innerHTML = html || '<p class="empty-state">Building recipe...</p>';
    }
}

/**
 * Update Connection UI
 */
function updateConnectionUI(text, connected) {
    if (!connectionStatus) return;

    const statusText = connectionStatus.querySelector('.status-text');
    const statusDot = connectionStatus.querySelector('.status-dot');

    if (statusText) {
        statusText.textContent = text;
    }

    if (statusDot) {
        statusDot.classList.toggle('connected', connected);
    }
}

/**
 * Show/Hide Voice Visualizer
 */
function showVoiceVisualizer(show) {
    if (!voiceVisualizer) return;

    voiceVisualizer.classList.toggle('hidden', !show);
}

/**
 * Show Toast Notification
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.style.cssText = `
        position: fixed;
        bottom: 2rem;
        left: 50%;
        transform: translateX(-50%);
        background: ${type === 'success' ? '#28A745' : type === 'error' ? '#DC3545' : '#FF6B35'};
        color: white;
        padding: 1rem 2rem;
        border-radius: 12px;
        font-weight: 500;
        box-shadow: 0 4px 16px rgba(0,0,0,0.3);
        z-index: 5000;
        animation: slideUp 0.3s ease;
    `;
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideUp 0.3s ease reverse';
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 3000);
}

// Add slideUp animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideUp {
        from { opacity: 0; transform: translate(-50%, 20px); }
        to { opacity: 1; transform: translate(-50%, 0); }
    }
`;
document.head.appendChild(style);

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

// Export for debugging
window.ChefApp = {
    scrollToApp,
    showLanding,
    goToSlide,
    connectToRoom,
    disconnectFromRoom,
    addMessage,
    updateRecipePreview,
    switchView, // NEW: For view switching
    clearConversationStorage, // NEW: For manual clearing
};

/**
 * Session Storage: Clear on tab close (not refresh)
 */
let isRefreshing = false;

window.addEventListener('beforeunload', (e) => {
    // Detect if this is a refresh vs tab close
    const perfNav = e.currentTarget.performance?.navigation;
    const navType = e.currentTarget.performance?.getEntriesByType?.('navigation')?.[0]?.type;

    // Navigation type 1 = reload, 'reload' = reload
    isRefreshing = (perfNav?.type === 1) || (navType === 'reload');
});

window.addEventListener('unload', () => {
    // Only clear if tab is closing (not refreshing)
    if (!isRefreshing) {
        clearConversationStorage();
    }
});

// Initialize default view on mobile/tablet
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        if (window.innerWidth < 1025) {
            // Default to recipe view on mobile/tablet
            switchView('recipe');
        }
    });
} else {
    if (window.innerWidth < 1025) {
        switchView('recipe');
    }
}
