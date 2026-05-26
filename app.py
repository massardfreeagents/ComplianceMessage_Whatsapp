"""
ForExperts — Agente de Disparo WhatsApp
Secrets necessários:
    WHATSAPP_API_URL, WHATSAPP_API_KEY, WHATSAPP_INSTANCE
    WHATSAPP_GROUPS, WHATSAPP_CONTACTS
    GROQ_API_KEY
    NOTIFY_WHATSAPP, WORKER_URL, WORKER_SECRET
"""

import os, base64, time, urllib3
import streamlit as st
import requests
from datetime import datetime, timezone, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="ForExperts · WhatsApp", page_icon="📱",
                   layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@400;500&display=swap');
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] { font-family:'Syne',sans-serif; background:#080e1a; color:#dde2ee; }
.stApp { background:#080e1a; }
section.main > div { max-width:720px !important; margin:0 auto; padding:1rem 1rem 4rem; }
.hero { padding:1.5rem; background:linear-gradient(120deg,#0a1628 0%,#0d2010 60%,#080e1a 100%);
    border:1px solid rgba(37,211,102,0.18); border-radius:16px; margin-bottom:1.5rem;
    position:relative; overflow:hidden; }
.hero::after { content:''; position:absolute; right:-40px; top:-40px; width:200px; height:200px;
    background:radial-gradient(circle,rgba(37,211,102,0.07) 0%,transparent 70%); pointer-events:none; }
.hero-row { display:flex; align-items:center; gap:1rem; }
.hero-icon { font-size:2.4rem; line-height:1; filter:drop-shadow(0 0 14px rgba(37,211,102,0.5)); }
.hero-title { font-size:1.5rem; font-weight:800; color:#fff; margin:0; line-height:1.1; }
.hero-sub { color:#25d366; font-size:0.72rem; font-weight:600; letter-spacing:0.13em; text-transform:uppercase; margin-top:0.25rem; }
.hero-status { margin-top:0.9rem; font-size:0.8rem; }
.card { background:rgba(255,255,255,0.028); border:1px solid rgba(255,255,255,0.07);
    border-radius:14px; padding:1.2rem 1.3rem; margin-bottom:1rem; }
.card-title { font-size:0.7rem; font-weight:700; color:#25d366; text-transform:uppercase;
    letter-spacing:0.13em; margin-bottom:0.9rem; }
.bubble { background:#1f2c34; border-radius:0 12px 12px 12px; padding:0.8rem 1rem;
    font-family:'DM Mono',monospace; font-size:0.82rem; color:#e9edef; line-height:1.6;
    white-space:pre-wrap; word-break:break-word; border-left:3px solid #25d366; margin-top:0.5rem; }
.result-grid { display:grid; grid-template-columns:1fr 1fr; gap:0.8rem; margin-top:1rem; }
.stat-ok { background:rgba(37,211,102,0.08); border:1px solid rgba(37,211,102,0.25);
    border-radius:12px; padding:1rem; text-align:center; }
.stat-fail { background:rgba(248,113,113,0.08); border:1px solid rgba(248,113,113,0.25);
    border-radius:12px; padding:1rem; text-align:center; }
.stat-num-ok { font-size:2rem; font-weight:800; color:#25d366; }
.stat-num-fail { font-size:2rem; font-weight:800; color:#f87171; }
.stat-lbl { font-size:0.68rem; text-transform:uppercase; letter-spacing:0.1em; margin-top:0.2rem; }
.log-line { font-family:'DM Mono',monospace; font-size:0.74rem; padding:5px 0;
    border-bottom:1px solid rgba(255,255,255,0.04); display:flex; gap:0.8rem; align-items:center; }
.log-ok { color:#25d366; } .log-fail { color:#f87171; } .log-time { color:#4a5568; white-space:nowrap; }
.stTextArea textarea { background:#0f1a2e !important; border:1px solid rgba(37,211,102,0.25) !important;
    border-radius:10px !important; color:#dde2ee !important;
    font-family:'DM Mono',monospace !important; font-size:0.88rem !important; line-height:1.65 !important; }
.stTextInput input { background:#0f1a2e !important; border:1px solid rgba(255,255,255,0.1) !important;
    border-radius:8px !important; color:#dde2ee !important; font-size:0.88rem !important; }
.stButton > button { font-family:'Syne',sans-serif !important; font-weight:700 !important;
    border-radius:10px !important; width:100%; }
.stMultiSelect [data-baseweb="tag"] { background:rgba(37,211,102,0.15) !important; color:#25d366 !important; }
.stCheckbox label, .stToggle label { font-size:0.95rem !important; padding:0.3rem 0 !important; }
.bg-info { background:rgba(37,211,102,0.08); border:1px solid rgba(37,211,102,0.2);
    border-radius:10px; padding:0.8rem 1rem; font-size:0.82rem; color:#25d366; margin-top:0.5rem; }
</style>
""", unsafe_allow_html=True)


# ─── Helpers API ──────────────────────────────────────────────────────────────
def _api_url():  return os.getenv("WHATSAPP_API_URL","").rstrip("/")
def _instance(): return os.getenv("WHATSAPP_INSTANCE","ForExperts")
def _headers():  return {"apikey":os.getenv("WHATSAPP_API_KEY",""),"Content-Type":"application/json"}

def fetch_grupos():
    url  = f"{_api_url()}/group/fetchAllGroups/{_instance()}?getParticipants=false"
    resp = requests.get(url, headers=_headers(), timeout=20, verify=False)
    resp.raise_for_status()
    data  = resp.json()
    items = data if isinstance(data,list) else data.get("groups",[])
    return sorted([{"id":g.get("id") or g.get("remoteJid",""),
                    "nome":g.get("subject") or g.get("name","Sem nome")} for g in items],
                  key=lambda x:x["nome"].lower())

def load_contacts_from_secret():
    raw = os.getenv("WHATSAPP_CONTACTS","")
    if not raw: return []
    result = []
    for entry in raw.split(","):
        entry = entry.strip()
        if "|" not in entry: continue
        nome, numero = entry.split("|",1)
        result.append({"id":f"{numero.strip()}@s.whatsapp.net","nome":nome.strip()})
    return result

def corrigir_portugues(texto):
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization":f"Bearer {os.getenv('GROQ_API_KEY','')}","Content-Type":"application/json"},
        json={"model":"llama-3.3-70b-versatile","max_tokens":1000,"messages":[
            {"role":"system","content":"Corrija apenas os erros de ortografia, acentuacao e gramatica. Nao mude estilo, tom, emojis, estrutura. Retorne SOMENTE o texto corrigido."},
            {"role":"user","content":texto}
        ]}, timeout=30)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()

def enviar_msg(jid, texto, imagem_b64=None, imagem_mime="image/jpeg", imagem_nome="imagem.jpg"):
    base=_api_url(); inst=_instance(); h=_headers()
    if imagem_b64:
        payload={"number":jid,"mediatype":"image","mimetype":imagem_mime,
                 "caption":texto,"media":imagem_b64,"fileName":imagem_nome}
        endpoint=f"{base}/message/sendMedia/{inst}"
    else:
        payload={"number":jid,"text":texto}
        endpoint=f"{base}/message/sendText/{inst}"
    r = requests.post(endpoint, headers=h, json=payload, timeout=60, verify=False)
    return r.status_code in [200,201]

def disparar_background(destinos, mensagem, imagem_b64, imagem_mime, imagem_nome):
    worker_url    = os.getenv("WORKER_URL","")
    worker_secret = os.getenv("WORKER_SECRET","")
    if not worker_url:
        return False, "WORKER_URL não configurado"
    payload = {
        "secret":      worker_secret,
        "mensagem":    mensagem,
        "destinos":    destinos,
        "imagem_b64":  imagem_b64 or "",
        "imagem_mime": imagem_mime,
        "imagem_nome": imagem_nome,
        "notify_jid":  os.getenv("NOTIFY_WHATSAPP","") + "@s.whatsapp.net",
        "api_url":     _api_url(),
        "api_key":     os.getenv("WHATSAPP_API_KEY",""),
        "instance":    _instance(),
    }
    try:
        r = requests.post(f"{worker_url}/dispatch", json=payload, timeout=15)
        if r.status_code == 200:
            return True, r.json().get("job_id","")
        return False, r.text
    except Exception as e:
        return False, str(e)


# ─── Session state ─────────────────────────────────────────────────────────────
for k,v in {"grupos_cache":[],"contatos_cache":[],"historico":[],"msg_corrigida":"",
            "contatos_excluidos":set(),"grupos_excluidos":set()}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── HERO ──────────────────────────────────────────────────────────────────────
api_ok    = bool(_api_url() and os.getenv("WHATSAPP_API_KEY"))
worker_ok = bool(os.getenv("WORKER_URL"))
status_html = (
    f'<span style="color:#25d366;font-weight:700">● API conectada</span>'
    f'<span style="color:#4a5568;font-size:0.75rem"> · {_instance()}</span>'
    + (f' <span style="color:#25d366;font-size:0.75rem">· Worker ativo</span>' if worker_ok else
       f' <span style="color:#fbbf24;font-size:0.75rem">· Worker não configurado</span>')
    if api_ok else '<span style="color:#f87171;font-weight:700">● Secrets não configurados</span>'
)
st.markdown(f"""
<div class="hero">
    <div class="hero-row">
        <div class="hero-icon">📱</div>
        <div><div class="hero-sub">ForExperts · Agente</div>
        <div class="hero-title">Disparo WhatsApp</div></div>
    </div>
    <div class="hero-status">{status_html}</div>
</div>
""", unsafe_allow_html=True)

# ─── 1. MENSAGEM ───────────────────────────────────────────────────────────────
st.markdown('<div class="card"><div class="card-title">✏️ Mensagem</div>', unsafe_allow_html=True)

if st.session_state.msg_corrigida:
    st.session_state.msg_texto = st.session_state.msg_corrigida
    st.session_state.msg_corrigida = ""

mensagem = st.text_area("Texto", placeholder="Digite aqui o texto que deseja enviar...",
                        height=160, key="msg_texto", label_visibility="collapsed")

chars = len(mensagem)
cor   = "#f87171" if chars>1000 else "#25d366" if chars>0 else "#4a5568"
st.markdown(f'<span style="color:{cor};font-size:0.76rem;font-family:\'DM Mono\',monospace">{chars} caracteres</span>',
            unsafe_allow_html=True)

if st.button("🔤 Corrigir português", key="btn_corrigir", use_container_width=True, disabled=not mensagem.strip()):
    with st.spinner("Corrigindo..."):
        try:
            corrigido = corrigir_portugues(mensagem)
            if corrigido != mensagem:
                st.session_state.msg_corrigida = corrigido
                st.rerun()
            else:
                st.success("✅ Nenhum erro encontrado!")
        except Exception as e:
            st.error(f"Erro na correção: {e}")

uploaded_img = st.file_uploader("📎 Anexar imagem (opcional)",
                                type=["jpg","jpeg","png","webp"], key="img_upload")
if mensagem.strip():
    st.markdown(f'<div class="bubble">{mensagem}</div>', unsafe_allow_html=True)
if uploaded_img:
    st.image(uploaded_img, caption="Imagem que será enviada", use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)

# ─── 2. DESTINOS ───────────────────────────────────────────────────────────────
st.markdown('<div class="card"><div class="card-title">🎯 Destinos</div>', unsafe_allow_html=True)

usar_grupos   = st.checkbox("📢 Grupos",             value=True,  key="cb_grupos")
usar_contatos = st.checkbox("👤 Contatos da agenda",  value=False, key="cb_contatos")

grupos_sel   = []
contatos_sel = []

# ── Grupos ─────────────────────────────────────────────────────────────────────
if usar_grupos:
    st.markdown("---")
    st.markdown('<div class="card-title" style="margin-bottom:0.5rem">📢 Grupos</div>', unsafe_allow_html=True)

    grupos_raw = os.getenv("WHATSAPP_GROUPS","")
    jids_fixos = [g.strip() for g in grupos_raw.split(",") if g.strip()]

    if not jids_fixos:
        st.warning("⚠️ Secret WHATSAPP_GROUPS não configurado.")
    else:
        if not st.session_state.grupos_cache:
            with st.spinner("Carregando nomes dos grupos..."):
                try:
                    todos_api = fetch_grupos()
                    mapa = {g["id"]:g["nome"] for g in todos_api}
                    st.session_state.grupos_cache = [
                        {"id":jid,"nome":mapa.get(jid,jid.split("@")[0])} for jid in jids_fixos]
                except Exception:
                    st.session_state.grupos_cache = [
                        {"id":jid,"nome":jid.split("@")[0]} for jid in jids_fixos]

        lista = [g for g in st.session_state.grupos_cache
                 if g["id"] not in st.session_state.grupos_excluidos]

        st.caption(f"{len(lista)} grupo(s) — toque no ✕ para excluir")

        cols = st.columns(2)
        for i, g in enumerate(lista):
            with cols[i % 2]:
                col_nome, col_x = st.columns([5,1])
                with col_nome:
                    st.markdown(f'<div style="font-size:0.8rem;padding:4px 0;color:#dde2ee">'
                                f'📢 {g["nome"]}</div>', unsafe_allow_html=True)
                with col_x:
                    if st.button("✕", key=f"del_g_{g['id']}", help=f"Remover {g['nome']}"):
                        st.session_state.grupos_excluidos.add(g["id"])
                        st.rerun()

        grupos_sel = [g["id"] for g in lista]

        if st.session_state.grupos_excluidos:
            if st.button("↺ Restaurar grupos removidos", key="restore_grupos"):
                st.session_state.grupos_excluidos = set()
                st.rerun()

# ── Contatos ───────────────────────────────────────────────────────────────────
if usar_contatos:
    st.markdown("---")
    st.markdown('<div class="card-title" style="margin-bottom:0.5rem">👤 Contatos</div>', unsafe_allow_html=True)

    if not st.session_state.contatos_cache:
        st.session_state.contatos_cache = load_contacts_from_secret()

    if not st.session_state.contatos_cache:
        st.warning("⚠️ Secret WHATSAPP_CONTACTS não configurado.")
    else:
        import pandas as pd

        filtro = st.text_input("🔎 Filtrar por nome", key="filtro_contato",
                               placeholder="Digite para filtrar...",
                               label_visibility="collapsed")

        todos_c = st.session_state.contatos_cache
        lista_c = [c for c in todos_c
                   if not filtro or filtro.lower() in c["nome"].lower()]

        total_excluidos = len(st.session_state.contatos_excluidos)
        ativos = [c for c in lista_c if c["id"] not in st.session_state.contatos_excluidos]
        st.caption(f"{len(ativos)} ativo(s)" + (f" · {total_excluidos} removido(s)" if total_excluidos else ""))

        # data_editor com checkbox — compacto, sem botão extra
        df = pd.DataFrame([{
            "✓":    c["id"] not in st.session_state.contatos_excluidos,
            "Nome": c["nome"],
            "_id":  c["id"],
        } for c in lista_c])

        edited = st.data_editor(
            df[["✓","Nome"]],
            use_container_width=True,
            hide_index=True,
            height=400,
            column_config={
                "✓":    st.column_config.CheckboxColumn("✓", width="small"),
                "Nome": st.column_config.TextColumn("Nome", disabled=True),
            },
            key="contact_editor"
        )

        # atualiza excluídos baseado no checkbox — sem rerun
        novos_excluidos = set()
        for i, row in edited.iterrows():
            if not row["✓"]:
                novos_excluidos.add(lista_c[i]["id"])
        st.session_state.contatos_excluidos = novos_excluidos

        if total_excluidos:
            if st.button("↺ Restaurar todos", key="restore_contatos", use_container_width=True):
                st.session_state.contatos_excluidos = set()
                st.rerun()

        contatos_sel = [c["id"] for c in todos_c
                        if c["id"] not in st.session_state.contatos_excluidos]

st.markdown('</div>', unsafe_allow_html=True)

# ─── 3. MODO DE ENVIO ──────────────────────────────────────────────────────────
todos_destinos = grupos_sel + contatos_sel
total  = len(todos_destinos)
pronto = bool(mensagem.strip()) and total > 0

if total > 0:
    st.markdown(
        f'<div style="color:#25d366;font-size:0.85rem;font-weight:700;margin-bottom:0.5rem">'
        f'📨 {total} destino(s): {len(grupos_sel)} grupo(s) + {len(contatos_sel)} contato(s)</div>',
        unsafe_allow_html=True)

# prepara imagem
imagem_b64 = None; imagem_mime = "image/jpeg"; imagem_nome = "imagem.jpg"
if uploaded_img:
    uploaded_img.seek(0)
    imagem_b64  = base64.b64encode(uploaded_img.read()).decode("utf-8")
    imagem_mime = uploaded_img.type or "image/jpeg"
    imagem_nome = uploaded_img.name or "imagem.jpg"

# modo de envio
if worker_ok:
    modo = st.radio("Modo de envio", ["🔕 Background (recomendado)", "📲 Direto (tela ativa)"],
                    key="modo_envio", horizontal=True)
    if "Background" in modo:
        st.markdown(
            '<div class="bg-info">🔕 <b>Background:</b> o envio roda no servidor. '
            'Você pode fechar o app e receberá uma mensagem no WhatsApp ao terminar.</div>',
            unsafe_allow_html=True)
else:
    modo = "📲 Direto (tela ativa)"
    st.markdown(
        '<div style="color:#fbbf24;font-size:0.8rem;margin-bottom:0.5rem">'
        '⚠️ Worker não configurado — envio direto apenas (mantenha a tela ativa).</div>',
        unsafe_allow_html=True)

if st.button(
    f"📤  Enviar para {total} destino(s)" if total else "📤  Selecione destinos",
    disabled=not pronto, key="btn_enviar"
):
    if "Background" in modo:
        with st.spinner("Despachando job para o servidor..."):
            ok, info = disparar_background(todos_destinos, mensagem, imagem_b64, imagem_mime, imagem_nome)
        if ok:
            st.success(f"✅ Job despachado! ID: `{info}`\n\nO servidor enviará para {total} destinos. "
                       f"Você receberá uma mensagem no WhatsApp quando terminar.")
        else:
            st.error(f"Erro ao despachar job: {info}")
    else:
        barra    = st.progress(0, text="Iniciando...")
        brasilia = timezone(timedelta(hours=-3))
        enviados = falhas = 0
        log_now  = []

        for i, jid in enumerate(todos_destinos):
            nome_dest = jid.split("@")[0]
            for g in (st.session_state.grupos_cache or []):
                if g["id"]==jid: nome_dest=g["nome"]; break
            for c in (st.session_state.contatos_cache or []):
                if c["id"]==jid: nome_dest=c["nome"]; break
            try:
                ok = enviar_msg(jid, mensagem, imagem_b64, imagem_mime, imagem_nome)
            except Exception:
                ok = False
            if ok: enviados+=1
            else:  falhas+=1
            ts = datetime.now(brasilia).strftime("%H:%M:%S")
            log_now.append({"ts":ts,"nome":nome_dest,"ok":ok})
            barra.progress((i+1)/total, text=f"{i+1}/{total} · {nome_dest}")
            time.sleep(2)

        barra.empty()
        st.session_state.historico = log_now + st.session_state.historico
        st.markdown(f"""
        <div class="result-grid">
            <div class="stat-ok"><div class="stat-num-ok">{enviados}</div>
                <div class="stat-lbl" style="color:#25d366">Enviados</div></div>
            <div class="stat-fail"><div class="stat-num-fail">{falhas}</div>
                <div class="stat-lbl" style="color:#f87171">Falhas</div></div>
        </div>""", unsafe_allow_html=True)
        if enviados > 0:
            st.balloons()

# ─── 4. HISTÓRICO ──────────────────────────────────────────────────────────────
if st.session_state.historico:
    st.markdown('<div class="card"><div class="card-title">📋 Histórico da sessão</div>',
                unsafe_allow_html=True)
    for entry in st.session_state.historico[:40]:
        cls  = "log-ok" if entry["ok"] else "log-fail"
        icon = "✓" if entry["ok"] else "✗"
        st.markdown(
            f'<div class="log-line"><span class="log-time">{entry["ts"]}</span>'
            f'<span class="{cls}">{icon} {entry["nome"]}</span></div>',
            unsafe_allow_html=True)
    if len(st.session_state.historico)>40:
        st.caption(f"... e mais {len(st.session_state.historico)-40} registros")
    st.markdown('</div>', unsafe_allow_html=True)
