(() => {
  const KEY = 'admin_token';

  function getAdminToken() {
    return (localStorage.getItem(KEY) || '').trim();
  }

  function setAdminToken(token) {
    localStorage.setItem(KEY, (token || '').trim());
  }

  function getAuthHeaders(extra = {}) {
    const token = getAdminToken();
    return token ? { ...extra, 'X-Admin-Token': token } : { ...extra };
  }

  async function adminPost(url, body = null) {
    const headers = getAuthHeaders();
    if (body !== null) {
      headers['Content-Type'] = 'application/json';
    }
    const res = await fetch(url, {
      method: 'POST',
      headers,
      body: body === null ? undefined : JSON.stringify(body),
    });
    let data;
    try {
      data = await res.json();
    } catch {
      data = { ok: false, message: `HTTP ${res.status}` };
    }
    return { res, data };
  }

  function bindTokenInput() {
    const input = document.getElementById('adminTokenInput');
    const btn = document.getElementById('saveAdminTokenBtn');
    const status = document.getElementById('adminTokenStatus');
    if (!input || !btn || !status) return;

    input.value = getAdminToken();

    const renderStatus = () => {
      status.textContent = getAdminToken() ? '管理员令牌：已保存' : '管理员令牌：未设置';
    };
    renderStatus();

    btn.addEventListener('click', () => {
      setAdminToken(input.value);
      renderStatus();
    });
  }

  window.WJAdmin = {
    getAdminToken,
    setAdminToken,
    getAuthHeaders,
    adminPost,
    bindTokenInput,
  };
})();
