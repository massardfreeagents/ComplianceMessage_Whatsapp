"""
ForExperts — Agente de Disparo WhatsApp
App Streamlit independente.
Secrets necessários (Streamlit Cloud):
    WHATSAPP_API_URL   = "https://evolution-api-production-a7d4.up.railway.app"
    WHATSAPP_API_KEY   = "sua-api-key"
    WHATSAPP_INSTANCE  = "ForExperts"
"""

import streamlit as st
import requests
import time
import urllib3
from datetime import datetime, timezone, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ForExperts · WhatsApp",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Estilo ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
    background-color: #080e1a;
    color: #dde2ee;
}
.stApp { background-color: #080e1a; }

/* ── Hero ── */
.hero {
    display: flex;
    align-items: flex-end;
    gap: 1.2rem;
    padding: 2rem 2.5rem 1.8rem;
    background: linear-gradient(120deg, #0a1628 0%, #0d2010 60%, #080e1a 100%);
    border: 1px solid rgba(37,211,102,0.18);
    border-radius: 18px;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
}
.hero::after {
    content: '';
    position: absolute;
    right: -60px; top: -60px;
    width: 280px; height: 280px;
    background: radial-gradient(circle, rgba(37,211,102,0.07) 0%, transparent 70%);
    pointer-events: none;
}
.hero-icon {
    font-size: 3rem;
    line-height: 1;
    filter: drop-shadow(0 0 18px rgba(37,211,102,0.5));
}
.hero-title {
    font-size: 1.9rem;
    font-weight: 800;
    color: #ffffff;
    line-height: 1.1;
    margin: 0;
}
.hero-sub {
    color: #25d366;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-top: 0.3rem;
}

/* ── Cards ── */
.card {
    background: rgba(255,255,255,0.028);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1.2rem;
}
.card-title {
    font-size: 0.72rem;
    font-weight: 700;
    color: #25d366;
    text-transform: uppercase;
    letter-spacing: 0.13em;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* ── Chips ── */
.chip-wrap { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 0.7rem; }
.chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: rgba(37,211,102,0.1);
    border: 1px solid rgba(37,211,102,0.28);
    color: #25d366;
    border-radius: 99px;
    padding: 3px 11px;
    font-size: 0.73rem;
    font-weight: 600;
}

/* ── Stat boxes ── */
.stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.stat-ok {
    background: rgba(37,211,102,0.08);
    border: 1px solid rgba(37,211,102,0.25);
    border-radius: 12px;
    padding: 1.2rem;
    text-align: center;
}
.stat-fail {
    background: rgba(248,113,113,0.08);
    border: 1px solid rgba(248,113,113,0.25);
    border-radius: 12px;
    padding: 1.2rem;
    text-align: center;
}
.stat-num-ok   { font-size: 2.2rem; font-weight: 800; color: #25d366; }
.stat-num-fail { font-size: 2.2rem; font-weight: 800; color: #f87171; }
.stat-lbl { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; margin-top: 0.2rem; }

/* ── Inputs override ── */
.stTextArea textarea {
    background: #0f1a2e !important;
    border: 1px solid rgba(37,211,102,0.25) !important;
    border-radius: 10px !important;
    color: #dde2ee !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.88rem !important;
    line-height: 1.65 !important;
}
.stTextInput input {
    background: #0f1a2e !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
    color: #dde2ee !important;
    font-size: 0.88rem !important;
}
.stTextInput input:focus {
    border-color: rgba(37,211,102,0.5) !important;
}
.stButton > button {
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    border-radius: 10px !important;
    transition: all 0.18s !important;
}
.stMultiSelect [data-baseweb="tag"] {
    background: rgba(37,211,102,0.15) !important;
    color: #25d366 !important;
}

/* ── Log history ── */
.log-line {
    font-family: 'DM Mono', monospace;
    font-size: 0.76rem;
    padding: 4px 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    display: flex;
    gap: 1rem;
}
.log-ok   { color: #25d366; }
.log-fail { color: #f87171; }
.log-time { color: #4a5568; }
</style>
""", unsafe_allow_html=True)


# ─── Helpers Evolution API ─────────────────────────────────────────────────────

import os

def _api_url():
    return os.getenv("WHATSAPP_API_URL", "").rstrip("/")

def _instance():
    return os.getenv("WHATSAPP_INSTANCE", "ForExperts")

def _headers():
    return {"apikey": os.getenv("WHATSAPP_API_KEY", ""), "Content-Type": "application/json"}

def fetch_grupos():
    url  = f"{_api_url()}/group/fetchAllGroups/{_instance()}?getParticipants=false"
    resp = requests.get(url, headers=_headers(), timeout=20, verify=False)
    resp.raise_for_status()
    data = resp.json()
    items = data if isinstance(data, list) else data.get("groups", [])
    return sorted(
        [{"id": g.get("id") or g.get("remoteJid",""), "nome": g.get("subject") or g.get("name","Sem nome")} for g in items],
        key=lambda x: x["nome"].lower()
    )

def fetch_contatos(filtro: str):
    url  = f"{_api_url()}/contact/fetchContacts/{_instance()}"
    resp = requests.get(url, headers=_headers(), timeout=20, verify=False)
    resp.raise_for_status()
    data = resp.json()
    raw  = data if isinstance(data, list) else data.get("contacts", [])
    f    = filtro.strip().lower()
    result = []
    for c in raw:
        jid  = c.get("remoteJid") or c.get("id") or ""
        nome = c.get("pushName") or c.get("name") or ""
        if "@g.us" in jid or "@broadcast" in jid:
            continue
        if f and f not in nome.lower():
            continue
        result.append({"id": jid, "nome": nome or jid.split("@")[0]})
    return sorted(result, key=lambda x: x["nome"].lower())

def enviar_msg(jid: str, texto: str, com_imagem: bool) -> bool:
    base = _api_url(); inst = _instance(); h = _headers()
    if com_imagem:
        payload  = {
            "number": jid, "mediatype": "image", "mimetype": "image/png",
            "caption": texto,
            "media": "https://forexperts.com.br/wp-content/uploads/2026/05/ha-vagas.png",
            "fileName": "forexperts.png",
        }
        endpoint = f"{base}/message/sendMedia/{inst}"
    else:
        payload  = {"number": jid, "text": texto}
        endpoint = f"{base}/message/sendText/{inst}"
    r = requests.post(endpoint, headers=h, json=payload, timeout=30, verify=False)
    return r.status_code in [200, 201]


# ─── Session state ─────────────────────────────────────────────────────────────
for k, v in {
    "grupos_cache":    [],
    "contatos_cache":  [],
    "historico":       [],
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─── HERO ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-icon">📱</div>
    <div>
        <div class="hero-sub">ForExperts · Agente</div>
        <div class="hero-title">Disparo WhatsApp</div>
    </div>
</div>
""", unsafe_allow_html=True)

col_main, col_side = st.columns([3, 2], gap="large")

# ═══════════════════════════════════════════════════════════════════════════════
# COLUNA PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════
with col_main:

    # ── 1. Mensagem ────────────────────────────────────────────────────────────
    st.markdown('<div class="card"><div class="card-title">✏️ Mensagem</div>', unsafe_allow_html=True)

    mensagem = st.text_area(
        "mensagem",
        placeholder="Digite aqui o texto que deseja enviar...",
        height=180,
        key="msg_texto",
        label_visibility="collapsed",
    )

    col_cnt, col_img = st.columns([3, 1])
    with col_cnt:
        chars = len(mensagem)
        cor   = "#f87171" if chars > 1000 else "#25d366" if chars > 0 else "#4a5568"
        st.markdown(f'<span style="color:{cor};font-size:0.78rem;font-family:\'DM Mono\',monospace">{chars} caracteres</span>', unsafe_allow_html=True)
    with col_img:
        com_imagem = st.toggle("📎 Com imagem", value=False, key="toggle_img")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── 2. Destinos ────────────────────────────────────────────────────────────
    st.markdown('<div class="card"><div class="card-title">🎯 Destinos</div>', unsafe_allow_html=True)

    col_cb1, col_cb2 = st.columns(2)
    with col_cb1:
        usar_grupos   = st.checkbox("📢 Grupos", value=True)
    with col_cb2:
        usar_contatos = st.checkbox("👤 Contatos por nome", value=False)

    grupos_sel    = []
    contatos_sel  = []

    # Grupos
    if usar_grupos:
        st.markdown("---")
        col_bg, col_bt = st.columns([3, 1])
        with col_bg:
            filtro_grupo = st.text_input("Filtrar grupos por nome", placeholder="Ex: GRC, Compliance...", key="fg")
        with col_bt:
            st.markdown("<div style='margin-top:1.75rem'>", unsafe_allow_html=True)
            if st.button("🔄 Carregar grupos", key="btn_grupos", use_container_width=True):
                with st.spinner("Buscando grupos na API..."):
                    try:
                        st.session_state.grupos_cache = fetch_grupos()
                    except Exception as e:
                        st.error(f"Erro: {e}")
            st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.grupos_cache:
            todos  = st.session_state.grupos_cache
            f      = filtro_grupo.strip().lower()
            lista  = [g for g in todos if f in g["nome"].lower()] if f else todos

            st.caption(f"{len(lista)} de {len(todos)} grupo(s)")

            col_sel, col_all = st.columns([4, 1])
            with col_all:
                sel_todos = st.checkbox("Todos", key="sel_all_g")

            opcoes = {g["nome"]: g["id"] for g in lista}
            if sel_todos:
                nomes_sel = list(opcoes.keys())
                st.markdown(
                    f'<div class="chip-wrap">' +
                    "".join(f'<span class="chip">📢 {n}</span>' for n in nomes_sel[:12]) +
                    (f'<span class="chip">+{len(nomes_sel)-12} mais</span>' if len(nomes_sel) > 12 else "") +
                    '</div>', unsafe_allow_html=True
                )
            else:
                with col_sel:
                    nomes_sel = st.multiselect(
                        "Selecionar grupos",
                        options=list(opcoes.keys()),
                        key="ms_grupos",
                        label_visibility="collapsed",
                    )
            grupos_sel = [opcoes[n] for n in nomes_sel]

    # Contatos
    FILTRO_CONTATOS = "ABC1234teste"  # ← troque aqui pelo nome real

    if usar_contatos:
        st.markdown("---")
        st.markdown(
            f'<div style="color:#8892a4;font-size:0.8rem;margin-bottom:0.7rem">'
            f'Buscando contatos cujo nome contenha: '
            f'<span style="color:#25d366;font-family:\'DM Mono\',monospace;font-weight:600">'
            f'"{FILTRO_CONTATOS}"</span></div>',
            unsafe_allow_html=True,
        )

        if st.button("🔍 Carregar contatos", key="btn_contatos", use_container_width=False):
            with st.spinner(f"Buscando contatos com '{FILTRO_CONTATOS}'..."):
                try:
                    st.session_state.contatos_cache = fetch_contatos(FILTRO_CONTATOS)
                    if not st.session_state.contatos_cache:
                        st.warning(f"Nenhum contato encontrado com '{FILTRO_CONTATOS}'.")
                except Exception as e:
                    st.error(f"Erro: {e}")

        if st.session_state.contatos_cache:
            lista_c = st.session_state.contatos_cache
            st.caption(f"{len(lista_c)} contato(s) encontrado(s)")
            opcoes_c = {f"{c['nome']}  ·  {c['id'].split('@')[0]}": c["id"] for c in lista_c}
            nomes_c  = st.multiselect(
                "Selecionar contatos",
                options=list(opcoes_c.keys()),
                default=list(opcoes_c.keys()),
                key="ms_contatos",
                label_visibility="collapsed",
            )
            contatos_sel = [opcoes_c[n] for n in nomes_c]

    st.markdown('</div>', unsafe_allow_html=True)

    # ── 3. Enviar ──────────────────────────────────────────────────────────────
    todos_destinos = grupos_sel + contatos_sel
    total = len(todos_destinos)

    pronto = bool(mensagem.strip()) and total > 0

    if total > 0:
        st.markdown(
            f'<div style="color:#25d366;font-size:0.88rem;font-weight:700;margin-bottom:0.7rem">'
            f'📨 {total} destino(s) selecionado(s) — {len(grupos_sel)} grupo(s) · {len(contatos_sel)} contato(s)'
            f'</div>', unsafe_allow_html=True
        )

    if st.button(
        f"📤  Enviar para {total} destino(s)" if total else "📤  Selecione destinos para enviar",
        disabled=not pronto,
        use_container_width=True,
        key="btn_enviar",
    ):
        barra    = st.progress(0, text="Iniciando...")
        enviados = 0
        falhas   = 0
        log_now  = []
        brasilia = timezone(timedelta(hours=-3))

        for i, jid in enumerate(todos_destinos):
            # descobre nome
            nome_dest = jid.split("@")[0]
            for g in (st.session_state.grupos_cache or []):
                if g["id"] == jid:
                    nome_dest = g["nome"]; break
            for c in (st.session_state.contatos_cache or []):
                if c["id"] == jid:
                    nome_dest = c["nome"]; break

            try:
                ok = enviar_msg(jid, mensagem, com_imagem)
            except Exception:
                ok = False

            if ok:
                enviados += 1
            else:
                falhas += 1

            ts = datetime.now(brasilia).strftime("%H:%M:%S")
            log_now.append({"ts": ts, "nome": nome_dest, "ok": ok})
            barra.progress((i + 1) / total, text=f"{i+1}/{total} — {nome_dest}")
            time.sleep(2)

        barra.empty()

        # Salva no histórico global
        st.session_state.historico = log_now + st.session_state.historico

        # Resultado
        col_ok, col_fail = st.columns(2)
        with col_ok:
            st.markdown(f'<div class="stat-ok"><div class="stat-num-ok">{enviados}</div><div class="stat-lbl" style="color:#25d366">Enviados</div></div>', unsafe_allow_html=True)
        with col_fail:
            st.markdown(f'<div class="stat-fail"><div class="stat-num-fail">{falhas}</div><div class="stat-lbl" style="color:#f87171">Falhas</div></div>', unsafe_allow_html=True)

        if enviados > 0:
            st.balloons()


# ═══════════════════════════════════════════════════════════════════════════════
# COLUNA LATERAL — histórico e status
# ═══════════════════════════════════════════════════════════════════════════════
with col_side:

    # Status da conexão
    st.markdown('<div class="card"><div class="card-title">⚡ Conexão</div>', unsafe_allow_html=True)
    api_ok = bool(_api_url() and os.getenv("WHATSAPP_API_KEY"))
    if api_ok:
        st.markdown('<span style="color:#25d366;font-weight:700">● API configurada</span>', unsafe_allow_html=True)
        st.caption(f"Instância: {_instance()}")
    else:
        st.markdown('<span style="color:#f87171;font-weight:700">● Secrets não configurados</span>', unsafe_allow_html=True)
        st.caption("Configure WHATSAPP_API_URL, WHATSAPP_API_KEY e WHATSAPP_INSTANCE nos Secrets do Streamlit.")
    st.markdown('</div>', unsafe_allow_html=True)

    # Preview da mensagem
    if mensagem.strip():
        st.markdown('<div class="card"><div class="card-title">👁️ Preview</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="
            background:#111b21;
            border-radius:12px;
            padding:1rem 1.1rem;
            font-family:'DM Mono',monospace;
            font-size:0.82rem;
            color:#e9edef;
            line-height:1.6;
            white-space:pre-wrap;
            word-break:break-word;
            border-left:3px solid #25d366;
        ">{mensagem}</div>
        """, unsafe_allow_html=True)
        if com_imagem:
            st.caption("📎 Será enviado com imagem ForExperts")
        st.markdown('</div>', unsafe_allow_html=True)

    # Histórico
    if st.session_state.historico:
        st.markdown('<div class="card"><div class="card-title">📋 Histórico da sessão</div>', unsafe_allow_html=True)
        for entry in st.session_state.historico[:30]:
            cls   = "log-ok" if entry["ok"] else "log-fail"
            icon  = "✓" if entry["ok"] else "✗"
            st.markdown(
                f'<div class="log-line">'
                f'<span class="log-time">{entry["ts"]}</span>'
                f'<span class="{cls}">{icon} {entry["nome"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        if len(st.session_state.historico) > 30:
            st.caption(f"... e mais {len(st.session_state.historico)-30} registros")
        st.markdown('</div>', unsafe_allow_html=True)
