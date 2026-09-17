// --- AutoDiag Chat Engine — Automotive Diagnostic RAG Assistant ---
document.addEventListener('DOMContentLoaded', () => {
  const chatScrollArea = document.getElementById('chat-scroll-area');
  const chatForm = document.getElementById('chat-form');
  const messageInput = document.getElementById('message-input');
  const sendBtn = document.getElementById('send-trigger-btn');
  const streamFrame = document.getElementById('border-stream-frame');
  const heroSplash = document.getElementById('hero-splash');
  const clearChatBtn = document.getElementById('clear-chat-btn');
  const suggestionCards = document.querySelectorAll('.suggestion-card');
  const statusPing = document.getElementById('status-ping');
  const statusText = document.getElementById('status-text');
  const statusPill = document.getElementById('status-pill');
  const chunksEl = document.getElementById('chunks-badge');

  let isGenerating = false;
  let audioCtx = null;

  // --- Health Check on Load ---
  fetch('/health', { method: 'GET' })
    .then(r => r.json())
    .then(data => {
      if (data && data.status === 'ok') {
        if (statusPing) statusPing.className = 'status-ping';
        if (statusText) statusText.textContent = 'System Online';
        if (chunksEl && data.chunks_indexed) {
          chunksEl.textContent = data.chunks_indexed.toLocaleString() + ' chunks indexed';
          chunksEl.style.display = 'inline-flex';
        }
      }
    })
    .catch(() => {
      if (statusPing) statusPing.className = 'status-ping offline';
      if (statusText) statusText.textContent = 'Backend Offline';
      if (statusPill) statusPill.className = 'badge-pill offline';
    });

  // --- Audio Haptic ---
  function playHapticChime() {
    try {
      if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      if (audioCtx.state === 'suspended') audioCtx.resume();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(680, audioCtx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(320, audioCtx.currentTime + 0.2);
      gain.gain.setValueAtTime(0.07, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.22);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.24);
    } catch (e) {}
  }

  function scrollToBottom() {
    requestAnimationFrame(() => { chatScrollArea.scrollTop = chatScrollArea.scrollHeight; });
  }

  function triggerSubmitSquash() {
    playHapticChime();
    if (streamFrame) {
      streamFrame.classList.remove('color-squashing');
      void streamFrame.offsetWidth;
      streamFrame.classList.add('color-squashing');
      setTimeout(() => streamFrame.classList.remove('color-squashing'), 720);
    }
    if (window.triggerSmashWebGL) window.triggerSmashWebGL();
    if (window.triggerSmashThreeJS) window.triggerSmashThreeJS();
  }

  function escapeHtml(text) {
    return text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function formatResponse(text) {
    if (!text) return '';
    let t = escapeHtml(text);
    t = t.replace(/`([^`]+)`/g, '<code>$1</code>');
    t = t.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    t = t.replace(/(?:^|\n)[ \t]*[-*][ \t]+(.+)/g, '<br/>• $1');
    t = t.replace(/(?:^|\n)[ \t]*(\d+)\.[ \t]+(.+)/g, '<br/><strong>$1.</strong> $2');
    return t;
  }

  function appendUserMessage(text) {
    if (heroSplash && heroSplash.style.display !== 'none') heroSplash.style.display = 'none';
    const row = document.createElement('div');
    row.className = 'chat-row user-row';
    row.innerHTML = `<div class="user-bubble"><div class="user-text">${escapeHtml(text)}</div></div>`;
    chatScrollArea.appendChild(row);
    scrollToBottom();
  }

  function appendTypingIndicator() {
    const row = document.createElement('div');
    row.className = 'chat-row assistant-row typing-row';
    row.id = 'active-typing-loader';
    row.innerHTML = `
      <div class="typing-loader">
        <div class="typing-dots">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
        <span class="typing-text">Scanning NHTSA records & diagnostics...</span>
      </div>`;
    chatScrollArea.appendChild(row);
    scrollToBottom();
    return row;
  }

  function removeTypingIndicator() {
    const el = document.getElementById('active-typing-loader');
    if (el) el.remove();
  }

  function appendAssistantMessage(data) {
    removeTypingIndicator();
    const row = document.createElement('div');
    row.className = 'chat-row assistant-row';

    const answer = data.answer || data.reply || '';
    const sources = data.sources || [];

    const sourcesHtml = sources.length > 0 ? `
      <div class="sources-footer">
        <span class="sources-label">Sources</span>
        ${sources.map(s => `<span class="source-tag"><span class="material-symbols-outlined" style="font-size:10px;">description</span>${escapeHtml(s)}</span>`).join('')}
      </div>` : '';

    row.innerHTML = `
      <div class="assistant-bubble">
        <div class="assistant-meta-bar">
          <span class="meta-chip rag-chip"><span class="material-symbols-outlined" style="font-size:11px;">auto_stories</span>NHTSA RAG</span>
          <span class="meta-chip model-chip"><span class="material-symbols-outlined" style="font-size:11px;">smart_toy</span>Llama 3.2</span>
          <span class="meta-chip source-chip"><span class="material-symbols-outlined" style="font-size:11px;">verified</span>${sources.length} Reference${sources.length !== 1 ? 's' : ''}</span>
        </div>
        <div class="assistant-body">${formatResponse(answer)}</div>
        ${sourcesHtml}
      </div>`;

    chatScrollArea.appendChild(row);
    scrollToBottom();
  }

  function appendErrorMessage(err) {
    removeTypingIndicator();
    const row = document.createElement('div');
    row.className = 'chat-row assistant-row';
    row.innerHTML = `
      <div class="assistant-bubble" style="border-top-color: var(--orange);">
        <div class="assistant-meta-bar">
          <span class="meta-chip" style="color:var(--orange);border-color:rgba(255,92,0,0.3);">
            <span class="material-symbols-outlined" style="font-size:11px;">error_outline</span>System Notice
          </span>
        </div>
        <div class="assistant-body" style="color:#F87171;">${escapeHtml(err || 'Unable to reach the backend. Please ensure the API server is running.')}</div>
      </div>`;
    chatScrollArea.appendChild(row);
    scrollToBottom();
  }

  async function submitMessage(userText) {
    const text = (userText || messageInput.value || '').trim();
    if (!text || isGenerating) return;

    messageInput.value = '';
    messageInput.blur();
    triggerSubmitSquash();
    appendUserMessage(text);
    appendTypingIndicator();

    isGenerating = true;
    if (sendBtn) sendBtn.disabled = true;

    try {
      const response = await fetch('/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: text })
      });
      if (!response.ok) throw new Error(`Server error: ${response.status}`);
      const data = await response.json();
      appendAssistantMessage(data);
    } catch (error) {
      console.error('Query error:', error);
      appendErrorMessage(error.message || 'Transmission interrupted.');
    } finally {
      isGenerating = false;
      if (sendBtn) sendBtn.disabled = false;
      messageInput.focus();
    }
  }

  if (chatForm) chatForm.addEventListener('submit', e => { e.preventDefault(); submitMessage(); });
  if (messageInput) messageInput.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitMessage(); } });
  if (sendBtn) sendBtn.addEventListener('click', e => { e.preventDefault(); submitMessage(); });

  suggestionCards.forEach(card => {
    card.addEventListener('click', () => {
      const prompt = card.getAttribute('data-prompt');
      if (prompt) submitMessage(prompt);
    });
  });

  if (clearChatBtn) {
    clearChatBtn.addEventListener('click', () => {
      document.querySelectorAll('.chat-row').forEach(r => r.remove());
      if (heroSplash) heroSplash.style.display = 'flex';
    });
  }
});
