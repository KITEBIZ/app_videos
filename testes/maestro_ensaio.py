"""Ensaio do agente-maestro (21/10/2026, "aprovo o plano agente-maestro"): mensagens reais dele, cada uma com a conversa
que havia ANTES dela, e o que o maestro deveria escolher. Não executa nada (só maestro.decidir); custa ~US$ 0,02 cada.

  .venv/bin/python testes/maestro_ensaio.py          roda todas e diz quantas acertou

Esperado: a 1ª ferramenta (ou "duvida") tem que estar no conjunto aceito. O esperado é proposta e ele corrige.
"""
import json, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import estudio as E, maestro as M

CASOS = [  # (vídeo, começo do id, aceitos, por quê)
    (373, "a30637e9", {"mudar_capa", "duvida"}, "o Lula de um lado e o sargento do outro no título: a capa (foi à abertura do vídeo, 25/10)"),
    (306, "85d2ea52", {"ajustar_video"}, "'metadata de baixo' é enquadramento, não baixar (foi ao animador antigo)"),
    (306, "c036dccb", {"ajustar_video"}, "selos, nomes e ELE DISSE na tela"),
    (306, "b93febe8", {"responder"}, "pergunta: quais selos tem"),
    (306, "65550e6f", {"mudar_capa"}, "a capa não condiz com o vídeo"),
    (306, "e696330c", {"mudar_capa"}, "Flávio e Lula frente a frente: é a capa (a conversa é de capa)"),
    (306, "9b7a30d0", {"mudar_capa"}, "foto do Flávio, sem a palavra capa, logo depois da capa (foi ao animador do vídeo)"),
    (306, "318a94a1", {"responder"}, "pergunta: qual capa é melhor (refez as capas)"),
    (306, "746fe6ae", {"responder"}, "achar e baixar o vídeo do Lula"),
    (306, "658ffa42", {"responder"}, "baixa ele"),
    (306, "dd0486e1", {"responder"}, "pergunta: conseguiu baixar e pode usar?"),
    (306, "791612e7", {"mudar_fala"}, "tirar os itens 7 e 8 e mudar o que é dito"),
    (306, "df787f2f", {"duvida", "responder", "mudar_fala"}, "ambíguo: pergunta ou o novo pedido final"),
    (306, "dfb35b97", {"mudar_fala"}, "tira os blocos 8, 9 e 10"),
    (306, "3e10c6f8", {"ajustar_video", "responder"}, "rostos no quadro dos 4 pedidos (tirar as fotos antes vale)"),
    (306, "b8b22216", {"ajustar_video", "mudar_fala"}, "Siga o perfil, abertura e o take inteiro da Rachel (muda a fala: vale mudar_fala antes)"),
    (306, "7d37ecea", {"ajustar_video"}, "enquadramento do Boulos e do Lula"),
    (306, "73a10e1e", {"revisar_video"}, "revisão geral de ponta a ponta (foi a um ajuste)"),
    (306, "fca306a1", {"revisar_video"}, "revise todo o vídeo (foi ao chat)"),
    (306, "25fc874f", {"revisar_video", "ajustar_video"}, "pontos com segundo e 'revisa a edição'"),
    (305, "eb11a828", {"ajustar_video"}, "refaz SÓ o bloco dos ministros: não é do zero"),
    (305, "69857676", {"responder"}, "'não faz nada ainda, espera': nada pode ser feito"),
    (305, "e2762606", {"mudar_capa"}, "o que a capa deve dizer"),
    (305, "d19406f1", {"ajustar_video"}, "pico e o carimbo do fim"),
    (304, "8df0d407", {"mudar_fala"}, "fechamento falado, com 'baixo nível'"),
]


def main():
    certos, linhas = 0, []
    for num, ini, aceitos, porque in CASOS:
        msgs = E.chat(num)
        msg = next((m for m in msgs if str(m.get("id", "")).startswith(ini)), None)
        if not msg:
            linhas.append(f"?  #{num} {ini}: mensagem não achada"); continue
        d = M.decidir(num, msg["texto"], msg_id=msg["id"])
        escolha = "duvida" if d.get("intencao") == "duvida" else (d.get("acoes") or [{}])[0].get("ferramenta", "(nada)")
        todas = " → ".join(a["ferramenta"] for a in d.get("acoes") or []) or d.get("intencao", "?")
        ok = escolha in aceitos
        certos += ok
        linhas.append(f"{'OK ' if ok else 'ERR'} #{num} \"{msg['texto'][:70].strip()}\" → {todas}"
                      + ("" if ok else f"  (esperado: {'/'.join(sorted(aceitos))}; {porque})")
                      + (f"  [pergunta: {d.get('pergunta_para_ele', '')[:80]}]" if escolha == "duvida" else ""))
    print("\n".join(linhas))
    print(f"\n{certos} de {len(CASOS)} certos")
    return 0 if certos == len(CASOS) else 1


if __name__ == "__main__":
    sys.exit(main())
