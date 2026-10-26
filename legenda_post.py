"""A legenda do post (estúdio v2, 16/10/2026, "aprovo o plano v2-aprovar-video").

  python3 legenda_post.py <número>                 escreve a legenda
  python3 legenda_post.py <número> "pedido dele"   muda a legenda pelo pedido

O agente (claude, regras/LEGENDA.md) lê o roteiro, a checagem, a intenção e o formato e escreve publicacao/legenda.txt.
O portão do publicador (ferramentas/portao.py) confere; o que reprovar volta ao agente uma vez com o motivo, e o que
continuar reprovado fica na tela com o motivo (o botão de aprovar o vídeo não aparece).
"""
import json, subprocess, sys
from pathlib import Path

import estudio as E

sys.path.insert(0, str(E.RAIZ / "ferramentas"))
from portao import portao_legenda


def arquivo(num):
    return E.pasta(num) / "publicacao/legenda.txt"


def ler(num):
    a = arquivo(num)
    if not a.exists():
        return None
    t = a.read_text().strip()
    return {"texto": t, "erros": portao_legenda(t), "caracteres": len(t)}


def _pedir(entrada, p):
    import ia                                 # 25/10/2026: a chamada de IA de um lugar só (ia.py)
    texto, _ = ia.chamar(entrada, "legenda do post", "opus", num=int(p.name), limite=600, cwd=p)
    return texto


def fazer(num, pedido=None):
    p = E.pasta(num); f = E.ler_ficha(num)
    ler_ = lambda n, lim=8000: (p / n).read_text()[:lim] if (p / n).exists() else "(não existe)"
    atual = ler(num)
    formato = {"checagem": "Checagem", "analise": "Análise"}.get(f.get("formato"), "não marcado")
    entrada = f"""{(E.RAIZ / 'regras/LEGENDA.md').read_text()}{E.molde(num)}{E.regra_idioma(num)}{E.memoria(num)}

## Este vídeo (#{int(num)}): {f.get('titulo', '')}
Formato: {formato}. Tipo da pauta: {E.TIPOS.get(f.get('tipo'), f.get('tipo'))}.

INTENCAO.md:
{ler_('INTENCAO.md', 3000)}

ROTEIRO.md:
{ler_('ROTEIRO.md')}

CHECAGEM.md:
{ler_('CHECAGEM.md')}

{('A legenda de agora:' + chr(10) + atual['texto'] + chr(10) + chr(10) + 'O que ele pediu: ' + pedido + chr(10) + 'Mude só o que ele pediu.') if (pedido and atual) else 'Escreva a legenda deste vídeo.'}
"""
    texto = _pedir(entrada, p)
    erros = portao_legenda(texto) if texto else ["a legenda veio vazia"]
    if texto and erros:          # uma volta com o motivo
        texto2 = _pedir(entrada + "\n\nA legenda abaixo foi REPROVADA pelo portão do publicador: " + "; ".join(erros)
                        + "\nReescreva corrigindo só isso.\n\n" + texto, p)
        if texto2:
            texto, erros = texto2, portao_legenda(texto2)
    if texto:
        arquivo(num).parent.mkdir(exist_ok=True)
        if arquivo(num).exists():
            (p / "publicacao/versoes").mkdir(exist_ok=True)
            arquivo(num).rename(p / f"publicacao/versoes/legenda-{E.agora().replace(':', '')[:17]}.txt")
        E._grava(arquivo(num), texto + "\n")
    E.evento(num, f"legenda do post: {len(texto)} caracteres" + (f", reprovada: {'; '.join(erros)}" if erros else ", passou no portão"))
    if not texto:
        return "A legenda não saiu. Peça de novo, por favor."
    return (f"Legenda do post pronta ({len(texto)} caracteres), passou no portão do publicador." if not erros
            else f"Escrevi a legenda, mas o portão ainda reprova: {'; '.join(erros)}. Peça a mudança no chat.")


if __name__ == "__main__":
    print(fazer(int(sys.argv[1]), " ".join(sys.argv[2:]) or None))
