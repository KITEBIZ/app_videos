"""Tipo A (sem rede): a regra de baixar (24/10/2026, ele: "autorizo e isso tem que ficar como regra, tentar mais vezes até
conseguir baixar ou avisar que tentou x vezes e não conseguiu"). Com um yt-dlp de mentira: (1) o post que só abre logado
baixa pelo login do Chrome depois que o direto falha; (2) quando nada dá, o aviso diz quantas vezes e por quais caminhos
tentou. Calibrado: sem o caminho "login do Chrome", o caso 1 falha."""
import os, stat, sys, tempfile
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R), str(R / "ferramentas")]
import saida_casa as SC
SC.PAUSA = 0; SC.NA_VPS = False; SC._tem_chrome = lambda: True
SC.no_ar = lambda: None; SC.endereco = lambda: None; SC.anotar = lambda *a, **k: None; SC._linha = lambda *a, **k: None
SC.LINHA = Path("/nao/existe")
d = Path(tempfile.mkdtemp())
falso = d / "yt-dlp"
falso.write_text("#!/bin/sh\ncase \"$*\" in *cookies-from-browser*) [ -n \"$SO_FALHA\" ] && { echo 'ERROR: login required' >&2; exit 1; }; echo ok; exit 0;; "
                 "*) echo 'ERROR: [Instagram] X: Instagram sent an empty media response. Check if this post is accessible in your browser without being logged-in' >&2; exit 1;; esac\n")
falso.chmod(falso.stat().st_mode | stat.S_IEXEC)
falhas = []
r = SC.yt([str(falso), "-o", str(d / "a.m4a"), "https://www.instagram.com/reel/X/"], quem="teste", timeout=20)
if r.returncode != 0:
    falhas.append(f"1: o post que só abre logado não baixou pelo login do Chrome ({(r.stderr or '')[-120:]})")
os.environ["SO_FALHA"] = "1"
r = SC.yt([str(falso), "-o", str(d / "a.m4a"), "https://www.instagram.com/reel/X/"], quem="teste", timeout=20)
msg = (r.stderr or "").splitlines()[-1] if r.stderr else ""
if r.returncode == 0 or "tentei 4 vez(es), por direto, login do Chrome" not in msg or "só abre logado" not in msg:
    falhas.append(f"2: o aviso final não diz as tentativas e os caminhos: {msg[:200]!r}")
print("passou · o post que só abre logado baixa pelo login do Chrome; sem jeito, o aviso conta as tentativas e os caminhos"
      if not falhas else "FALHOU · " + " | ".join(falhas))
sys.exit(1 if falhas else 0)
