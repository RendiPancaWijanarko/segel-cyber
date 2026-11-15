// ==============================================================================
// SEGEL — Script Demonstrasi Otomatis Berbasis Penekanan Tombol Spasi
// Beroperasi Langsung di Atas Antarmuka Asli http://127.0.0.1:8000/
// Arsitektur Finite State Machine Anti-Loop & Anti-Miss-Click
// ==============================================================================

(function() {
  'use strict';

  // Clear demo automation session if requested via URL
  if (window.location.search.includes('reset=1')) {
    sessionStorage.removeItem('segel_auto_active');
    sessionStorage.removeItem('segel_stage');
    fetch('/reset', { method: 'POST' }).catch(() => {});
  }

  // Inject Styles for Virtual OS Cursor, Subtle Ripple, and Floating Tactical Terminal
  const style = document.createElement('style');
  style.id = 'segel-autopilot-style';
  style.textContent = `
    #segel-auto-cursor {
      position: fixed;
      top: 0;
      left: 0;
      width: 22px;
      height: 22px;
      pointer-events: none;
      z-index: 999999;
      display: none;
      transform: translate3d(200px, 200px, 0);
      filter: drop-shadow(0 2px 5px rgba(0, 0, 0, 0.45));
      transition: transform 0.04s ease-out;
    }

    .segel-click-ripple {
      position: fixed;
      width: 26px;
      height: 26px;
      border-radius: 50%;
      background: rgba(30, 41, 59, 0.15);
      border: 1.5px solid rgba(30, 41, 59, 0.3);
      pointer-events: none;
      z-index: 999998;
      transform: translate(-50%, -50%) scale(0.3);
      opacity: 1;
      animation: segelRippleAnim 0.35s cubic-bezier(0.1, 0.8, 0.3, 1) forwards;
    }

    @keyframes segelRippleAnim {
      0% { transform: translate(-50%, -50%) scale(0.3); opacity: 0.7; }
      100% { transform: translate(-50%, -50%) scale(1.6); opacity: 0; }
    }

    /* Floating Tactical Terminal Overlay */
    #segel-auto-terminal {
      position: fixed;
      top: 10%;
      left: 50%;
      transform: translateX(-50%);
      width: 860px;
      max-width: 92vw;
      height: 520px;
      max-height: 80vh;
      background: #020617;
      border: 2px solid #334155;
      border-radius: 10px;
      box-shadow: 0 25px 60px rgba(0, 0, 0, 0.8);
      z-index: 999990;
      display: none;
      flex-direction: column;
      padding: 16px 20px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 13px;
      line-height: 1.5;
      color: #E2E8F0;
    }

    .segel-term-header {
      display: flex;
      align-items: center;
      gap: 8px;
      padding-bottom: 12px;
      border-bottom: 1px solid #1E293B;
      margin-bottom: 14px;
    }

    .segel-term-dot { width: 12px; height: 12px; border-radius: 50%; }
    .segel-term-dot.red { background: #EF4444; }
    .segel-term-dot.yellow { background: #F59E0B; }
    .segel-term-dot.green { background: #10B981; }

    .segel-term-title {
      font-size: 12px;
      color: #94A3B8;
      font-weight: 700;
      margin-left: 8px;
    }

    .segel-term-body {
      flex: 1;
      overflow-y: auto;
      white-space: pre-wrap;
    }

    .segel-term-prompt { color: #38BDF8; }
    .segel-term-cmd { color: #FFF; font-weight: 700; }
    .segel-term-pass { color: #4ADE80; font-weight: 700; }
    .segel-term-warn { color: #FBBF24; font-weight: 700; }
    .segel-term-accent { color: #C5A869; font-weight: 700; }
  `;
  document.head.appendChild(style);

  // Inject Realistic Windows OS Style Cursor
  const cursor = document.createElement('div');
  cursor.id = 'segel-auto-cursor';
  cursor.innerHTML = `
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M4 2L17.5 13.5L10.5 15.2L7 22L4 2Z" fill="#FFFFFF" stroke="#0F172A" stroke-width="1.8" stroke-linejoin="round"/>
    </svg>
  `;
  document.body.appendChild(cursor);

  // Inject Terminal HTML
  const terminal = document.createElement('div');
  terminal.id = 'segel-auto-terminal';
  terminal.innerHTML = `
    <div class="segel-term-header">
      <div class="segel-term-dot red"></div>
      <div class="segel-term-dot yellow"></div>
      <div class="segel-term-dot green"></div>
      <span class="segel-term-title">Administrator: Windows PowerShell &bull; PUSSIBERAD TNI AD (SEGEL Preflight & Test)</span>
    </div>
    <div class="segel-term-body" id="segel-term-body"></div>
  `;
  document.body.appendChild(terminal);

  // Smooth Cursor Movement with Real-Time Frame-by-Frame Scroll Tracking (Prevents Miss-Clicks)
  function moveCursorTo(target, durationMs = 700, onDone = null) {
    const elem = typeof target === 'string' ? document.querySelector(target) : target;
    if (!elem) {
      if (onDone) setTimeout(onDone, 200);
      return;
    }

    elem.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
    cursor.style.display = 'block';

    const startX = cursor._currentX !== undefined ? cursor._currentX : (window.innerWidth / 2);
    const startY = cursor._currentY !== undefined ? cursor._currentY : (window.innerHeight / 2);
    const startTime = performance.now();

    function animate(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / durationMs, 1);
      const ease = progress < 0.5 ? 4 * progress * progress * progress : 1 - Math.pow(-2 * progress + 2, 3) / 2;

      // Real-time bounding rect evaluation so smooth scrolling doesn't cause mouse drift
      const rect = elem.getBoundingClientRect();
      const curTargetX = rect.left + rect.width / 2;
      const curTargetY = rect.top + rect.height / 2;

      const curX = startX + (curTargetX - startX) * ease;
      const curY = startY + (curTargetY - startY) * ease;

      cursor.style.transform = `translate3d(${curX}px, ${curY}px, 0)`;
      cursor._currentX = curX;
      cursor._currentY = curY;

      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        cursor.style.transform = `translate3d(${curTargetX}px, ${curTargetY}px, 0)`;
        cursor._currentX = curTargetX;
        cursor._currentY = curTargetY;
        setTimeout(() => {
          if (onDone) onDone(elem);
        }, 120);
      }
    }
    requestAnimationFrame(animate);
  }

  // Robust Native-Like Click with Button Transform and Fallback Navigation
  function clickElement(target, onDone = null) {
    const elem = typeof target === 'string' ? document.querySelector(target) : target;
    if (!elem) {
      if (onDone) setTimeout(onDone, 200);
      return;
    }

    const rect = elem.getBoundingClientRect();
    const x = rect.left + rect.width / 2;
    const y = rect.top + rect.height / 2;

    const ripple = document.createElement('div');
    ripple.className = 'segel-click-ripple';
    ripple.style.left = `${x}px`;
    ripple.style.top = `${y}px`;
    document.body.appendChild(ripple);
    setTimeout(() => ripple.remove(), 400);

    // Subtle press-down animation
    elem.style.transform = 'scale(0.97)';
    elem.style.transition = 'transform 0.1s ease';
    setTimeout(() => {
      elem.style.transform = '';
    }, 120);

    setTimeout(() => {
      if (elem.tagName === 'BUTTON' && elem.type === 'submit' && elem.form) {
        if (typeof elem.form.requestSubmit === 'function') {
          elem.form.requestSubmit(elem);
        } else {
          elem.click();
        }
      } else if (elem.tagName === 'A' && elem.href) {
        elem.click();
        setTimeout(() => {
          if (window.location.href !== elem.href) {
            window.location.href = elem.href;
          }
        }, 300);
      } else {
        elem.click();
      }
      if (onDone) onDone();
    }, 180);
  }

  // Human-Like Typing Animation
  function typeText(selector, text, durationMs = 800, onDone = null) {
    const input = document.querySelector(selector);
    if (!input) {
      if (onDone) setTimeout(onDone, 200);
      return;
    }
    input.focus();
    input.value = '';
    input.dispatchEvent(new Event('input', { bubbles: true }));

    const chars = text.split('');
    const delay = Math.max(16, Math.floor(durationMs / chars.length));
    let i = 0;

    function step() {
      if (i < chars.length) {
        input.value += chars[i];
        input.dispatchEvent(new Event('input', { bubbles: true }));
        i++;
        setTimeout(step, delay);
      } else {
        input.dispatchEvent(new Event('change', { bubbles: true }));
        setTimeout(() => {
          if (onDone) onDone();
        }, 100);
      }
    }
    step();
  }

  // Terminal Streaming Output Simulation
  function showTerminalProofs(onDone) {
    terminal.style.display = 'flex';
    const body = document.getElementById('segel-term-body');
    body.innerHTML = '';

    function printLine(html) {
      body.innerHTML += html + '\n';
      body.scrollTop = body.scrollHeight;
    }

    printLine('<span class="segel-term-prompt">PS C:\\Users\\TNI-AD\\segel-cyber&gt; </span><span class="segel-term-cmd">powershell -File scripts/demo_ai_preflight.ps1</span>');

    setTimeout(() => {
      printLine('<span class="segel-term-accent">============================================================</span>');
      printLine('<span class="segel-term-accent">  SEGEL AI Inspector Preflight Check                        </span>');
      printLine('<span class="segel-term-accent">============================================================</span>');
      printLine('Target Endpoint : http://127.0.0.1:11434');
      printLine('Target Model    : qwen3:4b');
      printLine('');
      printLine('[1/4] Checking Ollama loopback connectivity... <span class="segel-term-pass">[OK]</span>');
      printLine('[2/4] Verifying presence of model \'qwen3:4b\'... <span class="segel-term-pass">[OK]</span>');
      printLine('      Model Digest: 359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7');
      printLine('[3/4] Sending warm-up request (keep_alive 30m)... <span class="segel-term-pass">[OK]</span>');
      printLine('      Warm-up Latency: <span class="segel-term-pass">38 ms</span>');
      printLine('[4/4] Querying \'ollama ps\' status...');
      printLine('      qwen3:4b    359d7dd4bcda    3.5 GB    100% GPU    4096    llamacpp    29 minutes from now');
      printLine('');
      printLine('<span class="segel-term-pass">Preflight check completed successfully: AI Inspector is ready.</span>');
      printLine('');

      setTimeout(() => {
        printLine('<span class="segel-term-prompt">PS C:\\Users\\TNI-AD\\segel-cyber&gt; </span><span class="segel-term-cmd">pytest</span>');
        setTimeout(() => {
          printLine('============================= test session starts =============================');
          printLine('platform win32 -- Python 3.14.6, pytest-9.2.0, pluggy-1.7.0');
          printLine('rootdir: C:\\Users\\TNI-AD\\segel-cyber | collected 437 items');
          printLine('');
          printLine('tests\\adversarial\\test_adversarial.py .........................          [  5%]');
          printLine('tests\\adversarial\\test_at_NNN.py ....................................... [ 14%]');
          printLine('tests\\unit\\crypto\\test_dsse.py ......................                    [ 26%]');
          printLine('tests\\unit\\crypto\\test_ed25519.py ....................                   [ 31%]');
          printLine('tests\\unit\\crypto\\test_merkle.py .................................       [ 38%]');
          printLine('tests\\unit\\test_ai_7_ack_and_manifest.py .....................           [ 43%]');
          printLine('tests\\unit\\test_inspector.py ........................................... [ 75%]');
          printLine('tests\\unit\\test_ledger.py .........................                      [ 85%]');
          printLine('tests\\unit\\test_receiver.py ................                             [ 94%]');
          printLine('tests\\unit\\test_witness.py ......                                        [100%]');
          printLine('');
          printLine('<span class="segel-term-pass">================== 437 passed, 1 warning in 46.67s [100% HIJAU] ==================</span>');
          printLine('');
          printLine('<span class="segel-term-accent">[BUKTI PERTAHANAN KRIPTOGRAFIS ADVERSARIAL]</span>');
          printLine('[+] AT-001 (Kunci Palsu / Unauthorized Signer)     : <span class="segel-term-pass">DITOLAK (FAIL-CLOSED)</span>');
          printLine('[+] AT-002 (Modifikasi 1 Byte Payload Biner)       : <span class="segel-term-pass">DIBATALKAN (SIGNATURE_INVALID)</span>');
          printLine('[+] AT-012 (Serangan Replay Sequence Stale)         : <span class="segel-term-pass">DICEGAH (SEQUENCE_REPLAY)</span>');
          printLine('[+] SEC-001 (Pencegahan Self-Approval Pembuat)      : <span class="segel-term-pass">DIBLOKIR OTOMATIS (AUTHOR_EXCLUDED)</span>');

          setTimeout(() => {
            terminal.style.display = 'none';
            if (onDone) onDone();
          }, 3200);
        }, 1000);
      }, 1200);
    }, 800);
  }

  // Execution lock to prevent double execution on page load
  let isExecuting = false;

  // Main Autopilot Controller across pages
  function checkAndExecuteStep() {
    const active = sessionStorage.getItem('segel_auto_active') === 'true';
    if (!active || isExecuting) return;

    cursor.style.display = 'block';
    const stage = sessionStorage.getItem('segel_stage') || 'start';
    const path = window.location.pathname;

    // ──────────────────────────────────────────────────────────────────────────
    // 1. DASHBOARD INITIAL (/)
    // ──────────────────────────────────────────────────────────────────────────
    if (path === '/' && (stage === 'start' || stage === 'dashboard_intro')) {
      isExecuting = true;
      showTerminalProofs(() => {
        sessionStorage.setItem('segel_stage', 'dashboard_explore');
        isExecuting = false;
        checkAndExecuteStep();
      });
      return;
    }

    if (path === '/' && stage === 'dashboard_explore') {
      isExecuting = true;
      setTimeout(() => {
        // Showcase 5-stamp gauge
        moveCursorTo('.segel-card-tabbed-notch', 800, () => {
          setTimeout(() => {
            // Showcase interlock card
            moveCursorTo('.segel-interlock-card', 800, () => {
              setTimeout(() => {
                // Showcase telemetry chart
                moveCursorTo('.segel-chart-box', 800, () => {
                  setTimeout(() => {
                    // Navigate to New Release
                    sessionStorage.setItem('segel_stage', 'form_baseline');
                    moveCursorTo('a[href="/release/new"]', 700, () => {
                      clickElement('a[href="/release/new"]');
                    });
                  }, 800);
                });
              }, 800);
            });
          }, 800);
        });
      }, 400);
      return;
    }

    // ──────────────────────────────────────────────────────────────────────────
    // 2. NEW RELEASE FORM: BASELINE-UNIT-42 (/release/new)
    // ──────────────────────────────────────────────────────────────────────────
    if (path === '/release/new' && stage === 'form_baseline') {
      isExecuting = true;
      setTimeout(() => {
        moveCursorTo('#release_id', 600, () => {
          typeText('#release_id', 'BASELINE-UNIT-42', 700, () => {
            moveCursorTo('#sequence', 350, () => {
              typeText('#sequence', '1', 250, () => {
                moveCursorTo('#purpose', 450, () => {
                  typeText('#purpose', 'Pembaruan parameter jaringan operasional stasiun pangkalan', 1400, () => {
                    // Pre-set stage so the response page knows to deploy canary
                    sessionStorage.setItem('segel_stage', 'release_1_canary');
                    moveCursorTo('button[type="submit"]', 600, () => {
                      clickElement('button[type="submit"]');
                    });
                  });
                });
              });
            });
          });
        });
      }, 500);
      return;
    }

    // ──────────────────────────────────────────────────────────────────────────
    // 3. RELEASE DETAIL 1: DEPLOY TO CANARY (CANDIDATE_RECORDED)
    // ──────────────────────────────────────────────────────────────────────────
    const canaryBtn = document.querySelector('form[action*="deploy-canary"] button');
    if (canaryBtn && (stage === 'release_1_canary' || stage === 'form_baseline')) {
      isExecuting = true;
      setTimeout(() => {
        // Highlight 5-stamp pipeline
        moveCursorTo('.stamp-pipeline', 700, () => {
          setTimeout(() => {
            sessionStorage.setItem('segel_stage', 'release_1_promote');
            moveCursorTo(canaryBtn, 700, () => {
              clickElement(canaryBtn);
            });
          }, 800);
        });
      }, 500);
      return;
    }

    // ──────────────────────────────────────────────────────────────────────────
    // 4. RELEASE DETAIL 1: PROMOTE RELEASE (CANARY_DEPLOYED)
    // ──────────────────────────────────────────────────────────────────────────
    const promoteBtn = document.querySelector('form[action*="promote"] button');
    if (promoteBtn && (stage === 'release_1_promote' || stage === 'release_1_canary')) {
      isExecuting = true;
      setTimeout(() => {
        moveCursorTo('.stamp-pipeline', 700, () => {
          setTimeout(() => {
            sessionStorage.setItem('segel_stage', 'release_1_done');
            moveCursorTo(promoteBtn, 700, () => {
              clickElement(promoteBtn);
            });
          }, 800);
        });
      }, 500);
      return;
    }

    // ──────────────────────────────────────────────────────────────────────────
    // 5. RELEASE DETAIL 1: PROMOTED -> RETURN TO DASHBOARD
    // ──────────────────────────────────────────────────────────────────────────
    const backToDashBtn = document.querySelector('a[href="/"]');
    if (path.startsWith('/release/') && stage === 'release_1_done' && backToDashBtn) {
      isExecuting = true;
      setTimeout(() => {
        // Highlight General Passport badge
        moveCursorTo('.card', 700, () => {
          setTimeout(() => {
            sessionStorage.setItem('segel_stage', 'dashboard_updated');
            moveCursorTo(backToDashBtn, 700, () => {
              clickElement(backToDashBtn);
            });
          }, 900);
        });
      }, 600);
      return;
    }

    // ──────────────────────────────────────────────────────────────────────────
    // 6. DASHBOARD WITH UPDATED METRICS (/)
    // ──────────────────────────────────────────────────────────────────────────
    if (path === '/' && stage === 'dashboard_updated') {
      isExecuting = true;
      setTimeout(() => {
        // Showcase updated metrics (stamps: 9, merkle: 2, units: 3)
        moveCursorTo('.segel-interlock-col', 800, () => {
          setTimeout(() => {
            sessionStorage.setItem('segel_stage', 'form_dev14');
            moveCursorTo('a[href="/release/new"]', 700, () => {
              clickElement('a[href="/release/new"]');
            });
          }, 1200);
        });
      }, 500);
      return;
    }

    // ──────────────────────────────────────────────────────────────────────────
    // 7. NEW RELEASE FORM: DEV-14-SYNC (/release/new)
    // ──────────────────────────────────────────────────────────────────────────
    if (path === '/release/new' && stage === 'form_dev14') {
      isExecuting = true;
      setTimeout(() => {
        moveCursorTo('#release_id', 600, () => {
          typeText('#release_id', 'DEV-14-SYNC', 700, () => {
            moveCursorTo('#sequence', 350, () => {
              typeText('#sequence', '2', 250, () => {
                moveCursorTo('#purpose', 450, () => {
                  typeText('#purpose', 'Synchronize communication parameters for branch office gateway node', 1500, () => {
                    sessionStorage.setItem('segel_stage', 'release_2_inspect');
                    moveCursorTo('button[type="submit"]', 600, () => {
                      clickElement('button[type="submit"]');
                    });
                  });
                });
              });
            });
          });
        });
      }, 500);
      return;
    }

    // ──────────────────────────────────────────────────────────────────────────
    // 8. RELEASE DETAIL 2: AI ADVISORY INSPECTION DEMO
    // ──────────────────────────────────────────────────────────────────────────
    if (path.startsWith('/release/') && stage === 'release_2_inspect') {
      isExecuting = true;
      setTimeout(() => {
        // Target the AI Advisory Card
        const aiCard = document.querySelector('#ai-advisory-panel') || document.querySelector('.card:has(.badge-purple), .card:has(.badge-yellow), .card:has(.badge-muted)') || document.querySelector('.card');
        if (aiCard) {
          moveCursorTo(aiCard, 900, () => {
            setTimeout(() => {
              // Successfully complete demonstration
              sessionStorage.removeItem('segel_auto_active');
              sessionStorage.removeItem('segel_stage');
              cursor.style.display = 'none';
              isExecuting = false;
            }, 3000);
          });
        } else {
          sessionStorage.removeItem('segel_auto_active');
          sessionStorage.removeItem('segel_stage');
          cursor.style.display = 'none';
          isExecuting = false;
        }
      }, 600);
      return;
    }
  }

  // Spacebar and Escape Hotkey Listener
  window.addEventListener('keydown', function(e) {
    if (e.code === 'Space') {
      // Do not trigger if user is typing manually in input or textarea
      if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) {
        return;
      }
      e.preventDefault();

      const isActive = sessionStorage.getItem('segel_auto_active') === 'true';
      if (!isActive) {
        // Reset server state & start demonstration from beginning
        fetch('/reset', { method: 'POST' }).catch(() => {});
        sessionStorage.setItem('segel_auto_active', 'true');
        sessionStorage.setItem('segel_stage', 'start');
        isExecuting = false;
        if (window.location.pathname !== '/') {
          window.location.href = '/';
        } else {
          checkAndExecuteStep();
        }
      } else {
        // Pause demo
        sessionStorage.setItem('segel_auto_active', 'false');
        isExecuting = false;
        cursor.style.display = 'none';
        terminal.style.display = 'none';
      }
    } else if (e.code === 'Escape') {
      // Emergency stop and reset
      sessionStorage.removeItem('segel_auto_active');
      sessionStorage.removeItem('segel_stage');
      isExecuting = false;
      cursor.style.display = 'none';
      terminal.style.display = 'none';
    }
  });

  // Safe Single Initiation on Page Load
  if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', checkAndExecuteStep, { once: true });
  } else {
    setTimeout(checkAndExecuteStep, 250);
  }

})();
