/**
 * I-Study Beta - HTTP API 클라이언트
 * 토큰 자동 첨부, JSON 응답 파싱, 에러 처리
 */

const Api = (() => {
  const BASE = "";  // 동일 서버에서 서빙 (절대 URL이 필요하면 여기에)

  function _headers() {
    const h = { "Content-Type": "application/json" };
    const t = localStorage.getItem("token");
    if (t) h["Authorization"] = `Bearer ${t}`;
    return h;
  }

  async function _handle(res) {
    if (res.status === 204) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = data.detail || data.message || res.statusText;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return data;
  }

  return {
    get: (path) => fetch(BASE + path, { headers: _headers() }).then(_handle),
    post: (path, body) => fetch(BASE + path, {
      method: "POST",
      headers: _headers(),
      body: body ? JSON.stringify(body) : undefined,
    }).then(_handle),
    patch: (path, body) => fetch(BASE + path, {
      method: "PATCH",
      headers: _headers(),
      body: body ? JSON.stringify(body) : undefined,
    }).then(_handle),
    put: (path, body) => fetch(BASE + path, {
      method: "PUT",
      headers: _headers(),
      body: body ? JSON.stringify(body) : undefined,
    }).then(_handle),
    del: (path) => fetch(BASE + path, {
      method: "DELETE", headers: _headers(),
    }).then(_handle),
  };
})();
