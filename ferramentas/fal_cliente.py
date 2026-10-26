"""
Cliente unico da fal.ai para o Farrapos: chave, saldo, envio de arquivo e fila.

Desde 18/9/2026 tudo que o Farrapos gera ou analisa passa pela fal, para os custos
ficarem numa conta so (decisao do Alexandre). Nenhum script daqui chama a API do
Google direto; o Gemini continua sendo o modelo de imagem, mas cobrado pela fal
("Nano Banana 2" = gemini-3.1-flash-image).

A chave lida e' so a FAL_KEY. O .env de video-reels-test e' compartilhado com
outros ~25 projetos (video-studio em producao, RAG do SDR); dele saem apenas as
linhas que o Farrapos usa, nunca a GEMINI_API_KEY.

Fila copiada do kling-animar.py do trailer, que gerou os takes de 17 e 18/9.
"""
import json
import mimetypes
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

FILA = "https://queue.fal.run"
ENV = pathlib.Path.home() / "Projetos" / "video-reels-test" / ".env"


def chave():
    k = os.environ.get("FAL_KEY")
    if k:
        return k
    if ENV.exists():
        for l in ENV.read_text().splitlines():
            if l.startswith("FAL_KEY="):
                return l.split("=", 1)[1].strip()
    sys.exit("sem FAL_KEY")


def _get(url, k):
    return json.load(urllib.request.urlopen(urllib.request.Request(
        url, headers={"Authorization": f"Key {k}"}), timeout=60))


def saldo(k):
    return float(_get("https://rest.alpha.fal.ai/billing/user_balance", k))


def subir(p, k):
    """Sobe um arquivo local para o CDN da fal e devolve a URL."""
    p = pathlib.Path(p)
    tipo = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    ini = urllib.request.Request(
        "https://rest.alpha.fal.ai/storage/upload/initiate?storage_type=fal-cdn-v3",
        data=json.dumps({"content_type": tipo, "file_name": p.name}).encode(),
        headers={"Authorization": f"Key {k}", "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(ini, timeout=60))
    urllib.request.urlopen(urllib.request.Request(
        r["upload_url"], data=p.read_bytes(), headers={"Content-Type": tipo}, method="PUT"), timeout=300)
    return r["file_url"]


def _namespace(endpoint, pedido, k):
    """O namespace de consulta nao e' sempre o endpoint inteiro (Topaz, 17/9/2026:
    supus 'topaz' e era 'topaz/upscale', e o laco girou para sempre)."""
    partes = endpoint.split("/")
    for n in range(len(partes), 0, -1):
        ns = "/".join(partes[:n])
        try:
            _get(f"{FILA}/{ns}/requests/{pedido}/status", k)
            return ns
        except urllib.error.HTTPError as e:
            if e.code != 405:
                return ns
        except Exception:
            pass
    sys.exit(f"nao achei o namespace de consulta de {endpoint}")


def rodar(endpoint, corpo, k, intervalo=3, limite=1800, falar=True):
    """Entra na fila, espera e devolve o JSON do resultado. Erro vira (None, texto)."""
    req = urllib.request.Request(f"{FILA}/{endpoint}", data=json.dumps(corpo).encode(),
                                 headers={"Authorization": f"Key {k}", "Content-Type": "application/json"})
    try:
        job = json.load(urllib.request.urlopen(req, timeout=120))
    except urllib.error.HTTPError as e:
        return None, f"erro {e.code}: {e.read().decode()[:300]}"
    pedido = job["request_id"]
    ns = _namespace(endpoint, pedido, k)
    inicio, falhas = time.time(), 0
    while True:
        time.sleep(intervalo)
        try:
            s = _get(f"{FILA}/{ns}/requests/{pedido}/status", k)
            falhas = 0
        except Exception as e:
            falhas += 1
            if falhas >= 12:
                return None, f"consulta falhou 12 vezes ({type(e).__name__}); confira {FILA}/{ns}/requests/{pedido}"
            continue
        if s.get("status") == "COMPLETED":
            break
        if s.get("status") == "ERROR":
            return None, "erro na geracao: " + json.dumps(s)[:300]
        if time.time() - inicio > limite:
            return None, f"passou de {limite}s; confira {FILA}/{ns}/requests/{pedido}"
    try:
        return _get(f"{FILA}/{ns}/requests/{pedido}", k), None
    except urllib.error.HTTPError as e:
        return None, f"resultado {e.code}: {e.read().decode()[:300]}"


def baixar(url):
    return urllib.request.urlopen(url, timeout=300).read()


# --- imagem: Gemini 3.1 Flash Image pela fal ---------------------------------

# nano-banana-2 = Gemini 3.1 Flash Image (cenas, retratos). nano-banana-pro = Gemini 3 Pro
# Image (correcao pontual, o corrigir-imagem-gemini.py usava gemini-3-pro-image no Google).
# Preco do nano-banana-2 na pagina da fal em 18/9/2026: US$ 0,08 em 1K; 2K = 1,5x; 4K = 2x;
# 0.5K = 0,75x. O do pro a pagina da API nao mostra: NAO CONFERIDO.
PRECO_IMAGEM = {"0.5K": 0.06, "1K": 0.08, "2K": 0.12, "4K": 0.16}


def gerar_imagem(prompt, refs, k, resolucao="1K", proporcao="9:16", seed=None, modelo="nano-banana-2"):
    """refs: arquivos locais que entram como referencia (rosto, primeiro quadro).
    Devolve (bytes, None) ou (None, erro)."""
    corpo = {"prompt": prompt, "num_images": 1, "aspect_ratio": proporcao,
             "resolution": resolucao, "output_format": "png"}
    if seed is not None:
        corpo["seed"] = seed
    if refs:
        corpo["image_urls"] = [subir(r, k) for r in refs]
    res, erro = rodar(f"fal-ai/{modelo}/edit" if refs else f"fal-ai/{modelo}", corpo, k)
    if erro:
        return None, erro
    imgs = res.get("images") or []
    if not imgs:
        return None, "sem imagem: " + (res.get("description") or json.dumps(res)[:200])
    return baixar(imgs[0]["url"]), None


# --- analise: modelos que veem e ouvem, pela fal (OpenRouter) ----------------

ANALISE_MODELO = "google/gemini-2.5-pro"


def analisar(prompt, k, imagens=(), audio=None, video=None, modelo=ANALISE_MODELO, temperatura=0.2):
    """Pergunta a um modelo multimodal. Cobrado por token na fal; o custo volta em usage.cost.
    Devolve (texto, custo, None) ou (None, 0, erro)."""
    corpo = {"prompt": prompt, "model": modelo, "temperature": temperatura,
             # 18/9/2026: com o gemini-2.5-pro a fal devolve 400 "Reasoning is mandatory for
             # this endpoint and cannot be disabled" se o campo faltar.
             "reasoning": True,
             # 19/9/2026: sem teto, num video de 79 s o raciocinio gastou o orcamento padrao e o
             # "output" voltou vazio, sem erro. Com 8000 a resposta veio inteira.
             "max_tokens": 8000}
    if audio:
        endpoint, corpo["audio_url"] = "openrouter/router/audio", subir(audio, k)
    elif video:
        # video e' lista (video_urls); audio e' campo unico (audio_url). Da documentacao da fal, 18/9/2026.
        endpoint, corpo["video_urls"] = "openrouter/router/video", [subir(video, k)]
    else:
        endpoint, corpo["image_urls"] = "openrouter/router/vision", [subir(i, k) for i in imagens]
    res, erro = rodar(endpoint, corpo, k)
    if erro:
        return None, 0.0, erro
    return res.get("output", ""), float((res.get("usage") or {}).get("cost") or 0), None
