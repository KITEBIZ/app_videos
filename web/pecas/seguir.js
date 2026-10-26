/* Convite para seguir (estúdio v2, 18/10/2026, "aprovo o plano peca-seguir"; refeito no mesmo dia, "aprovo o plano
   celular-e-zona-segura", depois do print do iPhone dele: a caixa ficava colada na borda, a seta não chegava ao nome e
   o brilho em volta do "Seguir" do app ficava solto, porque o app nem sempre mostra o botão: para quem já segue, como
   ele, não mostra).
   Caixa amarela "Siga o perfil · para a próxima checagem", centralizada na área que o celular mostra, entre a legenda
   (y 1290-1400) e o nome de quem publicou (o app começa em y ~1615), com uma seta descendo para a linha do nome. Sem
   nome de perfil: serve nos dois perfis e em colaboração (ele: "tem que ser generico").
   O tocador expõe T.seguir(instante): uma vez entre 12 e 15 s e uma no placar ou no fecho (regras/ANIMADOR.md). */
(function () {
  const DURACAO = 2.6;
  // 22/10/2026 (editor-327; os Olhos no #327: o convite "sobrepõe a fala"; a caixa ficava a 15 px da legenda): mais
  // baixa e mais fina, a 40 px da legenda (y 1290-1400) e com a seta ainda chegando à linha do nome
  const CAIXA = {x: 130, y: 1440, larg: 700, alt: 100};      // x 130-830: centro 480 (o centro útil, longe dos ícones)
  const SETA_X = 200;                                          // em cima do começo da linha do nome (depois do avatar)

  const tr = s => (window.T && window.T.t ? window.T.t(s) : s);   // idioma-do-video: o texto fixo no idioma do vídeo
  function html() {
    const c = CAIXA;
    return `<svg width="1080" height="1920" viewBox="0 0 1080 1920" style="position:absolute;inset:0;pointer-events:none" class="seguir">
      <g class="sg-caixa" opacity="0">
        <rect x="${c.x}" y="${c.y}" width="${c.larg}" height="${c.alt}" rx="18" fill="#ffc933"/>
        <text x="${c.x + c.larg / 2}" y="${c.y + 46}" text-anchor="middle" font-family="Montserrat" font-weight="900" font-size="40" fill="#0a1748">${tr('Siga o perfil')}</text>
        <text x="${c.x + c.larg / 2}" y="${c.y + 84}" text-anchor="middle" font-family="Montserrat" font-weight="800" font-size="28" fill="#0a1748">${tr('para a próxima checagem')}</text>
      </g>
      <g class="sg-seta" opacity="0"><path d="M${SETA_X - 14} 1540 h28 v26 h20 l-34 34 l-34 -34 h20 z" fill="#ffc933" stroke="#0a1748" stroke-width="3"/></g>
    </svg>`;
  }

  function por(cena, tl, T, t) {
    const caixa = document.createElement('div');
    caixa.className = 'seguir-caixa'; caixa.style.cssText = 'position:absolute;inset:0;pointer-events:none';
    caixa.innerHTML = html(); cena.appendChild(caixa);
    const q = s => caixa.querySelector(s);
    tl.fromTo(q('.sg-caixa'), {attr: {opacity: 0}, y: 30}, {attr: {opacity: 1}, y: 0, duration: .3, ease: 'back.out(2)'}, t);
    tl.to(q('.sg-seta'), {attr: {opacity: 1}, duration: .2}, t + .2);
    tl.fromTo(q('.sg-seta'), {y: 0}, {y: 8, duration: .3, yoyo: true, repeat: 5, ease: 'sine.inOut'}, t + .2);   // até y ~1608, antes do nome
    T.som('pop', t + .1);
    tl.to([q('.sg-caixa'), q('.sg-seta')], {attr: {opacity: 0}, duration: .25}, t + DURACAO - .25);
    return t + DURACAO;
  }
  window.Seguir = {por, DURACAO, CAIXA};
})();
