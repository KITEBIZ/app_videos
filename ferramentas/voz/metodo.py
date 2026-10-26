#!/usr/bin/env python3
"""Vídeo vertical de venda do Método VTA da KITEBIZ (1080x1920), para teste interno (Alexandre, 26/09/2026).

Roteiro no estilo aprovado (feedback_estilo_roteiro_video): pergunta, problema (Gap de Rigidez), estrutura item a item
(V, T, A), ligação (IA e curadoria humana), prova (caso Moto Morini, números do site), tese (escopo fechado; a vela do
kitesurf, nas palavras do Alexandre: "a kitebiz impulsiona o negocio dos clientes. usamos a metafora do kitesurf") e
convite. Tudo o mais é texto do site kitebiz.com.br lido em 26/09/2026.

Cenas: gráfico do Gap de Rigidez (mercado em vermelho, operação em azul, o gap entre eles; o que nasce nele; a IA em
processo torto acelerando o erro) que volta no fim com a linha dourada fechando o gap; linha do tempo de 12 semanas com
V, T e A e as entregas de cada fase; IA e pessoas; os números do caso. Fecho: o logo animado (src/logo.py) na junção.

  python3 src/metodo.py narrar     # voz Kore + alinhamento (reaproveita o narrar.py do modelo da Deliver IT)
  python3 src/metodo.py montar     # metodo/index.html + capa/index.html + carve da música
"""
import json, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent                       # KITEBIZ/video
MODELO = Path("/caminho/local/Projetos/deliverit-site/video/noticias")    # modelo de vídeo (narração, funções de texto, carve)
# 08/10/2026: nesta cópia o voz_alexandre só usa ROTEIRO e SLUG; sem o sys.path do modelo, o `import narrar` do
# voz_alexandre acha o alinhamento em ferramentas/voz (e não no deliverit-site)
SLUG = "metodo-vta"

ROTEIRO = [
    "A sua operação acompanha a velocidade que o mercado exige?",
    "O mercado acelerou. A operação ficou para trás.",
    "Essa distância tem nome: Gap de Rigidez.",
    "É nela que nascem o retrabalho, o custo escondido e a perda de margem.",
    "E colocar inteligência artificial em processo torto só acelera o erro.",
    "Por isso a KITEBIZ criou o Método VTA, um ciclo de doze semanas.",
    "Visualizar: em duas semanas, uma tomografia mostra onde o processo trava e onde a margem vaza.",
    "Transformar: em sete semanas, automações e agentes entram em produção, sem trocar o seu ERP.",
    "Acelerar: em três semanas, painel, indicadores e governança para decidir com dados.",
    "A inteligência artificial encontra os padrões. A curadoria humana valida e decide.",
    "Na Moto Morini, foram dois mil duzentos e quarenta e quatro leads atendidos em cinco meses, com resposta média de cinco segundos.",
    "Escopo fechado no início. Resultado medido no final.",
    "Como a vela no kitesurf, a KITEBIZ transforma a força do mercado em impulso para o seu negócio.",
    "Agende o seu pré-diagnóstico em kitebiz ponto com ponto b r.",
]
TELA = [  # texto na tela; <b> em dourado; mesma contagem de palavras da fala quando possível (palavras acendem no tempo)
    "A sua operação acompanha a <b>velocidade</b> que o mercado exige?",
    "O mercado acelerou. A operação <b>ficou para trás</b>.",
    "Essa distância tem nome: <b>Gap de Rigidez</b>.",
    "É nela que nascem o retrabalho, o custo escondido e a <b>perda de margem</b>.",
    "E colocar inteligência artificial em processo torto só <b>acelera o erro</b>.",
    "Por isso a KITEBIZ criou o <b>Método VTA</b>, um ciclo de doze semanas.",
    "<b>Visualizar:</b> em duas semanas, uma tomografia mostra onde o processo trava e onde a margem vaza.",
    "<b>Transformar:</b> em sete semanas, automações e agentes entram em produção, sem trocar o seu ERP.",
    "<b>Acelerar:</b> em três semanas, painel, indicadores e governança para decidir com dados.",
    "A inteligência artificial encontra os padrões. A <b>curadoria humana</b> valida e decide.",
    "Caso real: <b>Moto Morini</b>.",
    "<b>Escopo fechado</b> no início. <b>Resultado medido</b> no final.",
    "Como a vela no kitesurf, a KITEBIZ transforma a força do mercado em <b>impulso</b> para o seu negócio.",
    "Agende o seu <b>pré-diagnóstico</b> em kitebiz.com.br",
]
BAIXO = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12}                   # frases com cena em cima: texto no pé
COR = {"fundo": "#0a0a0a", "vermelho": "#dc2626", "azul": "#3b82f6", "ouro": "#f5a623", "vela": "#E9B566", "branco": "#F2F2F2"}
MUSICA_VOL, FADE_IN, FADE_OUT, CARVE_FORCA = 0.5, 1.2, 1.8, 0.4
FIM = 1.2                                                           # respiro depois da última frase (o logo entra na junção)


def narrar():
    import narrar as n
    n.ROOT = ROOT
    n.ROTEIROS = {SLUG: ROTEIRO}
    (ROOT / "narracao").mkdir(exist_ok=True)
    n.narrar(SLUG)


# ---------------------------------------------------------------- cenas
def cena_gap(t, fim):
    """Gráfico do Gap de Rigidez. Frases 1-4; volta nas frases 11-12 com a linha dourada fechando o gap."""
    MERC = "M0,470 C300,440 520,260 860,40"
    OPER = "M0,500 C300,480 560,440 860,400"
    GAP = "M0,470 C300,440 520,260 860,40 L860,400 C560,440 300,480 0,500 Z"
    OURO = "M0,500 C300,480 470,320 860,62"
    JAG = "M430,452 L470,408 L510,470 L550,396 L590,466 L630,400 L670,456 L710,392 L750,450 L790,386 L830,442 L860,384"
    def lay(id_, d, cor, w, extra=""):
        return (f'<svg class="gp-l" id="{id_}" viewBox="0 0 860 560"><path d="{d}" fill="none" stroke="{cor}" stroke-width="{w}" '
                f'stroke-linecap="round" stroke-linejoin="round" {extra}/></svg>')
    html = f'''
          <div id="gp" data-layout-allow-overflow>
            <div id="gp-eixo"></div><div id="gp-tempo">tempo</div>
            <svg class="gp-l" id="gp-area" viewBox="0 0 860 560"><path d="{GAP}" fill="rgba(220,38,38,.22)"/></svg>
            {lay("gp-oper", OPER, COR["azul"], 10)}
            {lay("gp-merc", MERC, COR["vermelho"], 10)}
            {lay("gp-ouro", OURO, COR["ouro"], 12)}
            {lay("gp-jag", JAG, "#ff5a5a", 7)}
            <div class="gp-rot" id="gp-rmerc" style="color:{COR["vermelho"]};left:640px;top:330px">Mercado exige</div>
            <div class="gp-rot" id="gp-roper" style="color:{COR["azul"]};left:600px;top:872px">Operação entrega</div>
            <div class="gp-rot" id="gp-rouro" style="color:{COR["ouro"]};left:560px;top:380px">Capacidade após VTA</div>
            <div id="gp-nome">GAP DE<br>RIGIDEZ</div>
            <div class="gp-chip" id="gpc0" style="left:600px;top:740px">retrabalho</div>
            <div class="gp-chip" id="gpc1" style="left:650px;top:668px">custo escondido</div>
            <div class="gp-chip" id="gpc2" style="left:690px;top:596px">perda de margem</div>
            <div id="gp-ia">IA</div>
          </div>'''
    css = f'''
      #gp {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1080px; opacity: 0; }}
      .gp-l {{ position: absolute; left: 110px; top: 360px; width: 860px; height: 560px; overflow: visible; clip-path: inset(0 100% 0 0); }}
      #gp-area {{ clip-path: none; opacity: 0; }}
      #gp-eixo {{ position: absolute; left: 110px; top: 920px; width: 860px; height: 3px; background: rgba(242,242,242,.25); }}
      #gp-tempo {{ position: absolute; left: 870px; top: 932px; font-weight: 600; font-size: 26px; color: rgba(242,242,242,.5); }}
      .gp-rot {{ position: absolute; font-weight: 800; font-size: 34px; opacity: 0; }}
      #gp-nome {{ position: absolute; left: 150px; top: 520px; font-weight: 900; font-size: 64px; line-height: 1; color: #fff; opacity: 0; letter-spacing: .01em; }}
      .gp-chip {{ position: absolute; font-weight: 700; font-size: 28px; color: #fff; background: rgba(220,38,38,.85); border-radius: 14px; padding: 8px 18px; opacity: 0; }}
      #gp-ia {{ position: absolute; left: 520px; top: 760px; font-weight: 900; font-size: 34px; color: #0a0a0a; background: {COR["ouro"]}; border-radius: 16px; padding: 6px 18px; opacity: 0; }}
'''
    a = []
    t1, t2, t3, t4, t5 = t[1], t[2], t[3], t[4], t[5]
    a.append(f'tl.fromTo("#gp", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.3 }}, {t1 - 0.2:.2f});')
    a.append(f'tl.fromTo("#gp-merc", {{ clipPath: "inset(0 100% 0 0)" }}, {{ clipPath: "inset(0 0% 0 0)", duration: 1.2, ease: "power2.in" }}, {t1:.2f});')
    a.append(f'tl.fromTo("#gp-rmerc", {{ opacity: 0, y: 20 }}, {{ opacity: 1, y: 0, duration: 0.4 }}, {t1 + 1.0:.2f});')
    a.append(f'tl.fromTo("#gp-oper", {{ clipPath: "inset(0 100% 0 0)" }}, {{ clipPath: "inset(0 0% 0 0)", duration: 1.4, ease: "power1.inOut" }}, {t1 + 1.3:.2f});')
    a.append(f'tl.fromTo("#gp-roper", {{ opacity: 0, y: 20 }}, {{ opacity: 1, y: 0, duration: 0.4 }}, {t1 + 2.4:.2f});')
    a.append(f'tl.fromTo("#gp-area", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.6 }}, {t2:.2f});')
    a.append(f'tl.fromTo("#gp-nome", {{ opacity: 0, scale: 0.7 }}, {{ opacity: 1, scale: 1, duration: 0.5, ease: "back.out(1.8)" }}, {t2 + 0.9:.2f});')
    for k in range(3):
        a.append(f'tl.fromTo("#gpc{k}", {{ opacity: 0, scale: 0.4 }}, {{ opacity: 1, scale: 1, duration: 0.35, ease: "back.out(2.4)" }}, {t3 + 0.9 + k * 0.7:.2f});')
    a.append(f'tl.fromTo("#gp-ia", {{ opacity: 0, y: -160 }}, {{ opacity: 1, y: 0, duration: 0.45, ease: "bounce.out" }}, {t4 + 0.6:.2f});')
    a.append(f'tl.fromTo("#gp-jag", {{ clipPath: "inset(0 100% 0 0)" }}, {{ clipPath: "inset(0 0% 0 0)", duration: 0.9, ease: "power3.in" }}, {t4 + 1.4:.2f});')
    a.append(f'tl.fromTo("#gp", {{ x: 0 }}, {{ keyframes: [{{ x: -10, duration: 0.05 }}, {{ x: 10, duration: 0.05 }}, {{ x: -6, duration: 0.05 }}, {{ x: 0, duration: 0.05 }}], immediateRender: false }}, {t4 + 2.2:.2f});')
    a.append(f'tl.to("#gp", {{ opacity: 0, duration: 0.35 }}, {t5 - 0.3:.2f});')
    # volta: sem chips, sem erro; a linha dourada fecha o gap
    t11, t12 = t[11], t[12]
    a.append(f'tl.set(["#gpc0","#gpc1","#gpc2","#gp-ia","#gp-jag","#gp-nome"], {{ opacity: 0 }}, {t11 - 0.4:.2f});')
    a.append(f'tl.to("#gp", {{ opacity: 1, duration: 0.35 }}, {t11 - 0.2:.2f});')
    a.append(f'tl.fromTo("#gp-ouro", {{ clipPath: "inset(0 100% 0 0)" }}, {{ clipPath: "inset(0 0% 0 0)", duration: 2.2, ease: "power2.inOut", immediateRender: false }}, {t11 + 0.4:.2f});')
    a.append(f'tl.to("#gp-area", {{ opacity: 0.25, duration: 1.6 }}, {t11 + 1.2:.2f});')
    a.append(f'tl.fromTo("#gp-rouro", {{ opacity: 0, y: 20 }}, {{ opacity: 1, y: 0, duration: 0.4 }}, {t11 + 2.2:.2f});')
    a.append(f'tl.to("#gp", {{ opacity: 0, duration: 0.35 }}, {t[13] - 0.3:.2f});')
    return html, css, a


def cena_vta(t):
    FASES = [("V", "Visualizar", "Semanas 1 e 2", ["Diagnóstico com evidências e baseline", "Mapa dos fluxos e pontos de atrito", "Backlog priorizado do ciclo"], COR["azul"], (0, 2)),
             ("T", "Transformar", "Semanas 3 a 9", ["Processos redesenhados", "Automações e agentes em produção", "Playbooks para o time"], COR["branco"], (2, 9)),
             ("A", "Acelerar", "Semanas 10 a 12", ["Cockpit com KPIs em tempo real", "Trilha de auditoria", "Supervisão por exceção"], COR["ouro"], (9, 12))]
    cels = "".join(f'<div class="vt-c" id="vtc{i}"><span>{i + 1}</span></div>' for i in range(12))
    cks = "".join(f'<div class="vt-ck" id="vtk{j}" style="left:{111 + (s - 1) * 72 + 22}px">◆</div>' for j, s in enumerate([4, 8, 12]))
    cards = "".join(
        f'<div class="vt-card" id="vtf{k}" style="--c:{c}"><div class="vt-L">{L}</div><div class="vt-tx"><div class="vt-n">{n}</div>'
        f'<div class="vt-s">{s}</div>' + "".join(f'<div class="vt-b">{b}</div>' for b in bs) + '</div></div>'
        for k, (L, n, s, bs, c, _) in enumerate(FASES))
    pessoa = ('<svg viewBox="0 0 24 24" width="70" height="70"><circle cx="12" cy="7.5" r="4.2" fill="#0a0a0a"/>'
              '<path d="M3.5 21c0-4.4 3.8-7.5 8.5-7.5s8.5 3.1 8.5 7.5z" fill="#0a0a0a"/></svg>')
    html = f'''
          <div id="vt" data-layout-allow-overflow>
            <div id="vt-tit">12 SEMANAS</div>
            <div id="vt-cels">{cels}</div>{cks}
            <div id="vt-ckl">checkpoints</div>
            {cards}
            <div id="vt-duo"><div class="vt-d" id="vtd0"><div class="vt-i">IA</div><div><b>Inteligência artificial</b><br>encontra os padrões</div></div>
              <div class="vt-d" id="vtd1"><div class="vt-i p">{pessoa}</div><div><b>Curadoria humana</b><br>valida e decide</div></div></div>
          </div>'''
    css = f'''
      #vt {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1080px; opacity: 0; }}
      #vt-tit {{ position: absolute; left: 111px; top: 300px; font-weight: 900; font-size: 44px; letter-spacing: .12em; color: {COR["vela"]}; }}
      #vt-cels {{ position: absolute; left: 111px; top: 390px; display: flex; gap: 6px; }}
      .vt-c {{ width: 66px; height: 96px; border-radius: 12px; background: rgba(242,242,242,.08); border: 2px solid rgba(242,242,242,.18);
        display: flex; align-items: flex-end; justify-content: center; padding-bottom: 8px; font-weight: 700; font-size: 22px; color: rgba(242,242,242,.6); opacity: 0; }}
      .vt-ck {{ position: absolute; top: 350px; font-size: 30px; color: {COR["ouro"]}; opacity: 0; }}
      #vt-ckl {{ position: absolute; left: 111px; top: 500px; font-weight: 600; font-size: 24px; color: rgba(245,166,35,.8); opacity: 0; }}
      .vt-card {{ position: absolute; left: 111px; top: 580px; width: 858px; display: flex; gap: 36px; align-items: flex-start; opacity: 0; }}
      .vt-L {{ font-weight: 900; font-size: 260px; line-height: .8; color: var(--c); }}
      .vt-n {{ font-weight: 900; font-size: 60px; color: #fff; }}
      .vt-s {{ font-weight: 700; font-size: 30px; color: var(--c); margin: 6px 0 18px; }}
      .vt-b {{ font-weight: 600; font-size: 32px; color: rgba(242,242,242,.88); margin-bottom: 12px; padding-left: 26px; position: relative; }}
      .vt-b::before {{ content: ""; position: absolute; left: 0; top: 14px; width: 12px; height: 12px; border-radius: 50%; background: var(--c); }}
      #vt-duo {{ position: absolute; left: 111px; top: 600px; width: 858px; display: flex; flex-direction: column; gap: 40px; }}
      .vt-d {{ display: flex; align-items: center; gap: 30px; font-weight: 500; font-size: 40px; line-height: 1.25; color: rgba(242,242,242,.9); opacity: 0; }}
      .vt-d b {{ font-weight: 900; color: #fff; }}
      .vt-i {{ width: 130px; height: 130px; flex: 0 0 130px; border-radius: 50%; background: {COR["ouro"]}; display: flex; align-items: center; justify-content: center;
        font-weight: 900; font-size: 52px; color: #0a0a0a; }}
      .vt-i.p {{ background: {COR["azul"]}; }}
'''
    a = []
    t5 = t[5]
    a.append(f'tl.fromTo("#vt", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.3 }}, {t5 - 0.1:.2f});')
    a.append(f'tl.fromTo("#vt-tit", {{ opacity: 0, x: -40 }}, {{ opacity: 1, x: 0, duration: 0.4 }}, {t5 + 1.2:.2f});')
    for i in range(12):
        a.append(f'tl.fromTo("#vtc{i}", {{ opacity: 0, y: 30 }}, {{ opacity: 1, y: 0, duration: 0.3, ease: "back.out(2)" }}, {t5 + 1.4 + i * 0.12:.2f});')
    for j in range(3):
        a.append(f'tl.fromTo("#vtk{j}", {{ opacity: 0, scale: 0.3 }}, {{ opacity: 1, scale: 1, duration: 0.3, ease: "back.out(3)" }}, {t5 + 3.0 + j * 0.2:.2f});')
    a.append(f'tl.fromTo("#vt-ckl", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4 }}, {t5 + 3.1:.2f});')
    for k, (L, n, s, bs, c, (c0, c1)) in enumerate(FASES):
        tk = t[6 + k] - 0.1
        a.append(f'tl.to([{",".join(f"{chr(34)}#vtc{i}{chr(34)}" for i in range(c0, c1))}], {{ backgroundColor: "{c}", borderColor: "{c}", color: "#0a0a0a", duration: 0.25, stagger: 0.08 }}, {tk:.2f});')
        a.append(f'tl.fromTo("#vtf{k}", {{ opacity: 0, x: 60 }}, {{ opacity: 1, x: 0, duration: 0.45, ease: "power3.out" }}, {tk + 0.1:.2f});')
        a.append(f'tl.fromTo("#vtf{k} .vt-b", {{ opacity: 0, x: 30 }}, {{ opacity: 1, x: 0, duration: 0.35, stagger: 0.35, immediateRender: false }}, {tk + 0.9:.2f});')
        a.append(f'tl.to("#vtf{k}", {{ opacity: 0, x: -60, duration: 0.3, ease: "power2.in" }}, {t[7 + k] - 0.35:.2f});')
    a.append(f'tl.fromTo("#vtd0", {{ opacity: 0, x: -50 }}, {{ opacity: 1, x: 0, duration: 0.45, ease: "power3.out" }}, {t[9] + 0.1:.2f});')
    a.append(f'tl.fromTo("#vtd1", {{ opacity: 0, x: -50 }}, {{ opacity: 1, x: 0, duration: 0.45, ease: "power3.out" }}, {t[9] + 2.3:.2f});')
    a.append(f'tl.to("#vt", {{ opacity: 0, duration: 0.35 }}, {t[10] - 0.3:.2f});')
    return html, css, a


def cena_caso(t):
    NUMS = [("2.244", 2244, "leads atendidos"), ("5", None, "meses de operação"), ("5 s", None, "de resposta média")]
    blocos = "".join(f'<div class="cs-b" id="csb{k}"><div class="cs-n" id="csn{k}">{txt}</div><div class="cs-l">{lab}</div></div>' for k, (txt, _, lab) in enumerate(NUMS))
    html = f'<div id="cs" data-layout-allow-overflow><div id="cs-tit">NÚMEROS DO CASO</div>{blocos}</div>'
    css = f'''
      #cs {{ position: absolute; left: 111px; top: 300px; width: 858px; opacity: 0; }}
      #cs-tit {{ font-weight: 900; font-size: 36px; letter-spacing: .12em; color: {COR["vela"]}; margin-bottom: 30px; }}
      .cs-b {{ display: flex; align-items: baseline; gap: 26px; margin-bottom: 26px; opacity: 0; }}
      .cs-n {{ font-weight: 900; font-size: 150px; line-height: 1; color: {COR["ouro"]}; font-variant-numeric: tabular-nums; }}
      .cs-l {{ font-weight: 700; font-size: 40px; color: #fff; }}
'''
    t10 = t[10]
    a = [f'tl.fromTo("#cs", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.3 }}, {t10 - 0.1:.2f});']
    for k in range(3):
        a.append(f'tl.fromTo("#csb{k}", {{ opacity: 0, y: 40 }}, {{ opacity: 1, y: 0, duration: 0.45, ease: "back.out(1.6)" }}, {t10 + 1.6 + k * 1.3:.2f});')
    a.append(f'const cont = {{ v: 0 }}; tl.fromTo(cont, {{ v: 0 }}, {{ v: 2244, duration: 1.2, ease: "power2.out", onUpdate: () => {{ document.getElementById("csn0").textContent = Math.round(cont.v).toLocaleString("pt-BR"); }} }}, {t10 + 1.6:.2f});')
    a.append(f'tl.to("#cs", {{ opacity: 0, duration: 0.35 }}, {t[11] - 0.3:.2f});')
    return html, css, a


# ---------------------------------------------------------------- composição
def montar():
    import montar as base                     # funções de texto do modelo (palavras no tempo, tamanho de fonte)
    nar = json.load(open(ROOT / "narracao" / f"{SLUG}.json"))
    al = nar["alinhamento"]; st = al["character_start_times_seconds"]; texto = nar["texto"]; frases = nar["frases"]
    t = [f["inicio"] for f in frases]
    T_NAR = nar["duracao"]; DUR = round(T_NAR + FIM, 2)
    out = ROOT / "metodo"
    (out / "assets" / "sfx").mkdir(parents=True, exist_ok=True); (out / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    for f in (ROOT / "logo" / "assets" / "sfx").iterdir():
        shutil.copy(f, out / "assets" / "sfx" / f.name)
    shutil.copy(ROOT / "logo" / "assets" / "fonts" / "montserrat-latin.woff2", out / "assets" / "fonts" / "montserrat-latin.woff2")
    shutil.copy(ROOT / "narracao" / f"{SLUG}.mp3", out / "assets" / "narracao.mp3")
    for f in ("package.json", "hyperframes.json"):
        shutil.copy(ROOT / "logo" / f, out / f)
    frases_html, js, sfx, pos = [], [], [], 0
    for k, (fr, tela) in enumerate(zip(frases, TELA)):
        i0 = texto.index(fr["frase"], pos); pos = i0 + len(fr["frase"])
        ini, fim = fr["inicio"], fr["fim"]
        prox = frases[k + 1]["inicio"] if k + 1 < len(frases) else DUR
        t_in = max(0.0, ini - 0.18)
        t_out = max(fim - 0.05, min(fim + 0.3, prox - 0.43)) if k + 1 < len(frases) else DUR - 0.2
        pal = base.palavras_com_tempo(fr["frase"], tela, i0, st, None)
        corpo = " ".join(f'<span class="w" data-t="{tt:.3f}" data-layout-allow-overlap>{w}</span>' for w, tt in pal) if pal else tela
        corpo = corpo.replace("<b>", "<b data-layout-allow-overlap>")
        fs = base.tamanho_fonte(tela) if k not in BAIXO else min(base.tamanho_fonte(tela), 72)
        lay = "baixo" if k in BAIXO else "centro"
        frases_html.append(f'<div class="frase {lay}" id="f{k}" data-layout-allow-overlap><div class="txt" style="font-size:{fs}px" data-layout-allow-overlap>{corpo}</div><div class="linha"></div></div>')
        js.append(f'fraseIn("#f{k}", {t_in:.2f}, {-1 if k % 2 == 0 else 1}); fraseOut("#f{k}", {t_out:.2f});')
        sfx.append(("click-soft", t_in, 0.37, 0.16))
    g_html, g_css, g_js = cena_gap(t, [f["fim"] for f in frases])
    v_html, v_css, v_js = cena_vta(t)
    c_html, c_css, c_js = cena_caso(t)
    sfx += [("whoosh-short", t[1] - 0.2, 0.57, 0.22), ("impact-bass-1", t[2] + 0.9, 2.1, 0.22), ("pop", t[3] + 0.9, 0.72, 0.2), ("pop", t[3] + 1.6, 0.72, 0.2),
            ("pop", t[3] + 2.3, 0.72, 0.2), ("impact-bass-2", t[4] + 2.2, 2.6, 0.25), ("whoosh-short", t[5] - 0.1, 0.57, 0.22), ("typing", t[5] + 1.4, 1.5, 0.12),
            ("ping", t[6] - 0.1, 1.32, 0.16), ("ping", t[7] - 0.1, 1.32, 0.16), ("ping", t[8] - 0.1, 1.32, 0.16), ("chime", t[9] + 2.3, 2.5, 0.16),
            ("sparkle", t[10] + 1.6, 1.8, 0.2), ("whoosh-cinematic", t[11] + 0.3, 5.5, 0.18)]
    audio = [f'<audio id="narracao" src="assets/narracao.mp3" data-start="0" data-duration="{T_NAR:.2f}" data-volume="1" data-track-index="1" data-audio-group="voiceover"></audio>']
    for i, (n, tt, d, v) in enumerate(sfx):
        audio.append(f'<audio id="sfx-{i:02d}-{n}" src="assets/sfx/{n}.mp3" data-start="{tt:.2f}" data-duration="{d}" data-volume="{v}" data-track-index="{i + 2}" data-audio-group="sfx"></audio>')
    musica = ROOT / "musica" / f"{SLUG}.wav"
    if musica.exists():
        shutil.copy(musica, out / "assets" / "musica.wav")
        lane = base.lane_volume([(0, 0), (FADE_IN, MUSICA_VOL), (DUR - FADE_OUT, MUSICA_VOL), (DUR, 0)])
        audio.append(f'<audio id="music-bed" src="assets/musica.wav" data-start="0" data-duration="{DUR}" data-volume="1" data-track-index="{len(sfx) + 2}" data-audio-group="music" data-automation="{lane}"></audio>')
    html = f'''<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <title>KITEBIZ · Método VTA</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      @font-face {{ font-family: "Montserrat"; src: url("assets/fonts/montserrat-latin.woff2") format("woff2"); font-weight: 400 900; font-display: block; }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: 1080px; height: 1920px; overflow: hidden; background: {COR["fundo"]}; }}
      #root {{ position: relative; width: 100%; height: 100%; overflow: hidden; font-family: "Montserrat", sans-serif; color: #fff; }}
      #cena {{ position: absolute; inset: 0; }}
      #camera {{ position: absolute; inset: 0; transform-origin: 50% 50%; }}
      .glow {{ position: absolute; border-radius: 50%; filter: blur(60px); opacity: .5; }}
      #eyebrow {{ position: absolute; left: 90px; top: 150px; font-weight: 800; font-size: 28px; letter-spacing: .16em; color: {COR["vela"]}; }}
      #eyebrow i {{ display: inline-block; width: 14px; height: 14px; border-radius: 50%; background: {COR["ouro"]}; margin-right: 14px; vertical-align: 2px; }}
      .frase {{ position: absolute; left: 90px; right: 90px; opacity: 0; }}
      .frase.centro {{ top: 50%; transform: translateY(-50%); }}
      .frase.baixo {{ top: 1150px; }}
      .frase .txt {{ font-weight: 800; letter-spacing: -0.02em; line-height: 1.1; color: #fff; }}
      .frase .txt b {{ color: {COR["ouro"]}; font-weight: 900; }}
      .frase .w {{ opacity: .35; display: inline-block; }}
      .frase .linha {{ width: 220px; height: 10px; border-radius: 5px; margin-top: 28px; transform-origin: left center; background: linear-gradient(90deg, {COR["vela"]}, {COR["ouro"]}); }}
{g_css}{v_css}{c_css}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{DUR}" data-width="1080" data-height="1920">
      <section id="cena" class="clip" data-start="0" data-duration="{DUR}" data-track-index="0">
        <div id="camera">
          <div class="glow" id="gl1" style="left:-120px;top:120px;width:560px;height:560px;background:rgba(245,166,35,.35)"></div>
          <div class="glow" id="gl2" style="left:660px;top:760px;width:520px;height:520px;background:rgba(59,130,246,.3)"></div>
          <div class="glow" id="gl3" style="left:120px;top:1450px;width:600px;height:500px;background:rgba(220,38,38,.18)"></div>
          <div id="eyebrow"><i></i>KITEBIZ · MÉTODO VTA™</div>
          {g_html}{v_html}{c_html}
          {"".join(frases_html)}
        </div>
      </section>
      {chr(10).join("      " + x for x in audio)}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      tl.fromTo("#camera", {{ scale: 1.0 }}, {{ scale: 1.04, duration: {DUR}, ease: "sine.inOut" }}, 0);
      ["#gl1", "#gl2", "#gl3"].forEach((g, i) => tl.to(g, {{ x: i % 2 ? -80 : 80, y: i % 2 ? 60 : -60, duration: {DUR}, ease: "sine.inOut" }}, 0));
      function fraseIn(sel, t, lado) {{
        tl.fromTo(sel, {{ opacity: 0, x: 140 * lado }}, {{ opacity: 1, x: 0, duration: 0.45, ease: "power4.out" }}, t);
        tl.fromTo(sel + " .linha", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.4, ease: "power3.out" }}, t + 0.2);
        document.querySelectorAll(sel + " .w").forEach(w => tl.to(w, {{ opacity: 1, duration: 0.18, ease: "power2.out" }}, parseFloat(w.dataset.t)));
      }}
      function fraseOut(sel, t) {{ tl.to(sel, {{ opacity: 0, y: -50, duration: 0.25, ease: "power3.in" }}, t); }}
{chr(10).join("      " + x for x in js)}
{chr(10).join("      " + x for x in g_js + v_js + c_js)}
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
'''
    (out / "index.html").write_text(html, encoding="utf-8")
    print(f"metodo/index.html · narração {T_NAR} s · total {DUR} s · {len(sfx)} efeitos · música {'sim' if musica.exists() else 'não'}")
    if musica.exists():
        r = subprocess.run(["node", str(Path.home() / ".claude/skills/hyperframes-audio/scripts/carve.mjs"), "--comp", "index.html", "--bed", "music-bed",
                            "--voice", "narracao", "--strength", str(CARVE_FORCA), "--core", str(MODELO / ".ferramentas")], cwd=out, capture_output=True, text=True)
        print("  carve:", "ok" if r.returncode == 0 else r.stderr[-300:])
    capa()


def capa():
    out = ROOT / "capa"; (out / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "logo" / "assets" / "fonts" / "montserrat-latin.woff2", out / "assets" / "fonts" / "montserrat-latin.woff2")
    shutil.copy(Path("/caminho/local/Projetos/KITEBIZ/logo-kitebiz.svg"), out / "assets" / "logo-kitebiz.svg")
    for f in ("package.json", "hyperframes.json"):
        shutil.copy(ROOT / "logo" / f, out / f)
    html = f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="UTF-8" /><meta name="viewport" content="width=1080, height=1920" /><title>KITEBIZ · capa Método VTA</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
  @font-face {{ font-family: "Montserrat"; src: url("assets/fonts/montserrat-latin.woff2") format("woff2"); font-weight: 400 900; font-display: block; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{ width: 1080px; height: 1920px; overflow: hidden; background: {COR["fundo"]}; }}
  #root {{ position: relative; width: 100%; height: 100%; overflow: hidden; font-family: "Montserrat", sans-serif; color: #fff; }}
  #cena {{ position: absolute; inset: 0; }}
  .glow {{ position: absolute; border-radius: 50%; filter: blur(60px); opacity: .55; }}
  #logo {{ position: absolute; left: 90px; top: 320px; width: 420px; }}
  #gap {{ position: absolute; left: 90px; top: 560px; width: 900px; height: 420px; }}
  #tit {{ position: absolute; left: 90px; right: 90px; top: 1040px; font-weight: 900; font-size: 104px; line-height: 1.02; letter-spacing: -0.02em; text-wrap: balance; }}
  #tit b {{ color: {COR["ouro"]}; }}
  #lin {{ position: absolute; left: 90px; top: 1400px; width: 240px; height: 12px; border-radius: 6px; background: linear-gradient(90deg, {COR["vela"]}, {COR["ouro"]}); }}
  #apoio {{ position: absolute; left: 90px; right: 90px; top: 1445px; font-weight: 600; font-size: 40px; line-height: 1.3; color: rgba(242,242,242,.85); }}
</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="2.5" data-width="1080" data-height="1920">
  <section id="cena" class="clip" data-start="0" data-duration="2.5" data-track-index="0">
    <div class="glow" id="g1" style="left:-120px;top:200px;width:560px;height:560px;background:rgba(245,166,35,.35)"></div>
    <div class="glow" id="g2" style="left:640px;top:700px;width:520px;height:520px;background:rgba(59,130,246,.3)"></div>
    <img id="logo" src="assets/logo-kitebiz.svg" alt="KITEBIZ">
    <svg id="gap" viewBox="0 0 860 400"><path d="M0,330 C300,300 520,140 860,20 L860,290 C560,320 300,350 0,360 Z" fill="rgba(220,38,38,.25)"/>
      <path d="M0,330 C300,300 520,140 860,20" fill="none" stroke="{COR["vermelho"]}" stroke-width="10" stroke-linecap="round"/>
      <path d="M0,360 C300,350 560,320 860,290" fill="none" stroke="{COR["azul"]}" stroke-width="10" stroke-linecap="round"/>
      <path d="M0,360 C300,345 470,210 860,42" fill="none" stroke="{COR["ouro"]}" stroke-width="12" stroke-linecap="round"/></svg>
    <div id="tit">Feche o <b>Gap de Rigidez</b> em 12 semanas</div>
    <div id="lin"></div>
    <div id="apoio">O Método VTA da KITEBIZ: Visualizar, Transformar, Acelerar.</div>
  </section>
</div>
<script>
  window.__timelines = window.__timelines || {{}};
  const tl = gsap.timeline({{ paused: true }});
  tl.to("#g1", {{ x: 40, y: -30, duration: 2.5, ease: "sine.inOut" }}, 0);
  tl.to("#g2", {{ x: -40, y: 30, duration: 2.5, ease: "sine.inOut" }}, 0);
  tl.fromTo("#lin", {{ scaleX: 1 }}, {{ scaleX: 1.25, transformOrigin: "left center", duration: 2.5, ease: "sine.inOut" }}, 0);
  window.__timelines["main"] = tl; tl.seek(0);
</script></body></html>
'''
    (out / "index.html").write_text(html, encoding="utf-8")
    print("capa/index.html")


if __name__ == "__main__":
    {"narrar": narrar, "montar": montar, "capa": capa}[sys.argv[1]]()
