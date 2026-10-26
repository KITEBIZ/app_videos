#!/usr/bin/env python3
"""Narra os roteiros com o Gemini 3.8 Flash TTS (voz Kore, escolhida pelo Alexandre em 25/09/2026) e alinha o áudio ao
texto pelo Whisper da Groq (antes ElevenLabs), que dá o instante de cada caractere. Gera narracao/<slug>.mp3 e
narracao/<slug>.json no mesmo formato que montar.py lê. Rodar: python3 src/narrar.py [slug]"""
import json, os, sys, base64, urllib.request, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GK = os.environ["GEMINI_API_KEY"]   # 13/10/2026: a chave da ElevenLabs saiu (o alinhamento é pela Groq)
VOZ = "Kore"; MODELO = "gemini-3.8-flash-tts"
ESTILO = "narração institucional corporativa em português do Brasil, calma, confiante e clara, ritmo moderado"
ROTEIROS = {
    "squads-hibridas": [
        "Squads híbridas e agênticas.",
        "Pessoas e inteligência artificial no mesmo time.",
        "Na Deliver IT, profissionais especializados trabalham com agentes de IA que apoiam análise, documentação, código, testes e automação.",
        "Menos tempo em tarefas operacionais.",
        "Mais energia em estratégia, criatividade e inovação.",
        "E o critério de onde usar a IA continua sendo humano: são as pessoas que decidem, validam e respondem pelo resultado.",
        "Tecnologia acelera. Pessoas validam.",
        "Leia o artigo completo em deliverit ponto com ponto b r."],
    # Conteúdo (26/09/2026): artigo "Tecnologia acelera, pessoas validam" (14/09), frase a frase fiel ao texto.
    "quatro-camadas": [
        "Como aplicar inteligência artificial na engenharia de software?",
        "No palco do TechNow Serra, a Deliver IT apresentou o seu modelo de modernização e evolução assistida por IA.",
        "São quatro camadas.",
        "Primeiro, a decodificação do sistema.",
        "Depois, a estruturação do conhecimento.",
        "Em seguida, a inteligência para decisão.",
        "E, por fim, a execução assistida por IA.",
        "Cada camada gera um resultado próprio e alimenta a seguinte.",
        "Em todas as etapas, a inteligência artificial trabalha com curadoria técnica humana.",
        "A tecnologia acelera. Mas é a experiência dos especialistas que sustenta a qualidade, a rastreabilidade e a confiança no resultado.",
        "Leia o artigo completo em deliverit ponto com ponto b r."],
    "12-anos": [
        "Vinte e oito de julho.",
        "A Deliver IT completa doze anos.",
        "Os desafios evoluíram, as tecnologias se transformaram, a empresa cresceu e novas pessoas chegaram.",
        "Uma coisa continua a mesma desde o primeiro dia:",
        "a vontade de construir, aprender, evoluir e entregar valor.",
        "Obrigado a cada Deliver, cliente e parceiro que escreveu essa história com a gente.",
        "Seguimos construindo os próximos capítulos."],
}


def gemini_tts(texto):
    body = {"model": MODELO, "input": [{"type": "user_input", "content": [{"type": "text", "text": texto, "annotations": [{"type": "speech_metadata", "style": ESTILO}]}]}],
            "response_format": {"type": "audio"}, "generation_config": {"speech_config": [{"voice": VOZ}]}}
    req = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/interactions", data=json.dumps(body).encode(), headers={"x-goog-api-key": GK, "Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=300))
    for s in d.get("steps", []):
        for c in s.get("content", []):
            if c.get("data"):
                return base64.b64decode(c["data"])
    raise SystemExit("Gemini não devolveu áudio: " + json.dumps(d)[:500])


def alinhar(mp3, texto):
    """O instante de cada caractere do texto, no formato que a ElevenLabs devolvia ({"characters": [{text, start, end}]}).
    13/10/2026 ("aprovo o plano alinhamento-groq"): a ElevenLabs passou a recusar (assinatura com fatura pendente) e era
    usada só para isto. Agora o Whisper da Groq dá o tempo de cada palavra ouvida; as palavras do texto são casadas com as
    ouvidas na ordem ("doze" ouvido como "12" vale; "dois mil e vinte e seis" ouvido como "2026" divide o tempo pelo
    tamanho das palavras), e a palavra que não casou fica entre as vizinhas. `loss` = fração de palavras sem par exato."""
    import difflib, re, unicodedata
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from transcrever import palavras
    from conferir_voz import extenso
    norm = lambda w: re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", w.lower()).encode("ascii", "ignore").decode())

    def por_extenso(w):
        """O Whisper escreve número ("2010", "12,6", "33%"); o texto fala ("dois mil e dez"). Calibração no #102: sem isto
        o casamento pegava o "e" errado e uma palavra ficou 1,5 s fora do lugar."""
        w = re.sub(r"(\d)\.(\d{3})\b", r"\1\2", w)
        w = re.sub(r"(\d+),(\d+)", lambda m: f"{m.group(1)} vírgula {m.group(2)}", w).replace("%", " por cento")
        return re.sub(r"\d+", lambda m: f" {extenso(int(m.group()))} " if int(m.group()) < 1_000_000 else m.group(), w).split()

    ouvidas = []                                     # cada palavra ouvida, já por extenso, com o seu pedaço do tempo
    for a, b, w in palavras(mp3)[0]:
        partes = por_extenso(w) or [w]
        tam = [max(1, len(x)) for x in partes]; acc = a
        for x, n in zip(partes, tam):
            fim = acc + (b - a) * n / sum(tam); ouvidas.append((acc, fim, x)); acc = fim
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp3)]))
    alvo = texto.split(" ")
    t = [None] * len(alvo)
    exatas = 0

    def reparte(i1, i2, ini, fim):
        """Divide [ini, fim] entre as palavras i1..i2-1 do texto, pelo número de letras."""
        tam = [max(1, len(alvo[k])) for k in range(i1, i2)]; soma, acc = sum(tam), ini
        for k, n in zip(range(i1, i2), tam):
            fim_k = acc + (fim - ini) * n / soma; t[k] = [acc, fim_k]; acc = fim_k

    m = difflib.SequenceMatcher(None, [norm(w) for w in alvo], [norm(w[2]) for w in ouvidas], autojunk=False)
    for tag, i1, i2, j1, j2 in m.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                t[i1 + k] = list(ouvidas[j1 + k][:2]); exatas += 1
        elif tag == "replace":
            reparte(i1, i2, ouvidas[j1][0], ouvidas[j2 - 1][1])
    # o que não casou (texto que o Whisper não ouviu): entre o fim da anterior e o começo da seguinte
    k = 0
    while k < len(alvo):
        if t[k] is not None:
            k += 1; continue
        j = k
        while j < len(alvo) and t[j] is None:
            j += 1
        reparte(k, j, t[k - 1][1] if k else 0.0, t[j][0] if j < len(alvo) else dur)
        k = j
    for k in range(1, len(t)):                      # nunca para trás
        t[k][0] = max(t[k][0], t[k - 1][0]); t[k][1] = max(t[k][1], t[k][0])
    chars = []
    for k, w in enumerate(alvo):
        if k:
            chars.append({"text": " ", "start": round(t[k - 1][1], 3), "end": round(t[k][0], 3)})
        chars += [{"text": c, "start": round(t[k][0], 3), "end": round(t[k][1], 3)} for c in w]
    return {"characters": chars, "loss": round(1 - exatas / max(1, len(alvo)), 3), "fonte": "groq whisper-large-v3"}


def narrar(slug):
    frases = ROTEIROS[slug]; texto = " ".join(frases)
    wav = ROOT / "narracao" / f"{slug}.wav"; mp3 = ROOT / "narracao" / f"{slug}.mp3"
    wav.write_bytes(gemini_tts(texto))
    # nível igual ao das narrações anteriores (média perto de -19 dB) e 44,1 kHz mono
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-af", "loudnorm=I=-18:TP=-2:LRA=9", "-ar", "44100", "-ac", "1", "-c:a", "libmp3lame", "-b:a", "128k", str(mp3)], check=True)
    al = alinhar(mp3, texto)
    chars = [c["text"] for c in al["characters"]]; st = [c["start"] for c in al["characters"]]; en = [c["end"] for c in al["characters"]]
    assert "".join(chars) == texto, "alinhamento devolveu texto diferente"
    print(f"  alinhamento: perda média {al['loss']:.2f} (quanto menor, mais seguro; > 1 pede conferência)")
    tempos, pos = [], 0
    for f in frases:
        i = texto.index(f, pos); j = i + len(f) - 1
        tempos.append({"frase": f, "inicio": round(st[i], 3), "fim": round(en[j], 3)}); pos = j + 1
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp3)]).decode().strip())
    json.dump({"voz": f"{VOZ} (Gemini 3.8 Flash TTS)", "voice_id": VOZ, "texto": texto, "chars": len(texto), "duracao": round(min(dur, en[-1] + 0.05), 3),
               "frases": tempos, "alinhamento": {"characters": chars, "character_start_times_seconds": st, "character_end_times_seconds": en}},
              open(ROOT / "narracao" / f"{slug}.json", "w"), ensure_ascii=False, indent=1)
    print(f"{slug}: {VOZ} · {len(texto)} chars · áudio {dur:.2f} s · última letra em {en[-1]:.2f} s")
    for t in tempos:
        print(f"  {t['inicio']:6.2f} - {t['fim']:6.2f}  {t['frase'][:70]}")


if __name__ == "__main__":
    for s in (sys.argv[1:] or ROTEIROS):
        narrar(s)
