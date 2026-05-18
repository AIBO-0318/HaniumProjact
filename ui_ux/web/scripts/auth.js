/**
 * I-Study Beta - 인증 헬퍼
 * 토큰 저장/조회, 로그인/회원가입 API 래퍼
 */

const Auth = (() => {
  const KEY_TOKEN = "token";
  const KEY_INFO = "user_info";

  function _save(token, info) {
    localStorage.setItem(KEY_TOKEN, token);
    localStorage.setItem(KEY_INFO, JSON.stringify(info));
  }

  return {
    getToken: () => localStorage.getItem(KEY_TOKEN),
    getInfo: () => {
      try { return JSON.parse(localStorage.getItem(KEY_INFO)) || {}; }
      catch { return {}; }
    },
    logout: () => {
      localStorage.removeItem(KEY_TOKEN);
      localStorage.removeItem(KEY_INFO);
    },
    requireLogin: () => {
      if (!localStorage.getItem(KEY_TOKEN)) {
        location.href = "/";
      }
    },

    // ─── 사용자 ───
    userSignup: (payload) =>
      Api.post("/users/signup", payload),

    userLogin: async (login_id, password) => {
      const res = await Api.post("/users/login", { login_id, password });
      _save(res.access_token, {
        account_type: res.account_type,
        role: res.role,
        name: res.name,
        login_id,
      });
      return res;
    },

    // ─── 관리자 ───
    adminSignup: ({ admin_id, password, name, level }) =>
      Api.post("/admins/signup", { admin_id, password, name, level }),

    adminLogin: async (admin_id, password) => {
      const res = await Api.post("/admins/login", { admin_id, password });
      _save(res.access_token, {
        account_type: res.account_type,
        role: res.role,
        name: res.name,
        admin_id,
      });
      return res;
    },
  };
})();
