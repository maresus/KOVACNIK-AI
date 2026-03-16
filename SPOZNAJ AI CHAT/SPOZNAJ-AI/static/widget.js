(function () {
  if (document.getElementById('spoznajai-widget')) return;

  const API_URL = document.currentScript?.getAttribute('data-api') || 'https://tvoj-server.com';

  const style = document.createElement('style');
  style.textContent = `
    #spoznajai-btn {
      position: fixed;
      bottom: 28px;
      right: 28px;
      width: 58px;
      height: 58px;
      border-radius: 50%;
      background: #afd037;
      color: #001f2d;
      border: none;
      cursor: pointer;
      font-size: 11px;
      font-weight: 800;
      font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
      letter-spacing: 0.3px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 20px rgba(175,208,55,0.45);
      z-index: 9998;
      transition: transform 0.2s, box-shadow 0.2s;
    }
    #spoznajai-btn:hover {
      transform: scale(1.08);
      box-shadow: 0 6px 28px rgba(175,208,55,0.55);
    }
    #spoznajai-popup {
      position: fixed;
      bottom: 100px;
      right: 28px;
      width: 370px;
      height: 520px;
      border-radius: 18px;
      overflow: hidden;
      box-shadow: 0 20px 60px rgba(0,0,0,0.45);
      z-index: 9999;
      border: 1px solid rgba(255,255,255,0.08);
      display: none;
      transition: opacity 0.2s;
    }
    #spoznajai-popup.open {
      display: block;
    }
    @media (max-width: 480px) {
      #spoznajai-popup {
        width: calc(100vw - 20px);
        height: calc(100vh - 120px);
        bottom: 90px;
        right: 10px;
      }
      #spoznajai-btn {
        bottom: 20px;
        right: 16px;
      }
    }
  `;
  document.head.appendChild(style);

  const btn = document.createElement('button');
  btn.id = 'spoznajai-btn';
  btn.innerHTML = 'AI';
  btn.title = 'Pogovorite se z nami';
  document.body.appendChild(btn);

  const iframe = document.createElement('iframe');
  iframe.id = 'spoznajai-popup';
  iframe.src = API_URL + '/widget';
  iframe.allow = 'clipboard-write';
  document.body.appendChild(iframe);

  let open = false;
  btn.addEventListener('click', () => {
    open = !open;
    iframe.classList.toggle('open', open);
    btn.innerHTML = open ? '✕' : 'AI';
  });
})();
