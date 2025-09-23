
(function(){
  const API_BASE = '/api';
  const LS_KEY = 'lease_saas_token';

  function h(tag, attrs={}, children=[]) {
    const el = document.createElement(tag);
    Object.entries(attrs||{}).forEach(([k,v]) => {
      if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
      else if (k.startsWith('on') && typeof v === 'function') el[k.toLowerCase()] = v;
      else el.setAttribute(k, v);
    });
    (Array.isArray(children) ? children : [children]).forEach(c => {
      if (c == null) return;
      if (typeof c === 'string') el.appendChild(document.createTextNode(c));
      else el.appendChild(c);
    });
    return el;
  }

  function css(){
    const s = document.createElement('style');
    s.textContent = `
      .ls-floating-btn { position: fixed; right: 20px; bottom: 20px; z-index: 99999;
        border-radius: 9999px; padding: 12px 16px; box-shadow: 0 10px 30px rgba(0,0,0,.25);
        background:#111827; color:#fff; font-weight:600; cursor:pointer; }
      .ls-modal-backdrop { position:fixed; inset:0; background:rgba(0,0,0,.4); z-index:99998; display:none; }
      .ls-modal { position:fixed; right:20px; bottom:80px; width:360px; max-width:96vw;
        background:#fff; color:#111; border-radius:16px; box-shadow:0 20px 60px rgba(0,0,0,.35);
        z-index:99999; display:none; overflow:hidden; }
      .ls-header { padding:14px 16px; background:#111827; color:#fff; display:flex; justify-content:space-between; align-items:center; }
      .ls-tabs { display:flex; gap:8px; padding:8px 12px; border-bottom:1px solid #eee; flex-wrap:wrap;}
      .ls-tab { padding:6px 10px; border-radius:10px; cursor:pointer; background:#f3f4f6; font-size:12px; }
      .ls-tab.active { background:#111827; color:#fff; }
      .ls-body { padding:14px 16px; max-height:60vh; overflow:auto; }
      .ls-input { width:100%; padding:10px 12px; border:1px solid #ddd; border-radius:10px; margin:6px 0 10px; }
      .ls-btn { background:#111827; color:#fff; padding:10px 12px; border:none; border-radius:10px; cursor:pointer; font-weight:600; }
      .ls-muted { color:#6b7280; font-size:12px; }
      .ls-row { display:flex; gap:8px; align-items:center; }
      .ls-file { margin:8px 0; }
      .ls-badge { display:inline-block; padding:2px 8px; border-radius:9999px; background:#e5e7eb; font-size:12px; }
      .ls-success { color:#065f46; }
      .ls-error { color:#991b1b; }
      .ls-link { color:#2563eb; text-decoration:underline; cursor:pointer; }
      .ls-right { text-align:right; }
    `;
    document.head.appendChild(s);
  }

  function getToken(){ try { return localStorage.getItem(LS_KEY) || ''; } catch(e){ return ''; } }
  function setToken(t){ try { localStorage.setItem(LS_KEY, t||''); } catch(e){} }
  function authHeader(){ const t=getToken(); return t? { 'Authorization': 'Bearer ' + t } : {}; }

  async function api(path, opt={}){
    const res = await fetch(API_BASE + path, {
      method: opt.method || 'GET',
      headers: { 'Content-Type':'application/json', ...(opt.headers||{}), ...authHeader() },
      body: opt.body ? JSON.stringify(opt.body) : undefined
    });
    if (!res.ok) {
      let msg = res.status + ' ' + res.statusText;
      try { const j = await res.json(); if (j.detail) msg = j.detail; } catch(e){}
      throw new Error(msg);
    }
    const txt = await res.text();
    try { return JSON.parse(txt); } catch(e){ return txt; }
  }

  async function apiUpload(file){
    const fd = new FormData();
    fd.append('f', file);
    const res = await fetch(API_BASE + '/upload', {
      method:'POST',
      headers: { ...authHeader() },
      body: fd
    });
    if (!res.ok) {
      let msg = res.status + ' ' + res.statusText;
      try { const j = await res.json(); if (j.detail) msg = j.detail; } catch(e){}
      throw new Error(msg);
    }
    return await res.json();
  }

  // UI
  css();
  const openBtn = h('button', { class:'ls-floating-btn', id:'ls-launcher' }, 'Lease SaaS');
  const backdrop = h('div', { class:'ls-modal-backdrop', id:'ls-backdrop' });
  const modal = h('div', { class:'ls-modal', id:'ls-modal' });

  function show(){ backdrop.style.display='block'; modal.style.display='block'; renderActive(); }
  function hide(){ backdrop.style.display='none'; modal.style.display='none'; }

  openBtn.addEventListener('click', show);
  backdrop.addEventListener('click', hide);

  let active = 'login';
  const tabs = [
    {id:'login', label:'Login/Register'},
    {id:'upload', label:'Upload'},
    {id:'quota', label:'Quota'},
    {id:'upgrade', label:'Upgrade'}
  ];

  const header = h('div', {class:'ls-header'}, [
    h('div', {}, ['Lease SaaS']),
    h('div', {}, [
      h('span', {class:'ls-badge', id:'ls-status'}, 'Signed out')
    ])
  ]);

  const tabsBar = h('div', {class:'ls-tabs'},
    tabs.map(t => {
      const el = h('div', {class:'ls-tab' + (t.id===active?' active':''), 'data-id':t.id}, t.label);
      el.addEventListener('click', ()=>{ active=t.id; renderActive(); });
      return el;
    })
  );

  const body = h('div', {class:'ls-body', id:'ls-body'});

  modal.appendChild(header);
  modal.appendChild(tabsBar);
  modal.appendChild(body);

  document.body.appendChild(openBtn);
  document.body.appendChild(backdrop);
  document.body.appendChild(modal);

  function setStatus(){
    const has = !!getToken();
    document.getElementById('ls-status').textContent = has ? 'Signed in' : 'Signed out';
  }

  function renderActive(){
    // highlight tabs
    Array.from(tabsBar.children).forEach(ch => {
      ch.classList.toggle('active', ch.getAttribute('data-id')===active);
    });
    body.innerHTML = '';
    setStatus();
    if (active === 'login') renderLogin();
    if (active === 'upload') renderUpload();
    if (active === 'quota') renderQuota();
    if (active === 'upgrade') renderUpgrade();
  }

  function renderLogin(){
    const email = h('input', {class:'ls-input', type:'email', placeholder:'Email'});
    const pass = h('input', {class:'ls-input', type:'password', placeholder:'Password'});
    const out = h('div', {class:'ls-muted'});
    const row = h('div', {class:'ls-row'}, [
      h('button', {class:'ls-btn', onclick: async ()=>{
        try {
          await api('/auth/register', {method:'POST', body:{ email: email.value.trim(), password: pass.value }});
          out.textContent = 'Registered. You can now log in.';
          out.className = 'ls-muted ls-success';
        } catch(e){ out.textContent = e.message; out.className = 'ls-muted ls-error'; }
      }}, 'Register'),
      h('button', {class:'ls-btn', onclick: async ()=>{
        try {
          const tok = await api('/auth/login', {method:'POST', body:{ email: email.value.trim(), password: pass.value }});
          setToken(tok.access_token || '');
          out.textContent = 'Logged in.';
          out.className = 'ls-muted ls-success';
          setStatus();
        } catch(e){ out.textContent = e.message; out.className = 'ls-muted ls-error'; }
      }}, 'Login'),
      h('button', {class:'ls-btn', onclick: ()=>{ setToken(''); setStatus(); out.textContent='Signed out.'; out.className='ls-muted'; }}, 'Logout')
    ]);
    body.appendChild(email);
    body.appendChild(pass);
    body.appendChild(row);
    body.appendChild(out);
  }

  function renderUpload(){
    const info = h('div', {class:'ls-muted'}, 'Upload a file (respects your plan quotas).');
    const inp = h('input', {type:'file', class:'ls-file'});
    const out = h('div', {class:'ls-muted'});
    const btn = h('button', {class:'ls-btn', onclick: async ()=>{
      const f = inp.files && inp.files[0];
      if (!f){ out.textContent = 'Choose a file first.'; return; }
      out.textContent = 'Uploading...';
      try{
        const r = await apiUpload(f);
        out.innerHTML = `<span class="ls-success">Uploaded:</span> ${r.filename} • ${(r.size_bytes/1024/1024).toFixed(2)} MB<br>
                         Month: ${r.yyyymm} • Plan quota: ${r.quota_mb} MB`;
      }catch(e){
        out.textContent = e.message;
        out.className = 'ls-muted ls-error';
      }
    }}, 'Upload');
    body.appendChild(info);
    body.appendChild(inp);
    body.appendChild(btn);
    body.appendChild(out);
  }

  async function renderQuota(){
    const out = h('div', {class:'ls-muted'}, 'Loading...');
    body.appendChild(out);
    try{
      const q = await api('/quota');
      const usedMB = (q.used_bytes/1024/1024).toFixed(2);
      const maxMB = (q.max_bytes/1024/1024).toFixed(0);
      out.innerHTML = `Plan: <b>${q.plan}</b><br>Used: <b>${usedMB} MB</b> of <b>${maxMB} MB</b> this month (${q.yyyymm}).`;
      out.className = 'ls-muted';
    }catch(e){
      out.textContent = e.message;
      out.className = 'ls-muted ls-error';
    }
  }

  function renderUpgrade(){
    const info = h('div', {class:'ls-muted'}, 'Start a Stripe Checkout session to upgrade to Pro.');
    const out = h('div', {class:'ls-muted'});
    const btn = h('button', {class:'ls-btn', onclick: async ()=>{
      out.textContent = 'Creating checkout session...';
      try{
        const j = await api('/billing/create-checkout-session', {method:'POST'});
        if (j.checkout_url) { window.location.href = j.checkout_url; }
        else { out.textContent = 'No checkout URL returned.'; out.className='ls-muted ls-error'; }
      }catch(e){
        out.textContent = e.message;
        out.className = 'ls-muted ls-error';
      }
    }}, 'Upgrade to Pro');
    body.appendChild(info);
    body.appendChild(btn);
    body.appendChild(out);
  }

  // Auto-open quota if already signed in
  if (getToken()) active = 'quota';
})();

  // Expose a tiny global API so nav buttons can open the modal
  window.LeaseSaaS = {
    open: function(tab){
      if (tab) { active = tab; }
      show();
    },
    close: function(){ 
      hide();
    }
  };

  // Bind any element with data-ls-open and optional data-ls-tab
  document.addEventListener('click', function(e){
    const a = e.target.closest('[data-ls-open]');
    if (!a) return;
    e.preventDefault();
    const tab = a.getAttribute('data-ls-tab') || '';
    window.LeaseSaaS.open(tab || null);
  }, {capture:true});
})();