document.body.addEventListener("htmx:responseError", function () {
  console.warn("HTMX request failed");
});

const ATTENDANCE_POLL_INTERVAL_MS = 15000;

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
  const labels = {
    ENTER: "入室",
    LEAVE_TEMP: "一時退出",
    RETURN: "再入室",
    LEAVE_FINAL: "退出",
  };
  return labels[eventType] || eventType;
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

async function refreshTodayAttendance() {
  if (window.location.pathname !== "/") {
    return;
  }

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
  } catch (error) {
    console.warn("Failed to refresh attendance", error);
  }
}

function initTopDashboard() {
  if (window.location.pathname !== "/") {
    return;
  }

  refreshTodayAttendance();
  window.setInterval(refreshTodayAttendance, ATTENDANCE_POLL_INTERVAL_MS);
}

initCardIdInputFocus();
initTopDashboard();
