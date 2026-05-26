"""
ForExperts — WhatsApp Worker
Roda no Railway como serviço separado.
Recebe jobs do Streamlit e envia mensagens em background.

Variáveis de ambiente no Railway:
    WORKER_SECRET  = "senha-compartilhada-com-streamlit"
    PORT           = 8000 (Railway define automaticamente)
"""

import os
import time
import uuid
import threading
import requests
import urllib3
from flask import Flask, request, jsonify

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# jobs em memória: {job_id: {status, enviados, falhas, total}}
jobs = {}


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

    jobs[job_id]["status"]  = "running"
    jobs[job_id]["total"]   = len(destinos)
    enviados = falhas = 0

    for jid in destinos:
        ok = enviar_msg(jid, mensagem, api_url, api_key, instance,
                        imagem_b64, imagem_mime, imagem_nome)
        if ok:
            enviados += 1
        else:
            falhas += 1
        jobs[job_id]["enviados"] = enviados
        jobs[job_id]["falhas"]   = falhas
        time.sleep(2)

    jobs[job_id]["status"] = "done"

    # notifica via WhatsApp ao terminar
    msg_resultado = (
        f"✅ *ForExperts — Disparo concluído*\n\n"
        f"📨 Job: `{job_id}`\n"
        f"✓ Enviados: {enviados}\n"
        f"✗ Falhas: {falhas}\n"
        f"Total: {len(destinos)}"
    )
    notificar(notify_jid, msg_resultado, api_url, api_key, instance)


@app.route("/dispatch", methods=["POST"])
def dispatch():
    data = request.get_json()
    if not data:
        return jsonify({"error": "payload vazio"}), 400

    # valida secret
    if data.get("secret") != os.getenv("WORKER_SECRET", ""):
        return jsonify({"error": "unauthorized"}), 401

    # valida campos obrigatórios
    for campo in ["destinos", "mensagem", "api_url", "api_key", "instance"]:
        if not data.get(campo):
            return jsonify({"error": f"campo obrigatorio ausente: {campo}"}), 400

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "queued", "enviados": 0, "falhas": 0, "total": len(data["destinos"])}

    # roda em thread separada
    t = threading.Thread(target=processar_job, args=(job_id, data), daemon=True)
    t.start()

    return jsonify({"job_id": job_id, "total": len(data["destinos"]), "status": "queued"})


@app.route("/status/<job_id>", methods=["GET"])
def status(job_id):
    if job_id not in jobs:
        return jsonify({"error": "job não encontrado"}), 404
    return jsonify(jobs[job_id])


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "jobs_ativos": len(jobs)})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
