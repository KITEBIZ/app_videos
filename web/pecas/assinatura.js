/* Assinatura do vídeo (estúdio v2, 16/10/2026, "aprovo o plano v2-assinatura"): o logo do Instituto BR360 se monta
   numa tela limpa no fim do vídeo. Desenho aprovado no estudo (regras/pecas/assinatura/estudo.html):
   as 24 cadeiras aparecem vazias e acendem em leque com pop; um halo cresce; INSTITUTO br360 bate como carimbo
   (ele: "o Instituto br360 tem que entrar como carimbo"); FATO, FONTE E PONTO. palavra por palavra; @newsbr360 com sino.
   O tocador expõe T.assinatura(instante) e estende o vídeo pela duração dela (DURACAO s depois do instante). */
(function () {
  // 24/10/2026 (consertos-do-369; os Olhos no #369: "logo animado sem fala por uns 5 s: eu já teria rolado"): o mesmo
  // desenho em ~2,2 s e meio segundo parado (antes 4,0 s)
  const DURACAO = 2.6;
  const SIMB = [[141,287,'#ff4d5e'],[81,287,'#ff4d5e'],[21,287,'#ff4d5e'],[37,195,'#ff4d5e'],[102,196,'#ff4d5e'],[170,199,'#ff4d5e'],
    [84,113,'#9cbcff'],[160,123,'#9cbcff'],[156,53,'#9cbcff'],[245,144,'#9cbcff'],[244,82,'#9cbcff'],[244,21,'#9cbcff'],
    [338,21,'#ffc933'],[338,82,'#ffc933'],[337,144,'#ffc933'],[426,53,'#ffc933'],[422,123,'#ffc933'],[498,113,'#ffc933'],
    [412,199,'#ffc933'],[480,196,'#ffc933'],[545,195,'#ffc933'],[441,287,'#ffc933'],[501,287,'#ffc933'],[561,287,'#ffc933']];
  // o leque: do arco esquerdo ao direito, pelo ângulo em volta do centro de baixo do símbolo
  const ORDEM = SIMB.map((p, i) => [Math.atan2(300 - p[1], p[0] - 291), i]).sort((a, b) => b[0] - a[0]).map(x => x[1]);

  const tr = s => (window.T && window.T.t ? window.T.t(s) : s);   // idioma-do-video: o texto fixo no idioma do vídeo
  function html() {
    const larg = 700, k = larg / 582, x0 = 480 - larg / 2, y0 = 500, r = 21 * k;
    const pos = SIMB.map(([x, y, c], i) => [(x0 + x * k).toFixed(1), (y0 + y * k).toFixed(1), c, ORDEM.indexOf(i)]);
    const vazias = pos.map(([x, y]) => `<circle class="as-vz" cx="${x}" cy="${y}" r="${(r - 2).toFixed(1)}" fill="none" stroke="#9cbcff" stroke-width="3" opacity="0"/>`).join('');
    const brilhos = pos.map(([x, y, c, o]) => `<circle class="as-br" data-o="${o}" cx="${x}" cy="${y}" r="${r.toFixed(1)}" fill="none" stroke="${c}" stroke-width="5" opacity="0"/>`).join('');
    const cheias = pos.map(([x, y, c, o]) => `<circle class="as-ch" data-o="${o}" cx="${x}" cy="${y}" r="${r.toFixed(1)}" fill="${c}" opacity="0"/>`).join('');
    return `<svg width="1080" height="1920" viewBox="0 0 1080 1920" style="position:absolute;inset:0" class="assinatura">
      <defs><radialGradient id="as-halo"><stop offset="0" stop-color="#ffffff" stop-opacity=".22"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient></defs>
      <ellipse class="as-halo" cx="480" cy="700" rx="460" ry="330" fill="url(#as-halo)" opacity="0"/>
      <g class="as-simb">${vazias}${brilhos}${cheias}</g>
      <g class="as-marca" opacity="0">
        <text x="480" y="1000" text-anchor="middle" font-family="Montserrat" font-weight="800" font-size="58" letter-spacing="26" fill="#b8c2e6">INSTITUTO</text>
        <text x="480" y="1190" text-anchor="middle" font-family="Montserrat" font-weight="900" font-size="200"><tspan fill="#009c3b">b</tspan><tspan fill="#ffdf00">r</tspan><tspan fill="#eef1fb">360</tspan></text></g>
      <g class="as-frase"><text x="480" y="1330" text-anchor="middle" font-family="Montserrat" font-weight="900" font-size="58">
        <tspan class="as-w" fill="#F4F6FF" fill-opacity="0">${tr('FATO, ')}</tspan><tspan class="as-w" fill="#F4F6FF" fill-opacity="0">${tr('FONTE ')}</tspan><tspan class="as-w" fill="#ffc933" fill-opacity="0">${tr('E PONTO')}</tspan><tspan class="as-w" fill="#ffc933" fill-opacity="0" font-size="80">.</tspan></text></g>
      <text class="as-arroba" x="480" y="1400" text-anchor="middle" font-family="Montserrat" font-weight="700" font-size="36" fill="#9cbcff" opacity="0">@newsbr360</text>
    </svg>`;
  }

  // a tela fica limpa: a cena de antes some (o animador não precisa apagar nada) e a legenda não aparece por cima
  function por(cena, tl, T, t) {
    const caixa = document.createElement('div');
    caixa.className = 'assinatura-caixa'; caixa.style.cssText = 'position:absolute;inset:0;opacity:0';
    caixa.innerHTML = html(); cena.appendChild(caixa);
    const q = s => caixa.querySelectorAll(s), ord = s => [...q(s)].sort((a, b) => a.dataset.o - b.dataset.o);
    const outros = [...cena.children].filter(e => e !== caixa);
    tl.to(outros, {opacity: 0, duration: .2}, t - .2);
    const leg = document.getElementById('legenda'); if (leg) tl.to(leg, {opacity: 0, duration: .2}, t - .2);
    tl.set(caixa, {opacity: 1}, t);
    tl.to(q('.as-vz'), {attr: {opacity: .35}, duration: .3, stagger: .008}, t);
    const ini = t + .25, passo = .03;
    tl.to(ord('.as-ch'), {attr: {opacity: 1}, duration: .01, stagger: passo}, ini);
    tl.fromTo(ord('.as-ch'), {scale: .3, transformOrigin: '50% 50%'}, {scale: 1, duration: .28, stagger: passo, ease: 'back.out(3.5)'}, ini);
    tl.fromTo(ord('.as-br'), {attr: {opacity: .9}, scale: 1, transformOrigin: '50% 50%'}, {attr: {opacity: 0}, scale: 1.9, duration: .4, stagger: passo}, ini);
    for (const n of [0, 6, 12, 18, 23]) T.som('pop', ini + n * passo);
    const cheio = ini + 23 * passo + .15;
    tl.to(q('.as-halo'), {attr: {opacity: 1}, duration: .5}, cheio - .1);
    tl.to(q('.as-simb'), {scale: 1.035, svgOrigin: '480 700', duration: .25, yoyo: true, repeat: 1, ease: 'sine.inOut'}, cheio - .1);
    // o nome bate como carimbo: 3 vezes maior até o lugar em 0,22 s, aparece logo no começo da descida, treme, e o
    // símbolo de cima sente o baque
    const bate = cheio + .25;
    tl.fromTo(q('.as-marca'), {scale: 3, svgOrigin: '480 1100'}, {scale: 1, svgOrigin: '480 1100', duration: .22, ease: 'power4.in'}, bate - .22);
    tl.fromTo(q('.as-marca'), {attr: {opacity: 0}}, {attr: {opacity: 1}, duration: .07, ease: 'none'}, bate - .22);
    tl.to(q('.as-marca'), {scale: 1.04, svgOrigin: '480 1100', duration: .06, yoyo: true, repeat: 1}, bate);
    tl.fromTo(q('.as-marca'), {x: 0}, {x: 7, duration: .04, yoyo: true, repeat: 3}, bate);
    tl.fromTo(q('.as-simb'), {y: 0}, {y: -6, duration: .05, yoyo: true, repeat: 1}, bate);
    T.som('carimbo', bate);
    const frase = bate + .2;
    tl.fromTo(q('.as-frase'), {y: 24}, {y: 0, duration: .5, ease: 'power2.out'}, frase);
    tl.to(q('.as-w'), {attr: {'fill-opacity': 1}, duration: .15, stagger: .12}, frase);
    T.som('pop', frase + .36);
    tl.to(q('.as-arroba'), {attr: {opacity: 1}, duration: .2}, frase + .5);
    T.som('chime', frase + .5);
    return t + DURACAO;
  }
  window.Assinatura = {por, DURACAO};
})();
