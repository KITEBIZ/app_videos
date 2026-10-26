#!/usr/bin/env python3
"""O túnel da casa visto da VPS, a cada minuto (22/10/2026, "aprovo o plano pi-diagnostico"; ele: "pode criar um banco de
dados para salvar os dados em tabela para quando sair a gente saber?").

Grava em diagnostico/tunel.db, tabela tunel: se a saída pela casa respondeu de ponta a ponta (saida_casa.no_ar: túnel,
repassador do Pi e internet de casa) e em quanto tempo. Esta é a tabela que não se perde: se o Pi travar inteiro, ele
não grava a dele (pi_saude), mas aqui a queda fica marcada.

  python3 ferramentas/tunel_db.py            uma linha (o cron chama a cada minuto)
  python3 ferramentas/tunel_db.py quedas 7   as quedas dos últimos 7 dias (início, fim, quanto tempo)
"""
import datetime, sqlite3, sys, time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import saida_casa

DB = AQUI.parent / "diagnostico/tunel.db"
GUARDA_DIAS = 60


def gravar():
    DB.parent.mkdir(exist_ok=True)
    t0 = time.time()
    ok = saida_casa.no_ar(espera=6) is not None
    with sqlite3.connect(DB, timeout=20) as c:
        c.execute("create table if not exists tunel (quando text primary key, no_ar int, ms real)")
        c.execute("insert or replace into tunel values (?, ?, ?)",
                  (datetime.datetime.now().isoformat(timespec="seconds"), int(ok), round((time.time() - t0) * 1000, 1)))
        c.execute("delete from tunel where quando < ?", ((datetime.datetime.now() - datetime.timedelta(days=GUARDA_DIAS)).isoformat(),))


def quedas(dias=7):
    """[(início, fim ou None se ainda fora, minutos)]: cada sequência de minutos fora do ar."""
    desde = (datetime.datetime.now() - datetime.timedelta(days=dias)).isoformat()
    with sqlite3.connect(DB) as c:
        linhas = c.execute("select quando, no_ar from tunel where quando >= ? order by quando", (desde,)).fetchall()
    out, ini = [], None
    for q, ok in linhas:
        if not ok and ini is None:
            ini = q
        elif ok and ini is not None:
            out.append((ini, q, round((datetime.datetime.fromisoformat(q) - datetime.datetime.fromisoformat(ini)).total_seconds() / 60)))
            ini = None
    if ini is not None:
        out.append((ini, None, round((datetime.datetime.now() - datetime.datetime.fromisoformat(ini)).total_seconds() / 60)))
    return out


if __name__ == "__main__":
    if sys.argv[1:2] == ["quedas"]:
        qs = quedas(int(sys.argv[2]) if len(sys.argv) > 2 else 7)
        for a, z, m in qs:
            print(f"{a} até {z or 'agora (ainda fora)'} · {m} min")
        print(f"{len(qs)} queda(s)")
    else:
        gravar()
