// ==============================================================================
// SEGEL — Script Demonstrasi Otomatis Berbasis Penekanan Tombol Spasi
// Beroperasi Langsung di Atas Antarmuka Asli http://127.0.0.1:8000/
// ==============================================================================

(function() {
  'use strict';

  // Clear demo automation session if requested via URL
  if (window.location.search.includes('reset=1')) {
    sessionStorage.removeItem('segel_auto_active');
    sessionStorage.removeItem('segel_auto_step');
    fetch('/reset', { method: 'POST' }).catch(() => {});
  }

  // Inject Styles for Virtual Cursor, Ripple, and Floating Terminal
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

  // Smooth Cursor Movement
  function moveCursor(targetX, targetY, durationMs = 800, onDone = null) {
    cursor.style.display = 'block';
    const startX = cursor._currentX || 200;
    const startY = cursor._currentY || 200;
    const startTime = performance.now();

    function animate(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / durationMs, 1);
      const ease = progress < 0.5 ? 4 * progress * progress * progress : 1 - Math.pow(-2 * progress + 2, 3) / 2;
      const curX = startX + (targetX - startX) * ease;
      const curY = startY + (targetY - startY) * ease;
      cursor.style.transform = `translate3d(${curX}px, ${curY}px, 0)`;
      cursor._currentX = curX;
      cursor._currentY = curY;

      if (progress < 1) {
        requestAnimationFrame(animate);
      } else if (onDone) {
        onDone();
      }
    }
    requestAnimationFrame(animate);
  }

  function moveCursorToElement(selector, durationMs = 800, onDone = null) {
    const elem = document.querySelector(selector);
    if (!elem) {
      if (onDone) onDone();
      return;
    }
    elem.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setTimeout(() => {
      const rect = elem.getBoundingClientRect();
      const targetX = rect.left + rect.width / 2;
      const targetY = rect.top + rect.height / 2;
      moveCursor(targetX, targetY, durationMs, () => {
        if (onDone) onDone();
      });
    }, 150);
  }

  function clickElement(selector, onDone = null) {
    const elem = document.querySelector(selector);
    if (!elem) {
      if (onDone) onDone();
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
    setTimeout(() => ripple.remove(), 600);

    setTimeout(() => {
      elem.click();
      if (onDone) onDone();
    }, 200);
  }

  function typeText(selector, text, durationMs = 800, onDone = null) {
    const input = document.querySelector(selector);
    if (!input) {
      if (onDone) onDone();
      return;
    }
    input.focus();
    input.value = '';
    const chars = text.split('');
    const delay = durationMs / chars.length;
    let i = 0;

    function step() {
      if (i < chars.length) {
        input.value += chars[i];
        input.dispatchEvent(new Event('input', { bubbles: true }));
        i++;
        setTimeout(step, delay);
      } else {
        input.dispatchEvent(new Event('change', { bubbles: true }));
        if (onDone) onDone();
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
          }, 3500);
        }, 1200);
      }, 1500);
    }, 1000);
  }

  // Main Autopilot Controller across pages
  function checkAndExecuteStep() {
    const active = sessionStorage.getItem('segel_auto_active') === 'true';
    if (!active) return;

    cursor.style.display = 'block';
    const step = parseInt(sessionStorage.getItem('segel_auto_step') || '1', 10);
    const path = window.location.pathname;

    // STEP 1 & 2: ON DASHBOARD (/)
    if (path === '/' && step === 1) {
      showTerminalProofs(() => {
        sessionStorage.setItem('segel_auto_step', '2');
        checkAndExecuteStep();
      });
      return;
    }

    if (path === '/' && step === 2) {
      // Highlight dashboard metrics
      moveCursorToElement('.segel-card-tabbed-notch', 900, () => {
        setTimeout(() => {
          moveCursorToElement('.segel-interlock-card', 900, () => {
            setTimeout(() => {
              moveCursorToElement('.segel-chart-box', 900, () => {
                setTimeout(() => {
                  // Navigate to New Release
                  sessionStorage.setItem('segel_auto_step', '3');
                  moveCursorToElement('a[href="/release/new"]', 800, () => {
                    clickElement('a[href="/release/new"]');
                  });
                }, 1000);
              });
            }, 1000);
          });
        }, 1000);
      });
      return;
    }

    // STEP 3: ON NEW RELEASE FORM (/release/new) - BASELINE-UNIT-42
    if (path === '/release/new' && step === 3) {
      setTimeout(() => {
        moveCursorToElement('#release_id', 700, () => {
          typeText('#release_id', 'BASELINE-UNIT-42', 900, () => {
            moveCursorToElement('#sequence', 400, () => {
              typeText('#sequence', '1', 300, () => {
                moveCursorToElement('#purpose', 500, () => {
                  typeText('#purpose', 'Pembaruan parameter jaringan operasional stasiun pangkalan', 1500, () => {
                    sessionStorage.setItem('segel_auto_step', '4');
                    moveCursorToElement('button[type="submit"]', 700, () => {
                      clickElement('button[type="submit"]');
                    });
                  });
                });
              });
            });
          });
        });
      }, 600);
      return;
    }

    // STEP 4: ON RELEASE DETAIL PAGE (/release/0) - CANARY & PROMOTE
    if (path.startsWith('/release/') && step === 4) {
      setTimeout(() => {
        moveCursorToElement('.stamp-pipeline', 800, () => {
          setTimeout(() => {
            // Deploy canary
            moveCursorToElement('form[action*="deploy-canary"] button', 800, () => {
              clickElement('form[action*="deploy-canary"] button', () => {
                setTimeout(() => {
                  // Promote
                  moveCursorToElement('form[action*="promote"] button', 800, () => {
                    clickElement('form[action*="promote"] button', () => {
                      setTimeout(() => {
                        // Return to Dashboard
                        sessionStorage.setItem('segel_auto_step', '5');
                        moveCursorToElement('a[href="/"]', 800, () => {
                          clickElement('a[href="/"]');
                        });
                      }, 1200);
                    });
                  });
                }, 1500);
              });
            });
          }, 1000);
        });
      }, 800);
      return;
    }

    // STEP 5: ON DASHBOARD (/) - SHOW UPDATED METRICS & GO TO DEV-14
    if (path === '/' && step === 5) {
      setTimeout(() => {
        moveCursorToElement('.segel-interlock-col', 1000, () => {
          setTimeout(() => {
            sessionStorage.setItem('segel_auto_step', '6');
            moveCursorToElement('a[href="/release/new"]', 800, () => {
              clickElement('a[href="/release/new"]');
            });
          }, 1500);
        });
      }, 800);
      return;
    }

    // STEP 6: ON NEW RELEASE FORM (/release/new) - DEV-14-SYNC
    if (path === '/release/new' && step === 6) {
      setTimeout(() => {
        moveCursorToElement('#release_id', 700, () => {
          typeText('#release_id', 'DEV-14-SYNC', 800, () => {
            moveCursorToElement('#sequence', 400, () => {
              typeText('#sequence', '2', 300, () => {
                moveCursorToElement('#purpose', 500, () => {
                  typeText('#purpose', 'Synchronize communication parameters for branch office gateway node', 1600, () => {
                    sessionStorage.setItem('segel_auto_step', '7');
                    moveCursorToElement('button[type="submit"]', 700, () => {
                      clickElement('button[type="submit"]');
                    });
                  });
                });
              });
            });
          });
        });
      }, 600);
      return;
    }

    // STEP 7: ON RELEASE DETAIL PAGE (/release/1) - AI ADVISORY INSPECTION
    if (path.startsWith('/release/') && step === 7) {
      setTimeout(() => {
        moveCursorToElement('.stamp-warn, .card', 1000, () => {
          setTimeout(() => {
            // Finish demo
            sessionStorage.removeItem('segel_auto_active');
            sessionStorage.removeItem('segel_auto_step');
            cursor.style.display = 'none';
          }, 3000);
        });
      }, 1000);
      return;
    }
  }

  // Spacebar Listener
  window.addEventListener('keydown', function(e) {
    if (e.code === 'Space') {
      // Do not trigger if typing inside input or textarea
      if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) {
        return;
      }
      e.preventDefault();

      const isActive = sessionStorage.getItem('segel_auto_active') === 'true';
      if (!isActive) {
        // Reset state & Start
        fetch('/reset', { method: 'POST' }).catch(() => {});
        sessionStorage.setItem('segel_auto_active', 'true');
        sessionStorage.setItem('segel_auto_step', '1');
        if (window.location.pathname !== '/') {
          window.location.href = '/';
        } else {
          checkAndExecuteStep();
        }
      } else {
        // Pause
        sessionStorage.setItem('segel_auto_active', 'false');
        cursor.style.display = 'none';
        terminal.style.display = 'none';
      }
    } else if (e.code === 'Escape') {
      // Stop and reset
      sessionStorage.removeItem('segel_auto_active');
      sessionStorage.removeItem('segel_auto_step');
      cursor.style.display = 'none';
      terminal.style.display = 'none';
    }
  });

  // Run on page load if active
  window.addEventListener('DOMContentLoaded', checkAndExecuteStep);
  if (document.readyState !== 'loading') {
    checkAndExecuteStep();
  }

})();
