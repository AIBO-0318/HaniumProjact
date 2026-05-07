/**
 * I-Study Beta - 웹캠 → WebSocket 시선 추적 클라이언트
 *
 * 흐름:
 *   1) getUserMedia() 로 웹캠 스트림 획득
 *   2) <video> 에 표시
 *   3) requestAnimationFrame 으로 ~10fps 캡처
 *   4) Canvas → JPEG → base64 → WebSocket 전송
 *   5) 서버 결과 수신 → 오버레이 + 상태 패널 갱신
 */

(() => {
  const FPS = 10;            // 전송 빈도 (성능 고려)
  const JPEG_QUALITY = 0.5;
  const VIDEO_W = 640, VIDEO_H = 480;

  const video   = document.getElementById("video");
  const overlay = document.getElementById("overlay");
  const ctx     = overlay.getContext("2d");

  const startBtn = document.getElementById("startBtn");
  const stopBtn  = document.getElementById("stopBtn");

  const wsStatusDot  = document.getElementById("wsStatus");
  const wsStatusText = document.getElementById("wsStatusText");
  const faceStatus   = document.getElementById("faceStatus");
  const focusState   = document.getElementById("focusState");
  const focusScore   = document.getElementById("focusScore");
  const headPose     = document.getElementById("headPose");

  let stream = null;
  let ws = null;
  let sending = false;
  let lastSent = 0;
  let captureCanvas = document.createElement("canvas");
  captureCanvas.width = VIDEO_W;
  captureCanvas.height = VIDEO_H;
  const captureCtx = captureCanvas.getContext("2d");

  function setStatus(connected) {
    wsStatusDot.classList.toggle("on", connected);
    wsStatusDot.classList.toggle("off", !connected);
    wsStatusText.textContent = connected ? "connected" : "disconnected";
  }

  async function start() {
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { width: VIDEO_W, height: VIDEO_H }, audio: false,
      });
      video.srcObject = stream;
      await video.play();

      overlay.width = video.videoWidth;
      overlay.height = video.videoHeight;

      // WebSocket 연결 (토큰을 query 로 전달)
      const token = Auth.getToken();
      const proto = location.protocol === "https:" ? "wss:" : "ws:";
      ws = new WebSocket(`${proto}//${location.host}/ws/gaze?token=${encodeURIComponent(token)}`);

      ws.onopen = () => {
        setStatus(true);
        sending = true;
        loop();
      };
      ws.onclose = () => { setStatus(false); sending = false; };
      ws.onerror = () => { setStatus(false); };
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === "result") onResult(msg);
        } catch {}
      };

      startBtn.disabled = true;
      stopBtn.disabled = false;
    } catch (err) {
      alert("웹캠 접근 실패: " + err.message);
    }
  }

  function stop() {
    sending = false;
    if (ws) { ws.close(); ws = null; }
    if (stream) {
      stream.getTracks().forEach(t => t.stop());
      stream = null;
    }
    video.srcObject = null;
    ctx.clearRect(0, 0, overlay.width, overlay.height);
    setStatus(false);
    startBtn.disabled = false;
    stopBtn.disabled = true;
  }

  function loop() {
    if (!sending) return;
    const now = performance.now();
    if (now - lastSent >= 1000 / FPS) {
      lastSent = now;
      sendFrame();
    }
    requestAnimationFrame(loop);
  }

  function sendFrame() {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    if (video.videoWidth === 0) return;

    captureCtx.drawImage(video, 0, 0, VIDEO_W, VIDEO_H);
    const dataUrl = captureCanvas.toDataURL("image/jpeg", JPEG_QUALITY);

    ws.send(JSON.stringify({
      type: "frame",
      image: dataUrl,
      screen: [window.innerWidth, window.innerHeight],
    }));
  }

  function onResult(msg) {
    faceStatus.textContent = msg.face_detected ? "✅ 감지됨" : "❌ 미감지";
    if (!msg.face_detected) {
      ctx.clearRect(0, 0, overlay.width, overlay.height);
      focusState.textContent = "-";
      focusScore.textContent = "-";
      headPose.textContent = "-";
      return;
    }

    focusState.textContent = msg.focus_state;
    focusScore.textContent = msg.focus_score + " / 100";
    headPose.textContent = `${msg.head.yaw.toFixed(1)}° / ${msg.head.pitch.toFixed(1)}°`;

    // 시선 위치 오버레이
    const [gx, gy] = msg.gaze;
    const x = gx * overlay.width;
    const y = gy * overlay.height;

    ctx.clearRect(0, 0, overlay.width, overlay.height);
    ctx.beginPath();
    ctx.arc(x, y, 12, 0, Math.PI * 2);
    ctx.fillStyle = msg.focus_state === "Focused" ? "rgba(52,199,89,.6)"
                  : msg.focus_state === "Dazed"   ? "rgba(255,149,0,.6)"
                  : "rgba(255,59,48,.6)";
    ctx.fill();
    ctx.strokeStyle = "#fff";
    ctx.lineWidth = 2;
    ctx.stroke();
  }

  startBtn.addEventListener("click", start);
  stopBtn.addEventListener("click", stop);
  window.addEventListener("beforeunload", stop);
})();
