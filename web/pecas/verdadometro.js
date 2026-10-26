/* Verdadômetro (estúdio v2, 16/10/2026, "aprovo o plano v2-verdadometro"): o selo do veredito na linha do logo do
   Instituto BR360. O símbolo do Instituto (24 bolinhas, instituto/site/marca/favicon.svg) vira medidor; a faixa com a
   palavra atravessa o círculo (como a imagem de carimbo que ele mandou); embaixo, INSTITUTO br360 nas cores do logo.
   Desenho aprovado: regras/pecas/verdadometro/ (PNGs e a página do estudo).

   Checagem: VERDADE, MEIA-VERDADE, EXAGERO, ERRADO, FALSO, SEM PROVA (as bolinhas acendem até o nível, o ponteiro para ali).
   Análise: CONFIRMADO, PREVISÃO, OPINIÃO (todas as bolinhas na cor, sem ponteiro); ANÁLISE na conclusão (faixa amarela,
   o símbolo do Instituto nas cores dele).
   O tocador expõe T.selo(palavra, instante, {cx, cy, larg, sai}); este arquivo só desenha e anima. */
(function () {
  const SIMB = [[141,287,'#ff4d5e'],[81,287,'#ff4d5e'],[21,287,'#ff4d5e'],[37,195,'#ff4d5e'],[102,196,'#ff4d5e'],[170,199,'#ff4d5e'],
    [84,113,'#9cbcff'],[160,123,'#9cbcff'],[156,53,'#9cbcff'],[245,144,'#9cbcff'],[244,82,'#9cbcff'],[244,21,'#9cbcff'],
    [338,21,'#ffc933'],[338,82,'#ffc933'],[337,144,'#ffc933'],[426,53,'#ffc933'],[422,123,'#ffc933'],[498,113,'#ffc933'],
    [412,199,'#ffc933'],[480,196,'#ffc933'],[545,195,'#ffc933'],[441,287,'#ffc933'],[501,287,'#ffc933'],[561,287,'#ffc933']];
  const ORDEM = SIMB.map((p, i) => [p[0], i]).sort((a, b) => a[0] - b[0]).map(x => x[1]);      // da esquerda para a direita
  // palavra -> [cor, nível (0 a 24 bolinhas acesas; null = Análise, todas na cor e sem ponteiro)]
  const VEREDITOS = {
    'VERDADE': ['#3ddc84', 24], 'MEIA-VERDADE': ['#ff9f43', 13], 'EXAGERO': ['#ff9f43', 13], 'ERRADO': ['#ff4d5e', 4],
    'FALSO': ['#ff4d5e', 4], 'SEM PROVA': ['#8a94b8', 0],
    'CONFIRMADO': ['#3ddc84', null], 'PREVISÃO': ['#b9a6ff', null], 'OPINIÃO': ['#b9a6ff', null],
    // a conclusão da Análise (16/10, ele: "esse carimbo está antigo"): faixa amarela e o símbolo nas cores do Instituto
    'ANÁLISE': ['#ffc933', 'marca'],
    // o selo da CAPA (17/10, ele: "precisa mudar o selo verdade ou falso. mudamos os selos"): sem ponteiro e sem veredito,
    // o símbolo nas cores do Instituto e o formato do vídeo
    'CHECAGEM': ['#ffc933', 'marca'],
  };
  const APAGADA = '#2a3d86', ESCURO = '#0a1748', BRANCO = '#F4F6FF';
  const escala = i => { const pos = ORDEM.indexOf(i); return pos < 8 ? '#ff4d5e' : pos < 16 ? '#ff9f43' : '#3ddc84'; };
  let conta = 0;

  const tr = s => (window.T && window.T.t ? window.T.t(s) : s);   // idioma-do-video: o texto fixo no idioma do vídeo
  function svg(escrita) {
    // a chave em português dá a cor e o nível; o texto sai no idioma do vídeo ("SIN PRUEBAS" e "SEM PROVA" valem igual)
    const palavra = window.T && window.T.chave ? window.T.chave(escrita) : escrita, rotulo = tr(palavra);
    const v = VEREDITOS[palavra];
    if (!v) throw new Error(`veredito desconhecido: ${palavra} (use ${Object.keys(VEREDITOS).join(', ')})`);
    const [cor, nivelOuMarca] = v, marca = nivelOuMarca === 'marca', nivel = marca ? null : nivelOuMarca;
    const analise = nivel === null, id = 'vm' + (++conta);
    const k = 400 / 582, corDe = i => marca ? SIMB[i][2] : analise ? cor : ORDEM.indexOf(i) < nivel ? escala(i) : APAGADA;
    const bolinhas = SIMB.map(([x, y], i) => `<circle class="vmb" data-ordem="${ORDEM.indexOf(i)}" data-acesa="${analise || ORDEM.indexOf(i) < nivel ? 1 : 0}" `
      + `cx="${(100 + x * k).toFixed(1)}" cy="${(150 - 154 * k + y * k).toFixed(1)}" r="${(21 * k).toFixed(1)}" fill="${corDe(i)}"/>`).join('');
    const ang = nivel === null ? 0 : nivel === 0 ? 0 : -90 + 180 * (nivel - .5) / 24;      // 0 = em pé
    const ponteiro = analise ? '' : `<g class="vmp" transform="rotate(${ang.toFixed(1)} 300 270)"><polygon points="292,270 308,270 300,120" fill="${BRANCO}"/><circle cx="300" cy="270" r="16" fill="${BRANCO}"/></g>`;
    const tam = Math.min(88, 500 / (rotulo.length * .76));
    return {id, ang, analise, html: `<svg id="${id}" viewBox="-40 -20 680 580" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block;overflow:visible">
      <g class="vmd"><circle cx="300" cy="270" r="282" fill="${ESCURO}" fill-opacity=".94" stroke="${cor}" stroke-width="10"/>
        <circle cx="300" cy="270" r="264" fill="none" stroke="${cor}" stroke-width="2.5" opacity=".7"/></g>
      <g transform="translate(300 250) scale(.80) translate(-300 -275)">${bolinhas}${ponteiro}
        <text class="vmn" x="300" y="524" text-anchor="middle" font-family="Montserrat" font-weight="900"><tspan font-size="29" letter-spacing="6" fill="#b8c2e6">INSTITUTO </tspan><tspan font-size="56" fill="#009c3b">b</tspan><tspan font-size="56" fill="#ffdf00">r</tspan><tspan font-size="56" fill="#eef1fb">360</tspan></text></g>
      <g class="vmf"><rect x="-22" y="294" width="644" height="108" rx="14" fill="${cor}"/>
        <rect x="-10" y="305" width="620" height="86" rx="8" fill="none" stroke="${ESCURO}" stroke-width="3" opacity=".5"/>
        <text x="300" y="${(348 + tam * .36).toFixed(1)}" text-anchor="middle" font-family="Montserrat" font-weight="900" font-size="${tam.toFixed(1)}" letter-spacing="4" fill="${ESCURO}">${rotulo}</text></g>
    </svg>`};
  }

  // põe o selo na cena e anima a partir de t: disco entra (.25 s), bolinhas acesas uma a uma (.6 s), ponteiro gira,
  // faixa bate (fim em t + 1,15) e treme; sons: 3 pops (um por cor) e o carimbo quando a faixa bate
  function por(cena, tl, T, palavra, t, o = {}) {
    const larg = o.larg || 760, cx = o.cx ?? 480, cy = o.cy ?? 900;
    const s = svg(palavra), alt = larg * 580 / 680;
    const caixa = document.createElement('div');
    caixa.className = 'verdadometro'; caixa.style.cssText = `position:absolute;left:${cx - larg / 2}px;top:${cy - alt / 2}px;width:${larg}px;opacity:0`;
    caixa.innerHTML = s.html; cena.appendChild(caixa);
    const q = sel => caixa.querySelectorAll(sel);
    const acesas = [...q('.vmb[data-acesa="1"]')].sort((a, b) => a.dataset.ordem - b.dataset.ordem);
    tl.to(caixa, {opacity: 1, duration: .2}, t);
    tl.from(q('.vmd'), {scale: .6, svgOrigin: '300 270', duration: .3, ease: 'back.out(2)'}, t);
    tl.from(acesas, {attr: {fill: APAGADA}, scale: .2, transformOrigin: '50% 50%', duration: .14, stagger: .6 / Math.max(1, acesas.length), ease: 'back.out(3)'}, t + .2);
    if (acesas.length) for (const k of [0, Math.floor(acesas.length / 2), acesas.length - 1].filter((v, i, a) => a.indexOf(v) === i))
      T.som('pop', t + .2 + k * .6 / acesas.length);
    // o ponteiro gira animando o próprio atributo transform, com o eixo no pino (16/10: girar pelo GSAP com svgOrigin
    // tirava o ponteiro do eixo, porque o miolo está escalado; e um onUpdate não roda quando o tocador pula com seek)
    if (!s.analise) tl.fromTo(q('.vmp'), {attr: {transform: 'rotate(-90 300 270)'}},
      {attr: {transform: `rotate(${s.ang.toFixed(1)} 300 270)`}, duration: .5, ease: 'back.out(1.6)'}, t + .35);
    tl.from(q('.vmf'), {scale: 1.5, opacity: 0,   // era 2.6: passava da borda da tela (19/10, #302, 72 s)
      svgOrigin: '300 348', duration: .2, ease: 'power4.in'}, t + .95);
    T.som('carimbo', t + 1.15);
    tl.fromTo(caixa, {x: 0}, {x: 6, duration: .04, yoyo: true, repeat: 3}, t + 1.15);
    if (o.sai != null) tl.to(caixa, {opacity: 0, duration: .25}, o.sai);
    return caixa;
  }
  window.Verdadometro = {svg, por, VEREDITOS};
})();
