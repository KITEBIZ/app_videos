/* Carimbos com rótulo (estúdio v2, 19/10/2026; ele, sobre o bloco 9 do #300: "nesse ponto tem dois carimbos, porque?").
   Um ou mais selos do Verdadômetro (T.selo) lado a lado, cada um com o rótulo do que foi checado embaixo, numa pílula
   escura (o desenho do #300: MINISTROS · CASA DO CAMILO). Os selos ficam montados ~3 s e saem juntos.
   A regra que faltava no #300 (o cartão da PF entrou por cima dos dois SEM PROVA e parecia que eles julgavam a PF):
   enquanto os selos estão na tela, T.fotos e T.documento esperam eles saírem (T.esperaSelos, no tocador; vale para
   qualquer T.selo com `sai`). Para chamar o selo ANTES deles em montar (na ordem dos blocos, como já se faz).
   Raro (ele, 19/10: "em geral analisamos uma fala de cada vez"): o normal é um T.selo por tela.

   T.carimbos(lista, o) → instante em que os selos saem
     lista: [{palavra, rotulo, t}]: palavra do Verdadômetro ('SEM PROVA', 'VERDADE'...), o que foi checado ('MINISTROS')
       e o instante (no começo da fala de cada um; o segundo pode vir depois do primeiro)
     o.cy: o centro dos selos (padrão 905) · o.sai: quando saem (padrão: o último t + 3,05) · o.larg: tamanho
   1 selo: no meio, 420 de largura · 2: x 275 e 700, 380 · 3: x 200, 480 e 760, 290 (zona segura: até x ~900). */
(function () {
  const NS = 'http://www.w3.org/2000/svg';
  const POS = {1: [[480], 420], 2: [[275, 700], 380], 3: [[200, 480, 760], 290]};
  const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');

  function quandoFonte(f) {
    f();
    if (!document.fonts) return;
    document.fonts.ready.then(f);
    document.fonts.addEventListener && document.fonts.addEventListener('loadingdone', f);
  }

  function por(cena, tl, T, lista, o = {}) {
    const n = lista.length, P = POS[n];
    if (!P) throw new Error('T.carimbos: de 1 a 3 selos (para mais, divida o bloco)');
    const [xs, larg0] = P, larg = o.larg || larg0, cy = o.cy ?? 905, alt = larg * 580 / 680;
    const ultimo = Math.max(...lista.map(x => +x.t)), sai = o.sai ?? ultimo + 3.05;
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('width', 1080); svg.setAttribute('height', 1920); svg.setAttribute('viewBox', '0 0 1080 1920');
    svg.style.cssText = 'position:absolute;inset:0'; svg.setAttribute('class', 'peca-carimbos');
    lista.forEach((c, i) => {
      T.selo(c.palavra, +c.t, {cx: xs[i], cy, larg, sai});
      if (!c.rotulo) return;
      const g = document.createElementNS(NS, 'g'), y = cy + alt / 2 + 11;
      g.setAttribute('opacity', 0);
      g.innerHTML = `<rect x="${xs[i] - 115}" y="${y}" width="230" height="44" rx="22" fill="#0a1748" stroke="#ff4d5e" stroke-width="2"/>`
        + `<text x="${xs[i]}" y="${y + 30}" text-anchor="middle" font-size="24" font-weight="900" fill="#F4F6FF">${esc(c.rotulo)}</text>`;
      svg.appendChild(g);
      // a pílula na largura do texto, medida depois que a letra carrega (e de novo se ela trocar)
      quandoFonte(() => {
        const w = g.querySelector('text').getComputedTextLength(), r = g.querySelector('rect');
        if (w > 0) { r.setAttribute('width', (w + 60).toFixed(1)); r.setAttribute('x', (xs[i] - (w + 60) / 2).toFixed(1)); }
      });
      tl.to(g, {opacity: 1, duration: .25}, +c.t + .3);           // cada rótulo junto com o seu selo
      tl.to(g, {opacity: 0, duration: .25}, sai);
    });
    cena.appendChild(svg);
    // a trava: o que pedir para entrar entre o primeiro selo e a saída deles espera
    // a janela de cada selo já fica no T.selo (tocador: T.esperaSelos); o que esperar entra no instante em que eles
    // começam a sumir: os dois se cruzam e a tela nunca fica vazia (no estudo, esperar o fim do sumiço deixou 0,5 s vazia)
    return sai + .25;
  }
  window.Carimbos = {por};
})();
