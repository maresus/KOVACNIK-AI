error: non-monotonic index .git/objects/pack/._pack-77a3c134273f26497d6154d1a4667a64abaaf77f.idx
(function() {
  'use strict';

  // Konfiguracija
  const CONFIG = {
    apiUrl: 'https://kovacnik-ai-production.up.railway.app/chat',
    brandColor: '#7b5e3b',
    brandColorHover: '#5d472d',
    title: 'Domačija Kovačnik',
    subtitle: 'Kako vam lahko pomagam?',
    placeholder: 'Vprašajte karkoli...',
    welcomeMessage: 'Pozdravljeni! 👋 Sem vaš virtualni pomočnik Domačije Kovačnik. Kako vam lahko pomagam? — Feel free to write in any language!',
    mobileBreakpoint: 768,
    autoOpenDesktop: true,  // Auto-popup na desktopu
    autoOpenDelay: 6000,  // ms — daj karticam čas da se prikažejo (800ms), nato odpri panel
    maxStoredMessages: 50  // Maksimalno število shranjenih sporočil
  };

  // CSS stili
  const styles = `
    #kv-widget-container * {
      box-sizing: border-box;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    /* === LAUNCHER: en sam position:fixed wrapper za bubble + kartice === */
    #kv-launcher {
      position: fixed;
      bottom: 20px;
      right: 20px;
      z-index: 9999999;
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 10px;
      pointer-events: none;
    }
    #kv-launcher > * {
      pointer-events: all;
    }


    #kv-widget-bubble {
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: ${CONFIG.brandColor};
      cursor: pointer;
      box-shadow: 0 4px 16px rgba(0,0,0,0.2);
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.2s, box-shadow 0.2s;
      border: none;
      padding: 0;
      touch-action: manipulation;
      -webkit-tap-highlight-color: transparent;
      flex-shrink: 0;
      position: relative;
    }

    #kv-widget-bubble:hover {
      transform: scale(1.08);
      box-shadow: 0 6px 24px rgba(0,0,0,0.25);
    }

    #kv-widget-bubble svg {
      width: 28px;
      height: 28px;
      fill: white;
    }

    #kv-widget-bubble.kv-has-notification::after {
      content: '';
      position: absolute;
      top: 2px;
      right: 2px;
      width: 14px;
      height: 14px;
      background: #ef4444;
      border-radius: 50%;
      border: 2px solid white;
    }

    #kv-widget-panel {
      position: fixed;
      bottom: 90px;
      right: 20px;
      width: 380px;
      height: 520px;
      max-height: calc(100vh - 120px);
      background: #fff;
      border-radius: 16px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.18);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      z-index: 999998;
      opacity: 0;
      visibility: hidden;
      transform: translateY(8px);
      transition: opacity 0.15s ease, transform 0.15s ease, visibility 0.15s;
    }

    #kv-widget-panel.kv-open {
      opacity: 1;
      visibility: visible;
      transform: translateY(0);
    }

    /* Mobilni full-screen */
    @media (max-width: ${CONFIG.mobileBreakpoint}px) {
      #kv-widget-panel {
        position: fixed !important;
        inset: 0 !important;
        width: 100% !important;
        height: 100dvh !important;
        height: 100vh !important;
        max-height: none !important;
        border-radius: 0 !important;
        margin: 0 !important;
      }

      #kv-widget-panel.kv-open {
        opacity: 1 !important;
        visibility: visible !important;
        transform: translateY(0) !important;
      }

      /* bubble viden na mobile — tabs so vmesni člen */

      #kv-widget-header {
        padding-top: max(16px, env(safe-area-inset-top)) !important;
        padding-left: max(16px, env(safe-area-inset-left)) !important;
        padding-right: max(16px, env(safe-area-inset-right)) !important;
      }

      #kv-widget-messages {
        -webkit-overflow-scrolling: touch;
        padding-left: max(16px, env(safe-area-inset-left));
        padding-right: max(16px, env(safe-area-inset-right));
      }
    }


    @media (max-width: ${CONFIG.mobileBreakpoint}px) {

      #kv-widget-input-area {
        padding-bottom: max(12px, env(safe-area-inset-bottom)) !important;
        padding-left: max(16px, env(safe-area-inset-left)) !important;
        padding-right: max(16px, env(safe-area-inset-right)) !important;
      }

      #kv-widget-input {
        font-size: 16px !important; /* Prepreči zoom na iOS */
      }

      #kv-scroll-down {
        bottom: 90px;
      }
    }

    #kv-widget-header {
      background: #ffffff;
      color: #1a1a1a;
      padding: 16px 20px;
      display: flex;
      align-items: center;
      gap: 12px;
      flex-shrink: 0;
      border-bottom: 1px solid #e8e0d8;
    }

    #kv-widget-header-icon {
      width: 48px;
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    #kv-widget-header-icon img {
      width: 48px;
      height: 48px;
      object-fit: contain;
    }

    #kv-widget-header-text {
      flex: 1;
    }

    #kv-widget-header-text h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
      color: ${CONFIG.brandColor};
    }

    #kv-widget-header-text p {
      margin: 2px 0 0;
      font-size: 12px;
      color: #6a6a6a;
    }

    .kv-header-btn {
      background: none;
      border: none;
      color: ${CONFIG.brandColor};
      cursor: pointer;
      padding: 8px;
      border-radius: 8px;
      transition: background 0.15s;
    }

    .kv-header-btn:hover {
      background: rgba(123,94,59,0.1);
    }

    .kv-header-btn svg {
      width: 18px;
      height: 18px;
      fill: ${CONFIG.brandColor};
    }

    #kv-widget-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      background: #f9f7f5;
    }

    .kv-message {
      margin-bottom: 12px;
      display: flex;
      flex-direction: column;
    }

    .kv-message.kv-bot {
      align-items: flex-start;
    }

    .kv-message.kv-user {
      align-items: flex-end;
    }

    .kv-message-bubble {
      max-width: 85%;
      padding: 12px 16px;
      border-radius: 16px;
      font-size: 14px;
      line-height: 1.5;
      word-wrap: break-word;
    }

    .kv-bot .kv-message-bubble {
      background: white;
      color: #1a1a1a;
      border-bottom-left-radius: 4px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }

    .kv-user .kv-message-bubble {
      background: ${CONFIG.brandColor};
      color: white;
      border-bottom-right-radius: 4px;
    }

    .kv-typing {
      display: flex;
      gap: 4px;
      padding: 12px 16px;
    }

    .kv-typing span {
      width: 8px;
      height: 8px;
      background: #999;
      border-radius: 50%;
      animation: kv-bounce 1.2s infinite;
    }

    .kv-typing span:nth-child(2) { animation-delay: 0.2s; }
    .kv-typing span:nth-child(3) { animation-delay: 0.4s; }

    @keyframes kv-bounce {
      0%, 60%, 100% { transform: translateY(0); }
      30% { transform: translateY(-6px); }
    }

    #kv-widget-input-area {
      padding: 12px 16px;
      background: white;
      border-top: 1px solid #eee;
      display: flex;
      gap: 10px;
      flex-shrink: 0;
    }

    #kv-widget-powered {
      text-align: center;
      font-size: 13px;
      color: #aaa;
      padding: 4px 0 6px;
      background: white;
    }
    #kv-widget-powered a {
      color: #7b5e3b;
      text-decoration: none;
    }

    #kv-widget-input {
      flex: 1;
      border: 1px solid #ddd;
      border-radius: 24px;
      padding: 12px 18px;
      font-size: 14px;
      outline: none;
      transition: border-color 0.15s;
    }

    #kv-widget-input:focus {
      border-color: ${CONFIG.brandColor};
    }

    #kv-widget-send {
      width: 44px;
      height: 44px;
      border-radius: 50%;
      background: ${CONFIG.brandColor};
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.15s;
      flex-shrink: 0;
    }

    #kv-widget-send:hover {
      background: ${CONFIG.brandColorHover};
    }

    #kv-widget-send:disabled {
      background: #ccc;
      cursor: not-allowed;
    }

    #kv-widget-send svg {
      width: 20px;
      height: 20px;
      fill: white;
    }

    /* Scroll down arrow indicator */
    #kv-scroll-down {
      position: absolute;
      bottom: 80px;
      left: 50%;
      transform: translateX(-50%);
      width: 36px;
      height: 36px;
      background: ${CONFIG.brandColor};
      border-radius: 50%;
      display: none;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 2px 8px rgba(0,0,0,0.2);
      z-index: 10;
    }

    #kv-scroll-down.kv-visible {
      display: flex;
    }

    #kv-scroll-down svg {
      width: 20px;
      height: 20px;
      fill: white;
    }

    @keyframes kv-bounce-arrow {
      0%, 100% { transform: translateX(-50%) translateY(0); }
      50% { transform: translateX(-50%) translateY(4px); }
    }

    /* Booking form overlay */
    #kv-booking-form {
      position: absolute;
      inset: 0;
      background: #fff;
      z-index: 10;
      display: none;
      flex-direction: column;
      overflow: hidden;
    }
    #kv-booking-form.kv-open { display: flex; }

    #kv-bf-header {
      background: ${CONFIG.brandColor};
      color: #fff;
      padding: 14px 16px;
      display: flex;
      align-items: center;
      gap: 10px;
      flex-shrink: 0;
    }
    #kv-bf-header h3 { margin: 0; font-size: 15px; flex: 1; }
    #kv-bf-back {
      background: rgba(255,255,255,0.2);
      border: 1px solid rgba(255,255,255,0.5);
      color: #fff;
      cursor: pointer;
      padding: 5px 10px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      white-space: nowrap;
      transition: background 0.15s;
    }
    #kv-bf-back:hover { background: rgba(255,255,255,0.35); }

    #kv-bf-body {
      flex: 1; overflow-y: auto;
      padding: 16px;
      display: flex; flex-direction: column; gap: 12px;
    }

    .kv-bf-row { display: flex; gap: 10px; }
    .kv-bf-field { display: flex; flex-direction: column; gap: 4px; flex: 1; }
    .kv-bf-field label { font-size: 12px; color: #666; font-weight: 600; }
    .kv-bf-field input, .kv-bf-field textarea, .kv-bf-field select {
      border: 1px solid #ddd; border-radius: 8px;
      padding: 9px 12px; font-size: 14px; outline: none;
      transition: border-color 0.15s; font-family: inherit;
    }
    .kv-bf-field input:focus, .kv-bf-field textarea:focus {
      border-color: ${CONFIG.brandColor};
    }
    .kv-bf-field textarea { resize: none; height: 60px; }

    /* Stepper +/- */
    .kv-stepper {
      display: flex; align-items: center; gap: 0;
      border: 1px solid #ddd; border-radius: 8px; overflow: hidden; height: 38px;
    }
    .kv-stepper button {
      width: 36px; background: #f5f0eb; border: none;
      font-size: 18px; cursor: pointer; color: ${CONFIG.brandColor};
      font-weight: 700; flex-shrink: 0; height: 100%;
      transition: background 0.15s;
    }
    .kv-stepper button:hover { background: #e8ddd0; }
    .kv-stepper span {
      flex: 1; text-align: center; font-size: 15px;
      font-weight: 600; color: #333;
    }

    /* Type tabs */
    .kv-bf-tabs { display: flex; gap: 8px; }
    .kv-bf-tab {
      flex: 1; padding: 9px; border: 2px solid #ddd;
      border-radius: 8px; background: #fff; cursor: pointer;
      font-size: 13px; font-weight: 600; color: #666;
      transition: all 0.15s; text-align: center;
    }
    .kv-bf-tab.active {
      border-color: ${CONFIG.brandColor};
      background: #fdf8f3; color: ${CONFIG.brandColor};
    }

    /* GDPR checkbox */
    .kv-bf-gdpr {
      display: flex; gap: 8px; align-items: flex-start;
      font-size: 12px; color: #888; line-height: 1.4;
    }
    .kv-bf-gdpr input { margin-top: 2px; flex-shrink: 0; }

    #kv-bf-footer {
      padding: 12px 16px;
      padding-bottom: max(12px, env(safe-area-inset-bottom));
      border-top: 1px solid #eee;
      background: #fff;
      flex-shrink: 0;
    }
    #kv-bf-submit {
      width: 100%; padding: 13px;
      background: ${CONFIG.brandColor}; color: #fff;
      border: none; border-radius: 10px; font-size: 15px;
      font-weight: 600; cursor: pointer; transition: background 0.15s;
    }
    #kv-bf-submit:hover { background: ${CONFIG.brandColorHover}; }
    #kv-bf-submit:disabled { background: #ccc; cursor: not-allowed; }

    #kv-bf-open-btn {
      width: 100%;
      padding: 10px;
      border-radius: 8px;
      border: 2px solid ${CONFIG.brandColor};
      background: #fdf8f3;
      cursor: pointer;
      font-size: 14px;
      font-weight: 600;
      color: ${CONFIG.brandColor};
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      transition: background 0.15s;
    }
    #kv-bf-open-btn:hover { background: #f0e8dc; }

    #kv-widget-input-area {
      padding: 8px 16px 4px !important;
    }
    #kv-bf-open-bar {
      padding: 0 16px 10px;
      background: white;
    }

    .kv-bf-section-title {
      font-size: 11px; font-weight: 700; color: #aaa;
      text-transform: uppercase; letter-spacing: 1px;
      margin-top: 4px;
    }

    #kv-bf-prices {
      font-size: 11px; color: #aaa; line-height: 1.6;
      background: #f9f7f5; border-radius: 6px;
      padding: 7px 10px;
    }
  `;

  // Ikone (SVG)
  const icons = {
    chat: '<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.17L4 17.17V4h16v12z"/><path d="M7 9h10v2H7zm0-3h10v2H7z"/></svg>',
    close: '<svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>',
    send: '<svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>',
    home: '<svg viewBox="0 0 24 24"><path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/></svg>',
    refresh: '<svg viewBox="0 0 24 24"><path d="M17.65 6.35A7.958 7.958 0 0012 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0112 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>',
    arrowDown: '<svg viewBox="0 0 24 24"><path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/></svg>'
  };

  // Session ID in shranjeni pogovori
  let sessionId = localStorage.getItem('kv_widget_session') || generateSessionId();
  localStorage.setItem('kv_widget_session', sessionId);

  // Naloži shranjene pogovore
  let storedMessages = [];
  try {
    const stored = localStorage.getItem('kv_widget_messages');
    if (stored) {
      storedMessages = JSON.parse(stored);
    }
  } catch (e) {
    storedMessages = [];
  }

  function generateSessionId() {
    return 'widget_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  function saveMessages() {
    // Ohrani samo zadnjih N sporočil
    const toSave = storedMessages.slice(-CONFIG.maxStoredMessages);
    localStorage.setItem('kv_widget_messages', JSON.stringify(toSave));
  }

  function clearConversation() {
    storedMessages = [];
    localStorage.removeItem('kv_widget_messages');
    // Nov session ID za nov pogovor
    sessionId = generateSessionId();
    localStorage.setItem('kv_widget_session', sessionId);
    // Počisti UI
    const messages = document.getElementById('kv-widget-messages');
    messages.innerHTML = '';
    // Dodaj welcome message
    addMessage(CONFIG.welcomeMessage, 'bot', false);
  }

  // Ustvari widget HTML
  function createWidget() {
    // Dodaj stile
    const styleEl = document.createElement('style');
    styleEl.textContent = styles;
    document.head.appendChild(styleEl);

    // LAUNCHER — en sam position:fixed element
    const launcher = document.createElement('div');
    launcher.id = 'kv-launcher';

    // Greeting kartice — VSE inline styles, nobenega zanašanja na CSS sheet
    var cardStyle = [
      'display:block',
      'background:#ffffff',
      'color:#7b5e3b',
      'font-size:14px',
      'font-family:-apple-system,BlinkMacSystemFont,sans-serif',
      'font-weight:600',
      'padding:10px 16px',
      'border-radius:18px 18px 4px 18px',
      'box-shadow:0 2px 12px rgba(0,0,0,0.13)',
      'cursor:pointer',
      'border:1px solid rgba(123,94,59,0.18)',
      'max-width:220px',
      'text-align:right',
      'touch-action:manipulation',
      '-webkit-tap-highlight-color:transparent',
      'margin-bottom:8px',
      'line-height:1.4',
    ].join(';');

    var closeStyle = [
      'display:block',
      'background:#fff',
      'color:#7b5e3b',
      'border:1px solid rgba(123,94,59,0.2)',
      'border-radius:50%',
      'width:24px',
      'height:24px',
      'font-size:13px',
      'cursor:pointer',
      'touch-action:manipulation',
      '-webkit-tap-highlight-color:transparent',
      'margin-bottom:6px',
      'margin-left:auto',
      'line-height:22px',
      'text-align:center',
      'padding:0',
    ].join(';');

    const greetingCards = document.createElement('div');
    greetingCards.id = 'kv-greeting-cards';
    greetingCards.setAttribute('style', [
      'position:fixed',
      'bottom:90px',
      'right:0',
      'z-index:2147483647',
      'display:none',
      'flex-direction:column',
      'align-items:flex-end',
      'padding-right:0',
    ].join(';'));

    var xBtn = document.createElement('button');
    xBtn.setAttribute('style', closeStyle + ';margin-right:6px');
    xBtn.textContent = '✕';
    xBtn.onclick = function(e) { e.stopPropagation(); e.preventDefault(); hideCards(); };
    greetingCards.appendChild(xBtn);

    ['Pozdravljeni 👋', 'Sem vaš pomočnik Domačije Kovačnik.', 'Kako vam lahko pomagam?'].forEach(function(text) {
      var btn = document.createElement('button');
      btn.setAttribute('style', cardStyle);
      btn.textContent = text;
      btn.onclick = function(e) { e.stopPropagation(); e.preventDefault(); setTimeout(openPanel, 0); };
      greetingCards.appendChild(btn);
    });

    // Bubble — button (iOS 1-tap)
    const bubble = document.createElement('button');
    bubble.id = 'kv-widget-bubble';
    bubble.innerHTML = icons.chat;
    bubble.onclick = function(e) {
      e.stopPropagation();
      e.preventDefault();
      setTimeout(togglePanel, 0);
    };

    // Panel
    const panel = document.createElement('div');
    panel.id = 'kv-widget-panel';
    panel.innerHTML = `
      <div id="kv-widget-header">
        <div id="kv-widget-header-icon"><img src="https://kovacnik.com/wp-content/uploads/2023/03/LOGO-KOVACNIK-2023.png" alt="Kovačnik"></div>
        <div id="kv-widget-header-text">
          <h3>${CONFIG.title}</h3>
          <p>${CONFIG.subtitle}</p>
        </div>
        <button class="kv-header-btn" id="kv-widget-refresh" title="Nov pogovor">${icons.refresh}</button>
        <button class="kv-header-btn" id="kv-widget-close" title="Zapri">${icons.close}</button>
      </div>
      <div id="kv-widget-messages"></div>
      <div id="kv-scroll-down" title="Scroll dol">${icons.arrowDown}</div>
      <div id="kv-widget-input-area">
        <input type="text" id="kv-widget-input" placeholder="${CONFIG.placeholder}">
        <button id="kv-widget-send">${icons.send}</button>
      </div>
      <div id="kv-bf-open-bar">
        <button id="kv-bf-open-btn">📅 Rezerviraj sobo ali mizo</button>
      </div>
      <div id="kv-widget-powered">built by: <a href="https://spoznaj-ai.si" target="_blank">spoznaj-ai.si</a></div>
    `;

    // Booking form overlay
    const bookingForm = document.createElement('div');
    bookingForm.id = 'kv-booking-form';
    bookingForm.innerHTML = `
      <div id="kv-bf-header">
        <button id="kv-bf-back">&#8592; Nazaj v pogovor</button>
        <h3>Rezervacija</h3>
      </div>
      <div id="kv-bf-body">
        <div class="kv-bf-tabs">
          <button class="kv-bf-tab active" data-type="room">🛏️ Soba</button>
          <button class="kv-bf-tab" data-type="table">🍽️ Miza</button>
        </div>

        <div id="kv-bf-prices"></div>

        <div id="kv-bf-meal-type-wrap" style="display:none">
          <div class="kv-bf-field">
            <label>Vrsta rezervacije *</label>
            <select id="kv-bf-meal-type">
              <option value="vikend">Vikend ponudba (sob–ned, 36 €)</option>
              <option value="tedenska">Tedenska ponudba (sre–pet, min. 6 oseb)</option>
              <option value="brunch">Brunch (samo po dogovoru, od 20 €/os)</option>
            </select>
          </div>
        </div>

        <div class="kv-bf-row">
          <div class="kv-bf-field">
            <label>Datum *</label>
            <input type="date" id="kv-bf-date" required>
          </div>
          <div class="kv-bf-field" id="kv-bf-nights-wrap">
            <label>Število noči</label>
            <div class="kv-stepper">
              <button type="button" data-step="nights" data-dir="-1">−</button>
              <span id="kv-bf-nights-val">2</span>
              <button type="button" data-step="nights" data-dir="1">+</button>
            </div>
          </div>
          <div class="kv-bf-field" id="kv-bf-time-wrap" style="display:none">
            <label>Ura prihoda</label>
            <input type="time" id="kv-bf-time" value="12:00">
          </div>
        </div>

        <div class="kv-bf-section-title">Gostje</div>
        <div class="kv-bf-row">
          <div class="kv-bf-field">
            <label>Odrasli</label>
            <div class="kv-stepper">
              <button type="button" data-step="adults" data-dir="-1">−</button>
              <span id="kv-bf-adults-val">2</span>
              <button type="button" data-step="adults" data-dir="1">+</button>
            </div>
          </div>
          <div class="kv-bf-field">
            <label>Otroci (do 12 let)</label>
            <div class="kv-stepper">
              <button type="button" data-step="children" data-dir="-1">−</button>
              <span id="kv-bf-children-val">0</span>
              <button type="button" data-step="children" data-dir="1">+</button>
            </div>
          </div>
        </div>

        <div id="kv-bf-children-ages-wrap" style="display:none">
          <div class="kv-bf-field">
            <label>Starosti otrok (npr. 5, 8)</label>
            <input type="text" id="kv-bf-children-ages" placeholder="npr. 5, 8">
          </div>
        </div>

        <div class="kv-bf-section-title">Vaši podatki</div>
        <div class="kv-bf-row">
          <div class="kv-bf-field">
            <label>Ime in priimek *</label>
            <input type="text" id="kv-bf-name" placeholder="Janez Novak" required>
          </div>
        </div>
        <div class="kv-bf-row">
          <div class="kv-bf-field">
            <label>Telefon *</label>
            <input type="tel" id="kv-bf-phone" placeholder="031 123 456" required>
          </div>
          <div class="kv-bf-field">
            <label>Email</label>
            <input type="email" id="kv-bf-email" placeholder="janez@email.com">
          </div>
        </div>

        <div id="kv-bf-dinner-wrap" class="kv-bf-field">
          <label>
            <input type="checkbox" id="kv-bf-dinner" style="margin-right:6px">
            Večerja — 30 €/odrasla oseba, 15 €/otrok do 12 let (pon/tor ni)
          </label>
        </div>

        <div class="kv-bf-field">
          <label>Posebnosti / opombe</label>
          <textarea id="kv-bf-note" placeholder="Alergije, posebne želje..."></textarea>
        </div>

        <div class="kv-bf-gdpr">
          <input type="checkbox" id="kv-bf-gdpr" required>
          <span>Strinjam se z obdelavo osebnih podatkov za namen rezervacije. Podatki se hranijo izključno za potrebe rezervacije pri Domačiji Kovačnik.</span>
        </div>
        <div style="background:#fff8f0;border:1px solid #e8d5b7;border-radius:8px;padding:10px 14px;font-size:12px;color:#8b6343;margin-top:8px;">
          ⚠️ <strong>Obrazec NI potrditev rezervacije.</strong> Po oddaji vas kontaktiramo in skupaj potrdimo ali prilagodimo termin.
        </div>
      </div>
      <div id="kv-bf-footer">
        <button id="kv-bf-submit">Pošlji povpraševanje →</button>
      </div>
    `;
    panel.appendChild(bookingForm);

    // Launcher: samo bubble
    launcher.appendChild(bubble);
    document.body.appendChild(launcher);
    // Kartice direktno na body (bypass WP stacking context)
    document.body.appendChild(greetingCards);
    // Panel direktno na body (full-screen na mobile)
    document.body.appendChild(panel);

    // Blokiraj WP document click handlerje kadar je panel odprt
    panel.addEventListener('click', function(e) { e.stopPropagation(); });
    greetingCards.addEventListener('click', function(e) { e.stopPropagation(); });
    launcher.addEventListener('click', function(e) { e.stopPropagation(); });

    // Event listeners - chat
    document.getElementById('kv-widget-close').onclick = closePanel;
    document.getElementById('kv-widget-refresh').onclick = clearConversation;
    document.getElementById('kv-widget-send').onclick = sendMessage;
    document.getElementById('kv-widget-input').onkeypress = function(e) {
      if (e.key === 'Enter') sendMessage();
    };

    // Booking form - type tabs
    let bookingType = 'room';
    let stepValues = { nights: 2, adults: 2, children: 0 };
    const stepMin = { nights: 1, adults: 1, children: 0 };
    const stepMax = { nights: 14, adults: 10, children: 6 };

    var pricesRoom = '50 €/os/noč z zajtrkom (min. 2 osebi, 2 noči) &nbsp;·&nbsp; otroci do 3 let brezplačno &nbsp;·&nbsp; do 12 let 50% popust &nbsp;·&nbsp; večerja 30 €/odrasla oseba, 15 €/otrok do 12 let';
    var pricesTable = 'Vikend: <a href="https://kovacnik.com/vikend-ponudba/" target="_blank" style="color:#7b5e3b;font-weight:600">kovacnik.com/vikend-ponudba/</a> &nbsp;·&nbsp; Teden: <a href="https://kovacnik.com/tedenska-ponudba/" target="_blank" style="color:#7b5e3b;font-weight:600">kovacnik.com/tedenska-ponudba/</a> &nbsp;·&nbsp; Brunch: od 20 €/os, po dogovoru';

    function updateFormForType() {
      var isRoom = bookingType === 'room';
      document.getElementById('kv-bf-meal-type-wrap').style.display = isRoom ? 'none' : '';
      document.getElementById('kv-bf-nights-wrap').style.display = isRoom ? '' : 'none';
      document.getElementById('kv-bf-time-wrap').style.display = isRoom ? 'none' : '';
      document.getElementById('kv-bf-dinner-wrap').style.display = isRoom ? '' : 'none';
      document.getElementById('kv-bf-prices').innerHTML = isRoom ? pricesRoom : pricesTable;
    }
    updateFormForType();

    document.querySelectorAll('.kv-bf-tab').forEach(function(tab) {
      tab.onclick = function() {
        document.querySelectorAll('.kv-bf-tab').forEach(function(t) { t.classList.remove('active'); });
        tab.classList.add('active');
        bookingType = tab.dataset.type;
        updateFormForType();
      };
    });

    // Steppers
    document.querySelectorAll('[data-step]').forEach(function(btn) {
      btn.onclick = function() {
        var key = btn.dataset.step;
        var dir = parseInt(btn.dataset.dir);
        stepValues[key] = Math.min(stepMax[key], Math.max(stepMin[key], stepValues[key] + dir));
        document.getElementById('kv-bf-' + key + '-val').textContent = stepValues[key];
        // Pokaži/skrij starosti otrok
        if (key === 'children') {
          document.getElementById('kv-bf-children-ages-wrap').style.display = stepValues.children > 0 ? '' : 'none';
        }
      };
    });

    // Nastavi min datum na danes
    var today = new Date().toISOString().split('T')[0];
    document.getElementById('kv-bf-date').min = today;

    // Open booking form button — onmousedown+preventDefault prepreči focus-loss (dvojni klik)
    document.getElementById('kv-bf-open-btn').onmousedown = function(e) {
      e.preventDefault();
    };
    document.getElementById('kv-bf-open-btn').onclick = function(e) {
      e.preventDefault();
      document.getElementById('kv-booking-form').classList.add('kv-open');
    };

    // Back button
    document.getElementById('kv-bf-back').onclick = function() {
      document.getElementById('kv-booking-form').classList.remove('kv-open');
    };

    // Submit booking form
    async function submitBookingForm() {
      var date = document.getElementById('kv-bf-date').value;
      var name = document.getElementById('kv-bf-name').value.trim();
      var phone = document.getElementById('kv-bf-phone').value.trim();
      var gdpr = document.getElementById('kv-bf-gdpr').checked;

      if (!date) { alert('Izberite datum prihoda.'); return; }
      if (!name) { alert('Vnesite ime in priimek.'); return; }
      if (!phone) { alert('Vnesite telefonsko številko.'); return; }
      if (!gdpr) { alert('Potrdite soglasje za obdelavo osebnih podatkov.'); return; }

      var submitBtn = document.getElementById('kv-bf-submit');
      submitBtn.disabled = true;
      submitBtn.textContent = 'Pošiljam...';

      // Parse children ages
      var childrenAgesRaw = document.getElementById('kv-bf-children-ages').value;
      var childrenAges = [];
      if (childrenAgesRaw.trim()) {
        childrenAges = childrenAgesRaw.split(/[,\s]+/).map(function(x) {
          return parseInt(x);
        }).filter(function(x) { return !isNaN(x); });
      }

      var payload = {
        session_id: sessionId,
        booking_type: bookingType,
        date: date,
        nights: bookingType === 'room' ? stepValues.nights : null,
        time: bookingType === 'table' ? document.getElementById('kv-bf-time').value : null,
        meal_type: bookingType === 'table' ? document.getElementById('kv-bf-meal-type').value : null,
        adults: stepValues.adults,
        children: stepValues.children,
        children_ages: childrenAges,
        name: name,
        phone: phone,
        email: document.getElementById('kv-bf-email').value.trim(),
        dinner: bookingType === 'room' ? document.getElementById('kv-bf-dinner').checked : false,
        note: document.getElementById('kv-bf-note').value.trim(),
        gdpr: gdpr
      };

      try {
        var response = await fetch(CONFIG.apiUrl + '/quick-booking', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        var data = await response.json();

        document.getElementById('kv-booking-form').classList.remove('kv-open');

        if (data.ok) {
          addMessage('✅ Rezervacija sprejeta! (ID: #' + data.reservation_id + ')\n\nKmalu boste prejeli potrditev. Se vidimo na Domačiji Kovačnik! 🏡', 'bot');
        } else {
          addMessage('⚠️ ' + (data.error || 'Napaka pri pošiljanju rezervacije. Pokličite nas na 031 330 113.'), 'bot');
        }
      } catch (err) {
        document.getElementById('kv-booking-form').classList.remove('kv-open');
        addMessage('⚠️ Napaka pri pošiljanju. Pokličite nas na 031 330 113.', 'bot');
        console.error('[KV Widget] Booking error:', err);
      }

      submitBtn.disabled = false;
      submitBtn.textContent = 'Pošlji rezervacijo ✓';
    }

    document.getElementById('kv-bf-submit').onclick = submitBookingForm;

    // Scroll arrow functionality
    const messagesEl = document.getElementById('kv-widget-messages');
    const scrollArrow = document.getElementById('kv-scroll-down');

    scrollArrow.onclick = function() {
      messagesEl.scrollTop = messagesEl.scrollHeight;
    };

    messagesEl.onscroll = function() {
      const isNearBottom = messagesEl.scrollHeight - messagesEl.scrollTop - messagesEl.clientHeight < 50;
      if (isNearBottom) {
        scrollArrow.classList.remove('kv-visible');
      }
    };

    // Naloži shranjene pogovore ali welcome message (brez auto-scroll)
    if (storedMessages.length > 0) {
      storedMessages.forEach(function(msg) {
        addMessageToUI(msg.text, msg.sender, false);  // false = ne scrollaj
      });
    } else {
      addMessageToUI(CONFIG.welcomeMessage, 'bot', false);  // false = ne scrollaj
    }

    // Pokaži kartice po kratkem zamiku
    setTimeout(function() {
      if (!panelOpen) showCards();
    }, 800);

    // Auto-odpri panel na desktopu po zamiku
    if (CONFIG.autoOpenDesktop && window.innerWidth > CONFIG.mobileBreakpoint) {
      setTimeout(function() {
        if (!panelOpen) openPanel();
      }, CONFIG.autoOpenDelay || 1500);
    }
  }

  var panelOpen = false;

  function showCards() {
    var c = document.getElementById('kv-greeting-cards');
    if (c) c.style.display = 'flex';
  }

  function hideCards() {
    var c = document.getElementById('kv-greeting-cards');
    if (c) c.style.display = 'none';
  }

  function togglePanel() {
    if (panelOpen) {
      closePanel();
    } else {
      openPanel();
    }
  }

  function openPanel() {
    if (panelOpen) return;
    panelOpen = true;
    var panel = document.getElementById('kv-widget-panel');
    // Inline styles + class (mobile media query zahteva kv-open class)
    panel.classList.add('kv-open');
    panel.style.opacity = '1';
    panel.style.visibility = 'visible';
    panel.style.transform = 'translateY(0)';
    // Na mobilnem: full screen
    if (window.innerWidth <= CONFIG.mobileBreakpoint) {
      panel.style.position = 'fixed';
      panel.style.inset = '0';
      panel.style.width = '100%';
      panel.style.height = '100%';
      panel.style.maxHeight = 'none';
      panel.style.borderRadius = '0';
      panel.style.bottom = '0';
      panel.style.right = '0';
      panel.style.top = '0';
      panel.style.left = '0';
      document.body.style.overflow = 'hidden';
    }
    hideCards();
    document.getElementById('kv-widget-bubble').classList.remove('kv-has-notification');
    document.getElementById('kv-widget-bubble').style.display = 'none';
    document.getElementById('kv-widget-input').focus();
    localStorage.setItem('kv_widget_open', 'true');
    var messages = document.getElementById('kv-widget-messages');
    var scrollArrow = document.getElementById('kv-scroll-down');
    if (messages.scrollHeight > messages.clientHeight) {
      scrollArrow.classList.add('kv-visible');
    }
  }

  function closePanel() {
    if (!panelOpen) return;
    panelOpen = false;
    var panel = document.getElementById('kv-widget-panel');
    panel.classList.remove('kv-open');
    panel.style.opacity = '0';
    panel.style.visibility = 'hidden';
    panel.style.transform = 'translateY(8px)';
    document.body.style.overflow = '';
    localStorage.setItem('kv_widget_open', 'false');
    document.getElementById('kv-widget-bubble').style.display = '';
    showCards();
  }

  function addMessageToUI(text, sender, autoScroll = true) {
    const messages = document.getElementById('kv-widget-messages');
    const scrollArrow = document.getElementById('kv-scroll-down');

    const msg = document.createElement('div');
    msg.className = 'kv-message kv-' + sender;
    msg.innerHTML = '<div class="kv-message-bubble">' + escapeHtml(text) + '</div>';
    messages.appendChild(msg);

    // Če je autoScroll false (pri nalaganju), ne scrollaj
    if (!autoScroll) return;

    // Ko pošlješ novo sporočilo, VEDNO scrollaj na dno da vidiš pogovor
    messages.scrollTop = messages.scrollHeight;
    // Skrij puščico ker smo na dnu
    if (scrollArrow) {
      scrollArrow.classList.remove('kv-visible');
    }
  }

  function addMessage(text, sender, save = true) {
    addMessageToUI(text, sender);
    if (save) {
      storedMessages.push({ text: text, sender: sender, time: Date.now() });
      saveMessages();
    }
  }

  function showTyping() {
    const messages = document.getElementById('kv-widget-messages');
    const scrollArrow = document.getElementById('kv-scroll-down');

    const typing = document.createElement('div');
    typing.id = 'kv-typing-indicator';
    typing.className = 'kv-message kv-bot';
    typing.innerHTML = '<div class="kv-message-bubble kv-typing"><span></span><span></span><span></span></div>';
    messages.appendChild(typing);

    // Vedno scrollaj na dno ko se pokaže typing
    messages.scrollTop = messages.scrollHeight;
    if (scrollArrow) {
      scrollArrow.classList.remove('kv-visible');
    }
  }

  function hideTyping() {
    const typing = document.getElementById('kv-typing-indicator');
    if (typing) typing.remove();
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML.replace(/\n/g, '<br>');
  }

  async function sendMessage() {
    const input = document.getElementById('kv-widget-input');
    const sendBtn = document.getElementById('kv-widget-send');
    const text = input.value.trim();

    if (!text) return;

    // Dodaj user message
    addMessage(text, 'user');
    input.value = '';
    sendBtn.disabled = true;

    // Pokaži typing indicator
    showTyping();

    try {
      const response = await fetch(CONFIG.apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          session_id: sessionId
        })
      });

      hideTyping();

      if (!response.ok) throw new Error('API error');

      const data = await response.json();
      const reply = data.reply || data.response || data.message || 'Oprostite, prišlo je do napake.';
      addMessage(reply, 'bot');
      var bookingAction = data.action;
      var bookingHint = data.booking_type_hint;

    } catch (err) {
      hideTyping();
      addMessage('Oprostite, trenutno ni mogoče vzpostaviti povezave. Poskusite ponovno.', 'bot');
      console.error('[KV Widget] Error:', err);
      return;
    }

    // Odpri booking formo IZVEN try-catch — JS napaka ne sme prekriti bot odgovora
    if (bookingAction === 'open_booking_form') {
      try {
        var hint = bookingHint || 'room';
        var tabType = (hint === 'room') ? 'room' : 'table';
        document.querySelectorAll('.kv-bf-tab').forEach(function(t) { t.classList.remove('active'); });
        var activeTab = document.querySelector('.kv-bf-tab[data-type="' + tabType + '"]');
        if (activeTab) {
          activeTab.classList.add('active');
          bookingType = tabType;
          updateFormForType();
        }
        if (hint === 'brunch') {
          var mealSelect = document.getElementById('kv-bf-meal-type');
          if (mealSelect) mealSelect.value = 'brunch';
        }
        setTimeout(function() {
          var form = document.getElementById('kv-booking-form');
          if (form) form.classList.add('kv-open');
        }, 400);
      } catch (formErr) {
        console.error('[KV Widget] Forma napaka:', formErr);
      }
    }

    sendBtn.disabled = false;
    input.focus();
  }

  // Zaženi widget ko je DOM pripravljen — defer za WordPress kompatibilnost
  function initWidget() {
    if (document.getElementById('kv-widget-container')) return; // že inicializiran
    createWidget();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWidget);
  } else {
    // requestAnimationFrame zagotovi da je WP DOM settled
    requestAnimationFrame(initWidget);
  }
})();
