/**
 * I-Study Beta - 공통 상단 네비게이션 (역할별 메뉴 분기)
 *
 * Role-based menus:
 *  - ADMIN    → 홈, 마이페이지(사용자 관리)
 *  - STUDENT  → 홈, 일정표, 학습 통계, 시선 추적, 마이페이지   (화이트리스트 ❌)
 *  - TEACHER  → 홈, 학생 일정 조회, 학생 화이트리스트 관리, 마이페이지
 */

(() => {
  const el = document.getElementById("topbar");
  if (!el) return;

  const info = Auth.getInfo();
  if (!info || !info.name) { location.href = "/"; return; }

  const role = info.role;       // STUDENT / TEACHER / ADMIN
  const path = location.pathname;

  let links = [];
  if (role === "ADMIN") {
    links = [
      { href: "/main",              label: "홈" },
      { href: "/admin-users",       label: "사용자 관리" },
      { href: "/admin-stats",       label: "학생 통계" },
      { href: "/teacher-schedule",  label: "학생 일정" },
      { href: "/teacher-whitelist", label: "화이트리스트" },
      { href: "/mypage",            label: "마이페이지" },
    ];
  } else if (role === "TEACHER") {
    links = [
      { href: "/main",                 label: "홈" },
      { href: "/teacher-schedule",     label: "학생 일정 조회" },
      { href: "/teacher-whitelist",    label: "학생 화이트리스트" },
      { href: "/mypage",               label: "마이페이지" },
    ];
  } else {  // STUDENT
    links = [
      { href: "/main",          label: "홈" },
      { href: "/schedule",      label: "일정표" },
      { href: "/stats",         label: "학습 통계" },
      { href: "/calibration",   label: "시선 초점" },
      { href: "/whitelist",     label: "화이트리스트" },
      { href: "/mypage",        label: "마이페이지" },
    ];
  }

  // 노출 가능한 path 화이트리스트 (학생이 직접 URL 입력 시 차단)
  const allowed = new Set(links.map(l => l.href).concat(["/mypage"]));
  if (!allowed.has(path) && path !== "/main" && !path.startsWith("/teacher-")) {
    // 권한이 없는 경로 방문 시 홈으로
    if (role === "STUDENT" && path.startsWith("/teacher-")) {
      location.href = "/main"; return;
    }
    if (role === "TEACHER" && (path === "/schedule" || path === "/stats" || path === "/dashboard" || path === "/gaze-settings" || path === "/calibration" || path === "/whitelist")) {
      location.href = "/main"; return;
    }
    if (role === "ADMIN" && (path === "/schedule" || path === "/stats" || path === "/dashboard" || path === "/gaze-settings" || path === "/calibration" || path === "/whitelist")) {
      location.href = "/main"; return;
    }
  }

  el.className = "topbar";
  el.innerHTML = `
    <div class="topbar-left">
      <span class="logo" onclick="location.href='/main'">📘 I-Study</span>
      <nav class="topbar-nav">
        ${links.map(l =>
          `<a href="${l.href}" class="${path === l.href ? 'active' : ''}">${l.label}</a>`
        ).join("")}
      </nav>
    </div>
    <div class="topbar-right">
      <span class="badge">${info.role}</span>
      <span style="font-weight:600;color:var(--ink-700)">${info.name}</span>
      <button class="btn-ghost" onclick="Auth.logout(); location.href='/'">로그아웃</button>
    </div>
  `;
})();
