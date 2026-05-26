"""
ForExperts — WhatsApp Worker com persistência PostgreSQL
Variáveis de ambiente no Railway:
    WORKER_SECRET  = "senha-compartilhada"
    DATABASE_URL   = (Railway injeta automaticamente ao linkar o Postgres)
    PORT           = (Railway define automaticamente)
"""

import os
import time
import uuid
import threading
import requests
import urllib3
import psycopg2
import psycopg2.extras
import json
from flask import Flask, request, jsonify
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)


# ─── Database ─────────────────────────────────────────────────────────────────

def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL"), sslmode="require")

def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS wa_jobs (
                    job_id    TEXT PRIMARY KEY,
                    status    TEXT NOT NULL DEFAULT 'queued',
                    total     INTEGER DEFAULT 0,
                    enviados  INTEGER DEFAULT 0,
                    falhas    INTEGER DEFAULT 0,
                    criado_em TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    payload   JSONB
                )
            """)
        conn.commit()

def upsert_job(job_id, status, total, enviados, falhas):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO wa_jobs (job_id, status, total, enviados, falhas, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (job_id) DO UPDATE SET
                    status     = EXCLUDED.status,
                    enviados   = EXCLUDED.enviados,
                    falhas     = EXCLUDED.falhas,
                    updated_at = NOW()
            """, (job_id, status, total, enviados, falhas))
        conn.commit()

def get_job(job_id):
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM wa_jobs WHERE job_id = %s", (job_id,))
            return cur.fetchone()

def save_payload(job_id, payload):
    safe = {k: v for k, v in payload.items() if k != "imagem_b64"}
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE wa_jobs SET payload = %s WHERE job_id = %s
            """, (json.dumps(safe), job_id))
        conn.commit()


# ─── WhatsApp ─────────────────────────────────────────────────────────────────

def enviar_msg(jid, texto, api_url, api_key, instance,
               imagem_b64=None, imagem_mime="image/jpeg", imagem_nome="imagem.jpg"):
    headers  = {"apikey": api_key, "Content-Type": "application/json"}
    if imagem_b64:
        payload  = {"number": jid, "mediatype": "image", "mimetype": imagem_mime,
                    "caption": texto, "media": imagem_b64, "fileName": imagem_nome}
        endpoint = f"{api_url}/message/sendMedia/{instance}"
    else:
        payload  = {"number": jid, "text": texto}
        endpoint = f"{api_url}/message/sendText/{instance}"
    try:
        r = requests.post(endpoint, headers=headers, json=payload, timeout=60, verify=False)
        return r.status_code in [200, 201]
    except Exception:
        return False

def notificar(notify_jid, mensagem, api_url, api_key, instance):
    if not notify_jid or notify_jid == "@s.whatsapp.net":
        return
    enviar_msg(notify_jid, mensagem, api_url, api_key, instance)


# ─── Job processor ────────────────────────────────────────────────────────────

def processar_job(job_id, payload):
    destinos    = payload["destinos"]
    mensagem    = payload["mensagem"]
    imagem_b64  = payload.get("imagem_b64") or None
    imagem_mime = payload.get("imagem_mime", "image/jpeg")
    imagem_nome = payload.get("imagem_nome", "imagem.jpg")
    notify_jid  = payload.get("notify_jid", "")
    api_url     = payload["api_url"]
    api_key     = payload["api_key"]
    instance    = payload["instance"]
    total       = len(destinos)

    upsert_job(job_id, "running", total, 0, 0)
    enviados = falhas = 0

    for jid in destinos:
        ok = enviar_msg(jid, mensagem, api_url, api_key, instance,
                        imagem_b64, imagem_mime, imagem_nome)
        if ok:
            enviados += 1
        else:
            falhas += 1
        # atualiza DB a cada envio
        upsert_job(job_id, "running", total, enviados, falhas)
        time.sleep(2)

    upsert_job(job_id, "done", total, enviados, falhas)

    msg_resultado = (
        f"✅ *ForExperts — Disparo concluído*\n\n"
        f"📨 Job: `{job_id}`\n"
        f"✓ Enviados: {enviados}\n"
        f"✗ Falhas: {falhas}\n"
        f"Total: {total}"
    )
    notificar(notify_jid, msg_resultado, api_url, api_key, instance)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.route("/dispatch", methods=["POST"])
def dispatch():
    data = request.get_json()
    if not data:
        return jsonify({"error": "payload vazio"}), 400
    if data.get("secret") != os.getenv("WORKER_SECRET", ""):
        return jsonify({"error": "unauthorized"}), 401
    for campo in ["destinos", "mensagem", "api_url", "api_key", "instance"]:
        if not data.get(campo):
            return jsonify({"error": f"campo obrigatorio ausente: {campo}"}), 400

    job_id = str(uuid.uuid4())[:8]
    upsert_job(job_id, "queued", len(data["destinos"]), 0, 0)
    save_payload(job_id, data)

    t = threading.Thread(target=processar_job, args=(job_id, data), daemon=True)
    t.start()

    return jsonify({"job_id": job_id, "total": len(data["destinos"]), "status": "queued"})


@app.route("/status/<job_id>", methods=["GET"])
def status(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "job não encontrado"}), 404
    return jsonify({
        "job_id":   job["job_id"],
        "status":   job["status"],
        "total":    job["total"],
        "enviados": job["enviados"],
        "falhas":   job["falhas"],
        "updated_at": str(job["updated_at"]),
    })


@app.route("/jobs", methods=["GET"])
def list_jobs():
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT job_id, status, total, enviados, falhas, criado_em, updated_at
                FROM wa_jobs ORDER BY criado_em DESC LIMIT 20
            """)
            jobs = cur.fetchall()
    return jsonify([dict(j) for j in jobs])


@app.route("/health", methods=["GET"])
def health():
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False
    return jsonify({"status": "ok", "db": "ok" if db_ok else "erro"})


# ─── Init ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
