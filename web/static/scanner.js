(function () {
  const token = window.SCAN_TOKEN;
  if (!token) return;

  function setEl(id, html) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = html;
  }

  function setElText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function collectScreen() {
    return {
      width: window.screen.width,
      height: window.screen.height,
      availWidth: window.screen.availWidth,
      availHeight: window.screen.availHeight,
      colorDepth: window.screen.colorDepth,
      pixelRatio: window.devicePixelRatio || 1,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      timezoneOffset: new Date().getTimezoneOffset(),
      language: navigator.language,
      languages: (navigator.languages || []).join(','),
      platform: navigator.platform,
      hardwareConcurrency: navigator.hardwareConcurrency || 0,
      maxTouchPoints: navigator.maxTouchPoints || 0,
      cookieEnabled: navigator.cookieEnabled,
      doNotTrack: navigator.doNotTrack,
    };
  }

  // Returns a human-readable OS string using User-Agent Client Hints (CH),
  // which is the only way to distinguish Windows 11 from Windows 10.
  // Brave is Chromium-based and supports userAgentData.
  async function getClientHints() {
    const result = { osHint: null, browserHint: null };
    try {
      // --- Brave detection (must be async) ---
      if (navigator.brave && typeof navigator.brave.isBrave === 'function') {
        const isBrave = await navigator.brave.isBrave();
        if (isBrave) {
          result.browserHint = 'Brave';
        }
      }

      // --- OS via Client Hints ---
      if (!navigator.userAgentData) return result;
      const data = await navigator.userAgentData.getHighEntropyValues(
        ['platform', 'platformVersion', 'fullVersionList']
      );
      const platform = data.platform || '';

      if (platform === 'Windows') {
        // Windows 11 reports platformVersion >= 13.0.0; Windows 10 reports 0.x.x–12.x.x
        const major = parseInt((data.platformVersion || '0').split('.')[0], 10);
        result.osHint = major >= 13 ? 'Windows 11' : 'Windows 10';
      } else if (platform === 'macOS') {
        result.osHint = 'macOS ' + (data.platformVersion || '');
      } else if (platform) {
        result.osHint = platform + (data.platformVersion ? ' ' + data.platformVersion : '');
      }

      // --- Browser version from fullVersionList (overrides UA parser) ---
      if (!result.browserHint && data.fullVersionList && data.fullVersionList.length) {
        // fullVersionList example: [{brand:'Chromium',version:'...'},{brand:'Google Chrome',version:'...'}]
        const preferred = data.fullVersionList.find(
          e => !e.brand.includes('Not') && !e.brand.includes('Brand')
        );
        if (preferred) {
          const major = preferred.version.split('.')[0];
          result.browserHint = preferred.brand + ' ' + major;
        }
      }
    } catch (e) {
      // Client Hints unavailable
    }
    return result;
  }

  function canvasFingerprint() {
    try {
      const canvas = document.createElement('canvas');
      canvas.width = 200;
      canvas.height = 40;
      const ctx = canvas.getContext('2d');
      ctx.font = '14px "JetBrains Mono", monospace';
      ctx.fillStyle = '#00ff88';
      ctx.fillText('TGScanner::fingerprint', 4, 24);
      ctx.fillStyle = '#ff0066';
      ctx.fillRect(160, 8, 24, 16);
      return canvas.toDataURL().slice(-80);
    } catch (e) {
      return 'unavailable';
    }
  }

  function audioFingerprint() {
    return new Promise(function (resolve) {
      try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) { resolve('unavailable'); return; }
        const ctx = new AudioCtx();
        const oscillator = ctx.createOscillator();
        const analyser = ctx.createAnalyser();
        const gain = ctx.createGain();
        gain.gain.value = 0;
        oscillator.type = 'triangle';
        oscillator.frequency.value = 10000;
        oscillator.connect(analyser);
        analyser.connect(gain);
        gain.connect(ctx.destination);
        oscillator.start(0);
        setTimeout(function () {
          const buf = new Float32Array(analyser.frequencyBinCount);
          analyser.getFloatFrequencyData(buf);
          let sum = 0;
          for (let i = 0; i < buf.length; i++) sum += Math.abs(buf[i]);
          oscillator.stop();
          ctx.close();
          resolve(sum.toFixed(4));
        }, 100);
      } catch (e) {
        resolve('unavailable');
      }
    });
  }

  function detectWebRTCLeaks() {
    return new Promise(function (resolve) {
      try {
        const RTCPeer = window.RTCPeerConnection || window.webkitRTCPeerConnection;
        if (!RTCPeer) { resolve([]); return; }
        const pc = new RTCPeer({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] });
        const ips = [];
        const ipRe = /(\d{1,3}(\.\d{1,3}){3})/;
        const timer = setTimeout(function () {
          pc.close();
          resolve(ips);
        }, 4000);
        pc.onicecandidate = function (e) {
          if (!e || !e.candidate || !e.candidate.candidate) return;
          const m = e.candidate.candidate.match(ipRe);
          if (m && ips.indexOf(m[1]) === -1) ips.push(m[1]);
        };
        pc.createDataChannel('');
        pc.createOffer().then(function (offer) {
          return pc.setLocalDescription(offer);
        }).catch(function () {
          clearTimeout(timer);
          pc.close();
          resolve([]);
        });
      } catch (e) {
        resolve([]);
      }
    });
  }

  function djb2(str) {
    let hash = 5381;
    for (let i = 0; i < str.length; i++) {
      hash = ((hash << 5) + hash) + str.charCodeAt(i);
      hash = hash & hash;
    }
    return Math.abs(hash).toString(16).padStart(8, '0');
  }

  function calculateScore(screen, canvasHash, audioHash) {
    const popularRes = ['1920x1080', '1366x768', '1280x720', '1440x900', '1536x864'];
    const res = screen.width + 'x' + screen.height;
    let score = 0;
    if (popularRes.indexOf(res) === -1) score += 2;
    if (canvasHash !== 'unavailable') score += 3;
    if (audioHash !== 'unavailable') score += 2;
    if (screen.timezoneOffset !== 0) score += 1;
    if (screen.language && !screen.language.startsWith('en')) score += 1;
    if (screen.hardwareConcurrency > 4) score += 1;
    return Math.round((score / 10) * 100);
  }

  async function run() {
    const screen = collectScreen();

    setElText('screen-res', screen.width + ' \u00d7 ' + screen.height + ' (\u00d7' + screen.pixelRatio + ')');
    setElText('timezone', screen.timezone || '\u2014');
    setElText('color-depth', screen.colorDepth + '-bit');

    const [canvasHash, audioHash, ips, hints] = await Promise.all([
      Promise.resolve(canvasFingerprint()),
      audioFingerprint(),
      detectWebRTCLeaks(),
      getClientHints(),
    ]);

    // Override OS display if Client Hints gave us a precise value
    if (hints.osHint) {
      setElText('os-hint', hints.osHint);
    }
    // Override browser display (Brave or exact version from fullVersionList)
    if (hints.browserHint) {
      setElText('browser-hint', hints.browserHint);
    }

    if (ips.length === 0) {
      setEl('webrtc-result', '<span class="status-ok">\u0423\u0442\u0435\u0447\u0435\u043a \u043d\u0435 \u043e\u0431\u043d\u0430\u0440\u0443\u0436\u0435\u043d\u043e \u2713</span>');
    } else {
      setEl('webrtc-result', '<span class="status-warn">\u26a0 \u041e\u0431\u043d\u0430\u0440\u0443\u0436\u0435\u043d\u044b IP: ' + ips.join(', ') + '</span>');
    }

    const fpRaw = canvasHash + '|' + audioHash + '|' + screen.width + '|' + screen.height + '|' + screen.colorDepth + '|' + screen.timezone;
    const fpHash = djb2(fpRaw);
    const score = calculateScore(screen, canvasHash, audioHash);

    setEl('fp-hash', '<span style="font-size:12px;word-break:break-all;">' + fpHash + '</span>');
    const color = score >= 70 ? 'var(--pink)' : score >= 40 ? 'var(--blue)' : 'var(--green)';
    setEl('fp-score', '<span style="color:' + color + '">' + score + '%</span> <span style="font-size:11px;color:var(--muted);">(\u043e\u0446\u0435\u043d\u043a\u0430 \u0443\u043d\u0438\u043a\u0430\u043b\u044c\u043d\u043e\u0441\u0442\u0438)</span>');

    try {
      await fetch('/scan/' + token + '/client', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          screen: screen,
          webrtc_ips: ips,
          fingerprint_hash: fpHash,
          fingerprint_score: score / 100,
          os_hint: hints.osHint || '',
          browser_hint: hints.browserHint || '',
        }),
      });
    } catch (e) {
      // network error \u2014 don't break UI
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();
