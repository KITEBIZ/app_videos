"""Entrada com Face ID (passkey) no estúdio da VPS (20/10/2026, ele: "quero entrar somente com face id").

Substitui o usuário e senha do Caddy (basic_auth) por um login do próprio app. Só liga com V2_ENTRADA=1 (no Mac, em
127.0.0.1, segue aberto como antes). Na primeira vez, num aparelho novo, entra com a senha de sempre
(~/estudio-v2-web/senha.txt) e cadastra o Face ID; depois, só o Face ID. A sessão vale 90 dias por aparelho.

Guarda as passkeys e as sessões em ~/.estudio-v2-entrada.json (fora da pasta do projeto).
"""
import hmac, json, os, secrets, threading, time
from pathlib import Path

LIGADA = os.environ.get("V2_ENTRADA") == "1"
if LIGADA:                        # o Mac (aberto) não precisa ter o webauthn instalado
    from webauthn import (generate_registration_options, verify_registration_response, generate_authentication_options,
                          verify_authentication_response, options_to_json)
    from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
    from webauthn.helpers.structs import (AuthenticatorSelectionCriteria, ResidentKeyRequirement,
                                          UserVerificationRequirement, PublicKeyCredentialDescriptor)

DOMINIO = os.environ.get("V2_DOMINIO", "admin.newsbr360.com")
ORIGEM = f"https://{DOMINIO}"
ARQ = Path(os.environ.get("V2_ENTRADA_ARQ", Path.home() / ".estudio-v2-entrada.json"))
SENHA_ARQ = Path(os.environ.get("V2_SENHA_ARQ", Path.home() / "estudio-v2-web/senha.txt"))
COOKIE = "v2sessao"
DURA = 90 * 24 * 3600
LIVRES = ("/entrar", "/api/entrada/", "/logo.png", "/fontes/")      # caminhos que abrem sem sessão
_trava = threading.Lock()
_desafios = {}                    # desafio (b64) -> (tipo, quando)
_erros = []                       # quando errou a senha (trava 10 min depois de 10 erros)


def _ler():
    try:
        return json.loads(ARQ.read_text())
    except (FileNotFoundError, ValueError):
        return {"chaves": [], "sessoes": {}}


def _gravar(d):
    tmp = ARQ.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    os.chmod(tmp, 0o600)
    os.replace(tmp, ARQ)


def _sessao_do_cookie(cabecalho):
    for parte in (cabecalho or "").split(";"):
        nome, _, valor = parte.strip().partition("=")
        if nome == COOKIE:
            return valor
    return None


def vale(cabecalho_cookie):
    s = _sessao_do_cookie(cabecalho_cookie)
    if not s:
        return False
    with _trava:
        fim = _ler()["sessoes"].get(s)
    return bool(fim and fim > time.time())


def livre(caminho):
    return caminho in LIVRES or caminho.startswith(tuple(p for p in LIVRES if p.endswith("/")))


def nova_sessao():
    s = secrets.token_urlsafe(32)
    with _trava:
        d = _ler()
        agora = time.time()
        d["sessoes"] = {k: v for k, v in d["sessoes"].items() if v > agora}
        d["sessoes"][s] = agora + DURA
        _gravar(d)
    return f"{COOKIE}={s}; Max-Age={DURA}; Path=/; Secure; HttpOnly; SameSite=Lax"


def sair(cabecalho_cookie):
    s = _sessao_do_cookie(cabecalho_cookie)
    with _trava:
        d = _ler()
        d["sessoes"].pop(s, None)
        _gravar(d)
    return f"{COOKIE}=; Max-Age=0; Path=/; Secure; HttpOnly; SameSite=Lax"


def _desafio(tipo, ch):
    agora = time.time()
    for k in [k for k, (_, q) in _desafios.items() if agora - q > 300]:
        _desafios.pop(k, None)
    _desafios[bytes_to_base64url(ch)] = (tipo, agora)


def _tirar_desafio(tipo, credencial):
    """O desafio vem assinado dentro do clientDataJSON; confere que fomos nós que demos (e só uma vez)."""
    dados = json.loads(base64url_to_bytes(credencial["response"]["clientDataJSON"]))
    ch = dados.get("challenge", "")
    t = _desafios.pop(ch, None)
    if not t or t[0] != tipo or time.time() - t[1] > 300:
        raise ValueError("desafio vencido; tente de novo")
    return base64url_to_bytes(ch)


def senha_ok(senha):
    agora = time.time()
    _erros[:] = [q for q in _erros if agora - q < 600]
    if len(_erros) >= 10:
        raise ValueError("muitas tentativas; espere 10 minutos")
    certa = SENHA_ARQ.read_text().strip()
    if hmac.compare_digest((senha or "").encode(), certa.encode()):
        return True
    _erros.append(agora)
    time.sleep(1)
    return False


def tem_chaves():
    return bool(_ler()["chaves"])


def opcoes_cadastro():
    with _trava:
        chaves = _ler()["chaves"]
    op = generate_registration_options(
        rp_id=DOMINIO, rp_name="Estúdio NewsBR360", user_name="alexandre", user_display_name="Alexandre",
        user_id=b"alexandre-estudio-v2",
        exclude_credentials=[PublicKeyCredentialDescriptor(id=base64url_to_bytes(c["id"])) for c in chaves],
        authenticator_selection=AuthenticatorSelectionCriteria(resident_key=ResidentKeyRequirement.REQUIRED,
                                                               user_verification=UserVerificationRequirement.REQUIRED))
    _desafio("cadastro", op.challenge)
    return json.loads(options_to_json(op))


def cadastrar(credencial, nome):
    ch = _tirar_desafio("cadastro", credencial)
    v = verify_registration_response(credential=credencial, expected_challenge=ch, expected_rp_id=DOMINIO,
                                     expected_origin=ORIGEM, require_user_verification=True)
    with _trava:
        d = _ler()
        d["chaves"].append({"id": bytes_to_base64url(v.credential_id), "chave": bytes_to_base64url(v.credential_public_key),
                            "conta": v.sign_count, "nome": (nome or "aparelho")[:60],
                            "quando": time.strftime("%Y-%m-%d %H:%M")})
        _gravar(d)


def opcoes_entrar():
    op = generate_authentication_options(rp_id=DOMINIO, user_verification=UserVerificationRequirement.REQUIRED)
    _desafio("entrar", op.challenge)
    return json.loads(options_to_json(op))


def entrar(credencial):
    ch = _tirar_desafio("entrar", credencial)
    with _trava:
        d = _ler()
        c = next((c for c in d["chaves"] if c["id"] == credencial.get("id")), None)
        if not c:
            raise ValueError("este Face ID não está cadastrado; entre com a senha e cadastre")
        v = verify_authentication_response(credential=credencial, expected_challenge=ch, expected_rp_id=DOMINIO,
                                           expected_origin=ORIGEM, credential_public_key=base64url_to_bytes(c["chave"]),
                                           credential_current_sign_count=c["conta"], require_user_verification=True)
        c["conta"] = v.new_sign_count
        c["usado"] = time.strftime("%Y-%m-%d %H:%M")
        _gravar(d)
