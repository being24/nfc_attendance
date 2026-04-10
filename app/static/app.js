document.body.addEventListener("htmx:responseError", function () {
  console.warn("HTMX request failed");
});

const ATTENDANCE_POLL_INTERVAL_MS = 15000;
const STUDENT_CARD_CAPTURE_POLL_INTERVAL_MS = 1000;
const UNKNOWN_CARD_ALERT_DURATION_MS = 5000;
let unknownCardAlertTimerId = null;
let lockAlertTimerId = null;
let touchErrorAlertTimerId = null;
let termTotalAlertTimerId = null;
let attendancePollTimerId = null;
let attendanceRefreshInFlight = false;
let attendanceEventSource = null;
let attendanceSseFallbackActive = false;
let studentCardCaptureEventSource = null;
let studentCardCapturePollTimerId = null;
let studentCardCaptureRefreshInFlight = false;
let loginCardCapturePollTimerId = null;
let loginCardCaptureRefreshInFlight = false;
let lastLoginCaptureKey = null;
let lastStudentCardCaptureKey = null;
let dismissedUnknownCardAlertKey = null;
let dismissedLockAlertKey = null;
let dismissedTouchErrorAlertKey = null;
let dismissedTermTotalAlertKey = null;

async function setKioskMode(mode) {
  try {
    await window.fetch("/api/attendance/kiosk-mode", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ mode }),
    });
  } catch (error) {
    console.warn("Failed to set kiosk mode", error);
  }
}

function touchActionLabel(action) {
  const labels = {
    ENTER: "入室",
    LEAVE_TEMP: "一時退出",
    RETURN: "再入室",
    LEAVE_FINAL: "退出",
    TERM_TOTAL: "通算時間",
  };
  return labels[action] || action;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function initCardIdInputFocus() {
  if (window.location.pathname !== "/") {
    return;
  }
  const input = document.getElementById("card-id-input");
  if (!input) {
    return;
  }

  const focusInput = () => {
    input.focus({ preventScroll: true });
  };

  focusInput();
  window.setTimeout(focusInput, 100);

  document.addEventListener("click", function (event) {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (target.closest("button, a, input, select, textarea, label")) {
      return;
    }
    focusInput();
  });

  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) {
      focusInput();
    }
  });
}

function formatTimestamp(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return new Intl.DateTimeFormat("ja-JP", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

function eventLabel(eventType) {
  return touchActionLabel(eventType);
}

function updateInRoom(inRoom) {
  const summary = document.getElementById("in-room-summary");
  const list = document.getElementById("in-room-list");
  if (!summary || !list) {
    return;
  }

  summary.textContent = `${inRoom.length}名在室中`;
  if (inRoom.length === 0) {
    list.innerHTML = '<p class="empty-text">在室者はいません</p>';
    return;
  }

  list.innerHTML = inRoom.map((entry) => {
    return `
      <article class="name-pill">
        <strong>${escapeHtml(entry.name)}</strong>
      </article>
    `;
  }).join("");
}

function updateRecentEvents(events) {
  const list = document.getElementById("recent-events-list");
  if (!list) {
    return;
  }

  const recent = events.slice(0, 5);
  if (recent.length === 0) {
    list.innerHTML = '<p class="empty-text">本日のログはまだありません</p>';
    return;
  }

  list.innerHTML = recent.map((event) => {
    return `
      <article class="event-row">
        <div class="event-main">
          <strong>${escapeHtml(event.student_name)}</strong>
          <span>${escapeHtml(event.student_code)}</span>
        </div>
        <div class="event-meta">
          <span class="event-type">${escapeHtml(eventLabel(event.event_type))}</span>
          <time datetime="${escapeHtml(event.occurred_at)}">${escapeHtml(formatTimestamp(event.occurred_at))}</time>
        </div>
      </article>
    `;
  }).join("");
}

function updateUnknownCardAlert(alert) {
  const card = document.getElementById("unknown-card-alert");
  if (!card) {
    return;
  }

  if (unknownCardAlertTimerId !== null) {
    window.clearTimeout(unknownCardAlertTimerId);
    unknownCardAlertTimerId = null;
  }

  if (!alert) {
    card.classList.add("is-hidden");
    return;
  }
  const alertKey = `${alert.card_id}:${alert.detected_at}`;
  if (alertKey === dismissedUnknownCardAlertKey) {
    card.classList.add("is-hidden");
    return;
  }

  const readerSuffix = alert.reader_name ? ` / reader: ${escapeHtml(alert.reader_name)}` : "";
  card.innerHTML = `
    <h2>未登録カード</h2>
    <p>カードID: <strong>${escapeHtml(alert.card_id)}</strong>${readerSuffix}</p>
  `;
  card.classList.remove("is-hidden");
  unknownCardAlertTimerId = window.setTimeout(() => {
    dismissedUnknownCardAlertKey = alertKey;
    card.classList.add("is-hidden");
    unknownCardAlertTimerId = null;
  }, UNKNOWN_CARD_ALERT_DURATION_MS);
}

function updateLockAlert(alert) {
  const card = document.getElementById("lock-alert");
  if (!card) {
    return;
  }

  if (lockAlertTimerId !== null) {
    window.clearTimeout(lockAlertTimerId);
    lockAlertTimerId = null;
  }

  if (!alert) {
    card.classList.add("is-hidden");
    return;
  }
  const alertKey = `${alert.message}:${alert.detected_at}`;
  if (alertKey === dismissedLockAlertKey) {
    card.classList.add("is-hidden");
    return;
  }

  card.innerHTML = `
    <h2>施錠してください</h2>
    <p>${escapeHtml(alert.message)}</p>
  `;
  card.classList.remove("is-hidden");
  lockAlertTimerId = window.setTimeout(() => {
    dismissedLockAlertKey = alertKey;
    card.classList.add("is-hidden");
    lockAlertTimerId = null;
  }, UNKNOWN_CARD_ALERT_DURATION_MS);
}

function updateTouchErrorAlert(alert) {
  const card = document.getElementById("touch-error-alert");
  if (!card) {
    return;
  }

  if (touchErrorAlertTimerId !== null) {
    window.clearTimeout(touchErrorAlertTimerId);
    touchErrorAlertTimerId = null;
  }

  if (!alert) {
    card.classList.add("is-hidden");
    return;
  }
  const alertKey = `${alert.message}:${alert.detected_at}`;
  if (alertKey === dismissedTouchErrorAlertKey) {
    card.classList.add("is-hidden");
    return;
  }

  card.innerHTML = `
    <h2>操作できません</h2>
    <p>${escapeHtml(alert.message)}</p>
  `;
  card.classList.remove("is-hidden");
  touchErrorAlertTimerId = window.setTimeout(() => {
    dismissedTouchErrorAlertKey = alertKey;
    card.classList.add("is-hidden");
    touchErrorAlertTimerId = null;
  }, UNKNOWN_CARD_ALERT_DURATION_MS);
}

function updateTermTotalAlert(result) {
  const card = document.getElementById("term-total-alert");
  if (!card) {
    return;
  }

  if (termTotalAlertTimerId !== null) {
    window.clearTimeout(termTotalAlertTimerId);
    termTotalAlertTimerId = null;
  }

  if (!result) {
    card.classList.add("is-hidden");
    return;
  }
  const alertKey = `${result.student_code}:${result.total_minutes}:${result.detected_at}`;
  if (alertKey === dismissedTermTotalAlertKey) {
    card.classList.add("is-hidden");
    return;
  }

  const hours = Math.floor((result.total_minutes || 0) / 60);
  const minutes = (result.total_minutes || 0) % 60;
  card.innerHTML = `
    <h2>今期の通算在室時間</h2>
    <p><strong>${escapeHtml(result.student_code)} ${escapeHtml(result.student_name)}</strong> / ${hours}時間${minutes}分（${escapeHtml(result.total_minutes)}分）</p>
    <p>${escapeHtml(result.period_label)}</p>
  `;
  card.classList.remove("is-hidden");
  termTotalAlertTimerId = window.setTimeout(() => {
    dismissedTermTotalAlertKey = alertKey;
    card.classList.add("is-hidden");
    termTotalAlertTimerId = null;
  }, UNKNOWN_CARD_ALERT_DURATION_MS);
}

function updateTouchPanelAction(action) {
  const status = document.getElementById("touch-action-status");
  const banner = document.getElementById("touch-action-banner");
  const help = document.getElementById("touch-action-help");
  const manualForm = document.getElementById("manual-card-form");
  const manualActionInput = document.getElementById("manual-action-input");
  const manualSubmitButton = document.getElementById("manual-submit-button");
  const buttons = document.querySelectorAll("[data-touch-action]");

  if (status) {
    status.textContent = touchActionLabel(action);
  }
  if (banner) {
    banner.className = `touch-action-banner touch-action-${String(action).toLowerCase()}`;
  }
  if (help) {
    help.textContent = action === "TERM_TOTAL"
      ? "この状態でカードをかざすと、今期の通算在室時間を表示します。"
      : "この状態でカードをかざすと、選択中の操作で処理します。";
  }
  if (manualForm) {
    manualForm.action = action === "TERM_TOTAL" ? "/student/term-total" : "/touch/manual";
  }
  if (manualActionInput) {
    manualActionInput.value = action;
  }
  if (manualSubmitButton) {
    manualSubmitButton.textContent = action === "TERM_TOTAL" ? "このカードIDで通算時間を表示" : "このカードIDで打刻";
  }
  buttons.forEach((button) => {
    if (!(button instanceof HTMLElement)) {
      return;
    }
    button.classList.toggle("is-selected", button.dataset.touchAction === action);
  });
}

async function refreshTouchPanelAction() {
  const status = document.getElementById("touch-action-status");
  if (!status) {
    return;
  }

  try {
    const response = await window.fetch("/api/attendance/touch-panel/action", {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch touch panel action: ${response.status}`);
    }
    const payload = await response.json();
    updateTouchPanelAction(payload.selected_action);
  } catch (error) {
    console.warn("Failed to refresh touch panel action", error);
  }
}

function initTouchPanelSelector() {
  const buttons = document.querySelectorAll("[data-touch-action]");
  if (buttons.length === 0) {
    return;
  }

  refreshTouchPanelAction();
  buttons.forEach((button) => {
    button.addEventListener("click", async function () {
      const action = button.dataset.touchAction;
      if (!action) {
        return;
      }
      try {
        const response = await window.fetch("/api/attendance/touch-panel/action", {
          method: "POST",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ action }),
        });
        if (!response.ok) {
          throw new Error(`Failed to set touch panel action: ${response.status}`);
        }
        const payload = await response.json();
        updateTouchPanelAction(payload.selected_action);
      } catch (error) {
        console.warn("Failed to set touch panel action", error);
      }
    });
  });
}

async function refreshTodayAttendance() {
  if (window.location.pathname !== "/") {
    return;
  }
  if (attendanceRefreshInFlight) {
    return;
  }

  attendanceRefreshInFlight = true;
  try {
    const response = await window.fetch("/api/attendance/today", {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch attendance: ${response.status}`);
    }

    const payload = await response.json();
    updateInRoom(payload.in_room || []);
    updateRecentEvents(payload.events || []);
    updateUnknownCardAlert(payload.unknown_card_alert || null);
    updateLockAlert(payload.lock_alert || null);
    updateTouchErrorAlert(payload.touch_error || null);
    updateTermTotalAlert(payload.latest_term_total || null);
  } catch (error) {
    console.warn("Failed to refresh attendance", error);
  } finally {
    attendanceRefreshInFlight = false;
  }
}

function scheduleTopDashboardRefresh(delayMs = ATTENDANCE_POLL_INTERVAL_MS) {
  if (attendancePollTimerId !== null) {
    window.clearTimeout(attendancePollTimerId);
  }
  attendancePollTimerId = window.setTimeout(async () => {
    await refreshTodayAttendance();
    scheduleTopDashboardRefresh();
  }, delayMs);
}

function initTopDashboard() {
  if (window.location.pathname !== "/") {
    return;
  }

  setKioskMode("ATTENDANCE");
  refreshTodayAttendance();
  if ("EventSource" in window) {
    attendanceEventSource = new window.EventSource("/api/attendance/stream");
    attendanceEventSource.onmessage = function () {
      attendanceSseFallbackActive = false;
      refreshTodayAttendance();
    };
    attendanceEventSource.onerror = function () {
      console.warn("Attendance SSE connection failed");
      if (!attendanceSseFallbackActive) {
        attendanceSseFallbackActive = true;
        scheduleTopDashboardRefresh(1000);
      }
    };
  } else {
    scheduleTopDashboardRefresh();
  }

  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) {
      refreshTodayAttendance();
      if (!attendanceEventSource) {
        scheduleTopDashboardRefresh();
      }
    }
  });
}

async function refreshStudentCardCapture() {
  const cardInput = document.getElementById("student-card-id-input");
  const status = document.getElementById("student-card-capture-status");
  if (!cardInput || !status) {
    return;
  }
  if (studentCardCaptureRefreshInFlight) {
    return;
  }

  studentCardCaptureRefreshInFlight = true;
  try {
    const response = await window.fetch("/api/admin/latest-student-card", {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (response.status === 401) {
      status.textContent = "管理者ログインが必要です。";
      return;
    }
    if (!response.ok) {
      throw new Error(`Failed to fetch latest unknown card: ${response.status}`);
    }

    const payload = await response.json();
    if (!payload) {
      return;
    }
    const captureKey = `${payload.card_id}:${payload.detected_at}`;
    if (captureKey === lastStudentCardCaptureKey) {
      return;
    }
    lastStudentCardCaptureKey = captureKey;

    cardInput.value = payload.card_id || "";
    const readerSuffix = payload.reader_name ? ` / reader: ${payload.reader_name}` : "";
    status.textContent = `カードを受信しました: ${payload.card_id}${readerSuffix}`;
  } catch (error) {
    console.warn("Failed to refresh student card capture", error);
  } finally {
    studentCardCaptureRefreshInFlight = false;
  }
}

function scheduleStudentCardCaptureRefresh(delayMs = STUDENT_CARD_CAPTURE_POLL_INTERVAL_MS) {
  if (studentCardCapturePollTimerId !== null) {
    window.clearTimeout(studentCardCapturePollTimerId);
  }
  studentCardCapturePollTimerId = window.setTimeout(async () => {
    await refreshStudentCardCapture();
    scheduleStudentCardCaptureRefresh();
  }, delayMs);
}

function initStudentCardCapture() {
  const cardInput = document.getElementById("student-card-id-input");
  const status = document.getElementById("student-card-capture-status");
  if (!cardInput || !status) {
    return;
  }

  setKioskMode("STUDENT_REGISTER");
  refreshStudentCardCapture();
  scheduleStudentCardCaptureRefresh();
  if ("EventSource" in window) {
    studentCardCaptureEventSource = new window.EventSource("/api/attendance/stream");
    studentCardCaptureEventSource.onmessage = function () {
      refreshStudentCardCapture();
    };
    studentCardCaptureEventSource.onerror = function () {
      console.warn("Student card capture SSE connection failed");
    };
  }

  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) {
      refreshStudentCardCapture();
      scheduleStudentCardCaptureRefresh();
    }
  });
}

async function refreshLoginCardCapture() {
  const cardInput = document.getElementById("login-card-id-input");
  const status = document.getElementById("login-card-capture-status");
  const form = document.getElementById("login-touch-form");
  if (!cardInput || !status || !form) {
    return;
  }
  if (loginCardCaptureRefreshInFlight) {
    return;
  }

  loginCardCaptureRefreshInFlight = true;
  try {
    const response = await window.fetch("/api/login/latest-card", {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch latest login card: ${response.status}`);
    }
    const payload = await response.json();
    if (!payload) {
      return;
    }
    const captureKey = `${payload.card_id}:${payload.detected_at}`;
    if (captureKey === lastLoginCaptureKey) {
      return;
    }
    lastLoginCaptureKey = captureKey;

    cardInput.value = payload.card_id || "";
    const readerSuffix = payload.reader_name ? ` / reader: ${payload.reader_name}` : "";
    status.textContent = `カードを受信しました: ${payload.card_id}${readerSuffix}`;
    form.submit();
  } catch (error) {
    console.warn("Failed to refresh login card capture", error);
  } finally {
    loginCardCaptureRefreshInFlight = false;
  }
}

function scheduleLoginCardCaptureRefresh(delayMs = 1000) {
  if (loginCardCapturePollTimerId !== null) {
    window.clearTimeout(loginCardCapturePollTimerId);
  }
  loginCardCapturePollTimerId = window.setTimeout(async () => {
    await refreshLoginCardCapture();
    scheduleLoginCardCaptureRefresh();
  }, delayMs);
}

function initLoginCardCapture() {
  const form = document.getElementById("login-touch-form");
  if (!form) {
    return;
  }

  setKioskMode("ADMIN_LOGIN");
  refreshLoginCardCapture();
  scheduleLoginCardCaptureRefresh();
  if ("EventSource" in window) {
    const source = new window.EventSource("/api/attendance/stream");
    source.onmessage = function () {
      refreshLoginCardCapture();
    };
    source.onerror = function () {
      console.warn("Login card capture SSE connection failed");
    };
  }
}

initCardIdInputFocus();
initTopDashboard();
initStudentCardCapture();
initTouchPanelSelector();
initLoginCardCapture();
