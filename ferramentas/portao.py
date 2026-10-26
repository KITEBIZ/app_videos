"""O portão da legenda do post, igual ao do publicador da VPS (newsbr360/publicar-instagram.py, portao_legenda, lido
em 16/10/2026 de /srv/kitebiz/projetos/newsbr360-estudio; a cópia do Mac era de 12/10, sem a regra do @).
Quando a v2 for para a VPS, usar a função de lá em vez desta cópia."""
import re


def portao_legenda(txt):
    """Regras do CLAUDE.md que valem para texto publicado (as dos Farrapos ficaram de fora)."""
    erros = []
    if "—" in txt:
        erros.append("tem travessao longo (regra: texto publicado usa ponto ou virgula)")
    for proibido in ("claude", "anthropic", "openai", "chatgpt", "lovable"):
        if proibido in txt.lower():
            erros.append(f"cita '{proibido}' (autoria e' da KITEBIZ)")
    if len(txt) > 2200:
        erros.append(f"{len(txt)} caracteres; o Instagram aceita 2200")
    # 16/10/2026 (legenda-sem-criador; ele: "coloca como regra não citar @ que não seja da newsbr360"): no #126 a
    # legenda automática citou o criador do vídeo que só inspirou a pauta
    for arroba in sorted(set(re.findall(r"@[\w.]*\w", txt))):
        if arroba.lower() != "@newsbr360":
            erros.append(f"cita {arroba}: a legenda só cita a @newsbr360")
    tags = re.findall(r"#\w+", txt)
    if len(tags) > 30:
        erros.append(f"{len(tags)} hashtags; o Instagram aceita 30")
    return erros
