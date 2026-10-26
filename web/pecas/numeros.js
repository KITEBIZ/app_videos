/* Molde números (estúdio v2, 24/10/2026, "pode fazer o molde números"; ele: "podemos usar nossas animacoes e tudo mais
   sobre as fotos de fundo. e quando tiver video usamos videos. acho que é um bom formato mesmo para os mini doc").
   Referência: os reels DePqpN0gX9G e DeRgAHbAJ9e (referencias/): uma foto por assunto, escura e tingida, parada com
   aproximação lenta; o número grande no meio com o rótulo pequeno; barra de comparação; régua de capítulos embaixo;
   "Comente RESUMO" no fim. É molde de ENCAIXE: as casas são fixas e só o conteúdo muda (a colagem pedia ~100 peças com
   posição à mão e o animador pensava 600 s sem escrever). Nas nossas cores e fontes, não nas deles.

   Casas (y na tela 1080x1920; a legenda fica em y 1340, os ícones do app em x > 900 entre y 765 e 1645):
     topo 250-420 título/chamada · centro 520-1080 número, barras · 1150-1215 régua · 1290-1390 legenda

   T.numeros.fundo(o)    {ini, fim, src: 'material/.../foto.jpg' | take: {src, corte, foco}, foco: '50% 30%', tom: 'azul'|'vermelho'|'cinza', zoom: 1.08,
                          credito: 'Autor (CC BY 2.0)'}
                         foto ou trecho de vídeo em tela cheia, preto e branco tingido, escurecido embaixo; aproxima devagar.
                         Fica EMBAIXO de tudo (nossas peças, selos e plenário vão por cima)
   T.numeros.numero(o)   {valor: '6,19', antes: 'R$', unidade: 'bi', rotulo: 'PERDA COM CORRUPÇÃO', fonte: 'Balanço 2014',
                          ini, fim, y: 820, tam: 250, cor, conta: true}: o número grande; conta do zero até o valor em 0,6 s
   T.numeros.titulo(o)   {texto: 'Lei das <b>Estatais</b>', ini, fim, y: 330, tam: 76, sobre: 'APROVADA EM 2016'}: a chamada,
                         com a palavra-chave em tarja amarela; '\n' quebra a linha
   T.numeros.barra(o)    {partes: [['FLÁVIO', 56], ['NENHUM', 17, 'cinza'], ['LULA', 27, 'azul']], ini, fim, y: 1000, titulo}:
                         a barra de comparação, uma parte depois da outra
   T.numeros.barras(o)   {itens: [['2024', 36.6, 'R$ 36,6 bi'], ['2025', 110, 'R$ 110 bi']], ini, fim, y: 700, passo, titulo, fonte}: barras
                         deitadas proporcionais (cada uma entra em ini + k*passo; passo pode ser lista de instantes)
   T.numeros.regua(o)    {capitulos: [['ORIGEM', 0], ['PRÉ-SAL', 18.2], ...], fim}: a régua de capítulos, o ponto anda
   T.numeros.alerta(o)   {texto: 'ANÁLISE', ini, fim, y, cor: 'vermelho'|'amarelo'|'azul'}: a etiqueta pequena
   T.numeros.troca(t)    a passagem de assunto: uma faixa de luz atravessa a tela (com whoosh)
   T.numeros.comenta(o)  {palavra: 'FUNDADOR', ini, fim, sobre: 'COMENTE'}: o convite da palavra-chave
   Cada uma devolve o elemento e some em `fim` (sem fim: até o fim do vídeo). */
(function () {
  const NS = 'http://www.w3.org/2000/svg';
  const COR = {marinho: '#0a1748', fundo: '#050a23', amarelo: '#ffc933', vermelho: '#ff4d5e', azul: '#9cbcff', branco: '#f4f6ff',
               cinza: '#6b7390', tinta: '#0a1748'};
  const TOM = {azul: '#2c4fb8', vermelho: '#b8323f', cinza: '#3a4060', amarelo: '#b88a1c'};
  const IMPACT = `style="font-family:Impact,sans-serif"`, MONT = 'font-family="Montserrat"';
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  const cor = c => COR[c] || c || COR.branco;
  let svgRaiz = null, fundos = null, conta = 0;

  function palco(cena) {             // um <svg> para as peças do molde, acima da cena desenhada
    if (svgRaiz && svgRaiz.isConnected) return svgRaiz;
    svgRaiz = document.createElementNS(NS, 'svg');
    svgRaiz.setAttribute('width', 1080); svgRaiz.setAttribute('height', 1920); svgRaiz.setAttribute('viewBox', '0 0 1080 1920');
    svgRaiz.setAttribute('class', 'peca-numeros'); svgRaiz.style.cssText = 'position:absolute;inset:0;pointer-events:none';
    svgRaiz.innerHTML = `<defs><linearGradient id="num-luz" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#9cbcff" stop-opacity="0"/><stop offset=".5" stop-color="#dfe8ff" stop-opacity=".55"/>
      <stop offset="1" stop-color="#9cbcff" stop-opacity="0"/></linearGradient></defs>`;
    cena.appendChild(svgRaiz);
    return svgRaiz;
  }
  function camadaFundo(cena) {       // os fundos ficam embaixo de tudo o que a cena desenha
    if (fundos && fundos.isConnected) return fundos;
    fundos = document.createElement('div');
    fundos.className = 'peca-numeros-fundo'; fundos.style.cssText = 'position:absolute;inset:0;overflow:hidden;background:#050a23';
    cena.insertBefore(fundos, cena.firstChild);
    return fundos;
  }
  function grupo(cena, html, cls) {
    const g = document.createElementNS(NS, 'g');
    g.setAttribute('class', 'num-' + cls + ' num' + (++conta)); g.setAttribute('opacity', 0);
    g.innerHTML = html; palco(cena).appendChild(g);
    return g;
  }
  const entra = (tl, g, ini, dy = 24) => { tl.fromTo(g, {opacity: 0, y: dy}, {opacity: 1, y: 0, duration: .3, ease: 'power3.out'}, ini); };
  const sai = (tl, g, fim, d = .2) => { if (fim != null) tl.to(g, {opacity: 0, duration: d}, fim); };

  function fundo(cena, tl, T, o) {
    const ini = +o.ini, fim = o.fim == null ? null : +o.fim, foco = o.foco || '50% 30%', zoom = +o.zoom || 1.08;
    const caixa = document.createElement('div');
    caixa.className = 'num-fundo'; caixa.style.cssText = 'position:absolute;inset:0;opacity:0';
    const filtro = 'grayscale(1) contrast(1.12) brightness(.62)';
    const midia = o.take
      ? `<video class="trecho take" data-ini="${ini}" data-fim="${fim ?? 999}" data-corte="${+o.take.corte || 0}" src="${esc(o.take.src)}"
           muted playsinline preload="metadata" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;
           object-position:${esc(o.take.foco || foco)};filter:${filtro}"></video>`
      : `<img src="${esc(o.src)}" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:${esc(foco)};filter:${filtro}">`;
    caixa.innerHTML = `<div class="num-mov" style="position:absolute;inset:0;transform-origin:${esc(foco)}">${midia}</div>
      <div style="position:absolute;inset:0;background:${TOM[o.tom] || TOM.azul};mix-blend-mode:color;opacity:.9"></div>
      <div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(5,10,35,.55) 0%,rgba(5,10,35,.15) 28%,
        rgba(5,10,35,.25) 48%,rgba(5,10,35,.9) 66%,#050a23 80%)"></div>`;
    camadaFundo(cena).appendChild(caixa);
    if (o.take) T._ocupado.push([ini, fim ?? 999]);
    tl.to(caixa, {opacity: 1, duration: ini <= .05 ? 0 : .35}, ini);
    tl.fromTo(caixa.querySelector('.num-mov'), {scale: 1}, {scale: zoom, duration: Math.max(1, (fim ?? T.duracao ?? ini + 8) - ini), ease: 'none'}, ini);
    if (fim != null) tl.to(caixa, {opacity: 0, duration: .35}, fim);
    if (o.credito) {           // a foto só com o crédito na tela (regra das fotos livres)
      const g = grupo(cena, `<text x="80" y="1262" ${MONT} font-size="22" font-weight="600" fill="${COR.branco}" fill-opacity=".55">Foto: ${esc(o.credito)}</text>`, 'credito');
      tl.to(g, {opacity: 1, duration: .3}, ini + .2); sai(tl, g, fim);
    }
    return caixa;
  }

  // o número conta do zero: 12 versões do texto, uma a cada 0,05 s (tl.set aparece no pulo da régua e dos quadros; um
  // onUpdate não dispara quando a prévia pula para um instante)
  function numero(cena, tl, T, o) {
    const ini = +o.ini, y = +o.y || 820, tam = +o.tam || 250, x = o.x ?? 80, c = cor(o.cor);
    const valor = String(o.valor), m = valor.match(/^([^\d]*)([\d.]+(?:,\d+)?)(.*)$/);
    const casas = m && m[2].includes(',') ? m[2].split(',')[1].length : 0;
    const alvo = m ? parseFloat(m[2].replace(/\./g, '').replace(',', '.')) : null;
    const fmt = v => {
      let s = v.toFixed(casas).replace('.', ',');
      if (m && m[2].includes('.')) s = s.split(',')[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.') + (casas ? ',' + s.split(',')[1] : '');
      return m[1] + s + m[3];
    };
    const passos = o.conta === false || alvo == null ? [valor] : Array.from({length: 12}, (_, k) => k === 11 ? valor : fmt(alvo * (1 - Math.pow(1 - (k + 1) / 12, 2))));
    const linha = v => `<text x="${x}" y="${y}" fill="${c}" ${IMPACT} font-size="${tam}">`
      + (o.antes ? `<tspan font-size="${tam * .36}" dy="0">${esc(o.antes)} </tspan>` : '')
      + `<tspan>${esc(v)}</tspan>` + (o.unidade ? `<tspan font-size="${tam * .4}"> ${esc(o.unidade)}</tspan>` : '') + `</text>`;
    const g = grupo(cena, `<g class="num-texto">` + passos.map((v, k) => `<g class="num-passo" opacity="${k === passos.length - 1 ? 1 : 0}">${linha(v)}</g>`).join('') + `</g>`
      + (o.rotulo ? `<text x="${x + 6}" y="${y + 62}" ${MONT} font-size="30" font-weight="800" letter-spacing="3" fill="${COR.azul}">${esc(String(o.rotulo).toUpperCase())}</text>` : '')
      + (o.fonte ? `<text x="${x + 6}" y="${y + 104}" ${MONT} font-size="22" font-weight="600" fill="${COR.branco}" fill-opacity=".6">Fonte: ${esc(o.fonte)}</text>` : ''), 'numero');
    // o número não passa de x 880 (os ícones do app ficam à direita): encolhe a partir do canto esquerdo
    const cabe = () => { try { const w = g.querySelector('.num-passo:last-child text').getBBox().width;
      if (x + w > 880) g.querySelector('.num-texto').setAttribute('transform', `translate(${x} ${y}) scale(${(880 - x) / w}) translate(${-x} ${-y})`); } catch (e) {} };
    cabe(); if (document.fonts && document.fonts.ready) document.fonts.ready.then(cabe);
    entra(tl, g, ini);
    const ps = g.querySelectorAll('.num-passo');
    if (ps.length > 1) {
      ps.forEach((p, k) => tl.set(p, {opacity: k === 0 ? 1 : 0}, ini));
      ps.forEach((p, k) => { if (k) { tl.set(ps[k - 1], {opacity: 0}, ini + k * .05); tl.set(p, {opacity: 1}, ini + k * .05); } });
    }
    T.som('click-soft', ini);
    sai(tl, g, o.fim);
    return g;
  }

  // a tarja amarela atrás das palavras em <b>: medida depois que a fonte carrega
  function tarjas(g) {
    const faz = () => g.querySelectorAll('text.num-linha').forEach(t => {
      g.querySelectorAll(`g[data-de="${t.dataset.k}"]`).forEach(r => r.remove());
      let pos = 0;
      t.querySelectorAll('tspan').forEach(sp => {
        const n = sp.textContent.length;
        if (sp.dataset.b) {
          try {
            const x0 = t.getStartPositionOfChar(pos).x, larg = t.getSubStringLength(pos, n), tam = +t.getAttribute('font-size');
            // a tarja vai num <g> à parte: a régua toma o retângulo irmão do texto como a caixa dele e acusava
            // "sai da caixa" em todo título (#368)
            const r = document.createElementNS(NS, 'g'), bb = t.getBBox();
            r.innerHTML = `<rect x="${x0 - 10}" y="${bb.y - 2}" width="${larg + 20}" height="${bb.height + 4}" fill="${COR.amarelo}"/>`;
            r.dataset.de = t.dataset.k;
            t.parentNode.insertBefore(r, t);
          } catch (e) {}
        }
        pos += n;
      });
    });
    faz(); if (document.fonts && document.fonts.ready) document.fonts.ready.then(faz);
  }

  function titulo(cena, tl, T, o) {
    const ini = +o.ini, y = +o.y || 330, tam = +o.tam || 76, x = o.x ?? 80;
    const linhas = String(o.texto).split('\n');
    const html = (o.sobre ? `<text x="${x + 4}" y="${y - tam - 2}" ${MONT} font-size="26" font-weight="800" letter-spacing="4" fill="${COR.azul}">${esc(String(o.sobre).toUpperCase())}</text>` : '')
      + linhas.map((l, k) => `<text class="num-linha" data-k="${conta + 1}-${k}" x="${x}" y="${y + k * tam * 1.18}" ${MONT} font-size="${tam}" font-weight="900" fill="${COR.branco}">`
        + l.split(/(<b>.*?<\/b>)/).filter(Boolean).map(p => p.startsWith('<b>')
          ? `<tspan data-b="1" fill="${COR.tinta}">${esc(p.slice(3, -4))}</tspan>` : `<tspan>${esc(p)}</tspan>`).join('') + `</text>`).join('');
    const g = grupo(cena, html, 'titulo');
    tarjas(g);
    entra(tl, g, ini, 16);
    sai(tl, g, o.fim);
    return g;
  }

  function barra(cena, tl, T, o) {
    const ini = +o.ini, y = +o.y || 1000, x0 = 80, L = 800, partes = o.partes || [];
    const total = partes.reduce((s, p) => s + +p[1], 0) || 1;
    let x = x0, html = o.titulo ? `<text x="${x0}" y="${y - 70}" ${MONT} font-size="26" font-weight="800" letter-spacing="3" fill="${COR.azul}">${esc(String(o.titulo).toUpperCase())}</text>` : '';
    partes.forEach((p, k) => {
      const w = L * +p[1] / total, c = cor(p[2] || (k === 0 ? 'branco' : k === partes.length - 1 ? 'azul' : 'cinza'));
      const escuro = c === COR.branco || c === COR.amarelo || c === COR.azul;
      html += `<g class="num-parte"><text x="${k === partes.length - 1 ? x + w : x}" y="${y - 18}" text-anchor="${k === partes.length - 1 ? 'end' : 'start'}"
        ${MONT} font-size="22" font-weight="800" letter-spacing="2" fill="${COR.branco}" fill-opacity=".8">${esc(String(p[0]).toUpperCase())}</text>
        <rect class="num-seg" x="${x}" y="${y}" width="${Math.max(2, w - 4)}" height="64" fill="${c}"/>
        ${w > 90 ? `<text x="${x + 14}" y="${y + 44}" ${MONT} font-size="30" font-weight="900" fill="${escuro ? COR.tinta : COR.branco}">${esc(p[3] || p[1] + '%')}</text>` : ''}</g>`;
      x += w;
    });
    const g = grupo(cena, html, 'barra');
    tl.set(g, {opacity: 1}, ini);
    g.querySelectorAll('.num-parte').forEach((pt, k) => {
      tl.fromTo(pt, {opacity: 0}, {opacity: 1, duration: .15}, ini + k * .25);
      tl.fromTo(pt.querySelector('.num-seg'), {scaleX: 0}, {scaleX: 1, duration: .4, ease: 'power2.out', svgOrigin: `${pt.querySelector('.num-seg').getAttribute('x')} ${y}`}, ini + k * .25);
    });
    T.som('click-soft', ini);
    sai(tl, g, o.fim);
    return g;
  }

  function barras(cena, tl, T, o) {
    const ini = +o.ini, y = +o.y || 700, itens = o.itens || [], max = Math.max(...itens.map(i => +i[1])) || 1, alto = 92;
    const quando = k => Array.isArray(o.passo) ? +o.passo[k] : ini + k * (o.passo ?? .5);
    const html = itens.map((it, k) => {
      const w = 400 * +it[1] / max, c = cor(it[3] || (k === itens.length - 1 ? 'amarelo' : 'azul'));
      return `<g class="num-item"><text x="80" y="${y + k * (alto + 40) + 58}" ${IMPACT} font-size="56" fill="${COR.branco}">${esc(it[0])}</text>
        <rect class="num-seg" x="250" y="${y + k * (alto + 40)}" width="${Math.max(6, w)}" height="${alto}" fill="${c}"/>
        <text class="num-val" x="${250 + Math.max(6, w) + 16}" y="${y + k * (alto + 40) + 60}" ${MONT} font-size="38" font-weight="900" fill="${COR.branco}">${esc(it[2] ?? it[1])}</text></g>`;
    }).join('') + (o.titulo ? `<text x="80" y="${y - 40}" ${MONT} font-size="26" font-weight="800" letter-spacing="3" fill="${COR.azul}">${esc(String(o.titulo).toUpperCase())}</text>` : '')
      + (o.fonte ? `<text x="80" y="${y + itens.length * (alto + 40) + 10}" ${MONT} font-size="22" font-weight="600" fill="${COR.branco}" fill-opacity=".6">Fonte: ${esc(o.fonte)}</text>` : '');
    const g = grupo(cena, html, 'barras');
    tl.set(g, {opacity: 1}, ini);
    g.querySelectorAll('.num-item').forEach((it, k) => {
      const t = quando(k);
      tl.fromTo(it, {opacity: 0}, {opacity: 1, duration: .15}, t);
      tl.fromTo(it.querySelector('.num-seg'), {scaleX: 0}, {scaleX: 1, duration: .5, ease: 'power2.out', svgOrigin: `250 ${y}`}, t);
      tl.fromTo(it.querySelector('.num-val'), {opacity: 0}, {opacity: 1, duration: .2}, t + .4);
      T.som('click-soft', t);
    });
    sai(tl, g, o.fim);
    return g;
  }

  function regua(cena, tl, T, o) {
    const caps = o.capitulos || [], y = +o.y || 1190, x0 = 80, x1 = 860, fim = o.fim ?? T.duracao ?? (caps.at(-1)[1] + 8);
    const xs = caps.map((_, k) => caps.length > 1 ? x0 + (x1 - x0) * k / (caps.length - 1) : x0);
    const g = grupo(cena, `<rect x="${x0}" y="${y - 1}" width="${x1 - x0}" height="2" fill="${COR.branco}" fill-opacity=".35"/>
      ${xs.map(x => `<circle cx="${x}" cy="${y}" r="4" fill="${COR.branco}" fill-opacity=".5"/>`).join('')}
      <rect class="num-feito" x="${x0}" y="${y - 2}" width="${x1 - x0}" height="4" fill="${COR.amarelo}"/>
      <circle class="num-ponto" cx="${x0}" cy="${y}" r="10" fill="${COR.amarelo}"/>
      ${caps.map((c, k) => `<text class="num-cap" x="${xs[k]}" y="${y + 38}" text-anchor="${k === 0 ? 'start' : k === caps.length - 1 ? 'end' : 'middle'}"
        ${MONT} font-size="23" font-weight="800" letter-spacing="3" fill="${COR.branco}" opacity="0">${esc(String(c[0]).toUpperCase())}</text>`).join('')}`, 'regua');
    const ini = +caps[0][1];
    tl.to(g, {opacity: 1, duration: .3}, ini);
    const feito = g.querySelector('.num-feito'), ponto = g.querySelector('.num-ponto'), nomes = g.querySelectorAll('.num-cap');
    tl.set(feito, {attr: {width: 0}}, 0);
    caps.forEach((c, k) => {
      const t = +c[1], ate = k + 1 < caps.length ? +caps[k + 1][1] : fim;
      // o ponto anda até perto do capítulo seguinte durante o capítulo (a régua nunca fica parada)
      const xa = xs[k], xb = k + 1 < caps.length ? xs[k] + (xs[k + 1] - xs[k]) * .85 : xs[k];
      tl.fromTo(ponto, {attr: {cx: xa}}, {attr: {cx: xb}, duration: Math.max(.3, ate - t), ease: 'none', immediateRender: false}, t);
      tl.fromTo(feito, {attr: {width: xa - x0}}, {attr: {width: xb - x0}, duration: Math.max(.3, ate - t), ease: 'none', immediateRender: false}, t);
      // só o nome do capítulo de agora (seis nomes juntos encavalavam: "ORIGEMABERTURA", #368)
      tl.to(nomes[k], {opacity: 1, duration: .2}, t);
      if (k + 1 < caps.length) tl.to(nomes[k], {opacity: 0, duration: .15}, ate);
    });
    if (o.fim != null) sai(tl, g, o.fim);
    return g;
  }

  function alerta(cena, tl, T, o) {
    const ini = +o.ini, y = +o.y || 250, x = o.x ?? 80, c = cor(o.cor || 'vermelho'), txt = String(o.texto).toUpperCase();
    const larg = txt.length * 19 + 40;
    const g = grupo(cena, `<rect x="${x}" y="${y}" width="${larg}" height="42" rx="4" fill="${c}"/>
      <text x="${x + 20}" y="${y + 29}" ${MONT} font-size="22" font-weight="900" letter-spacing="3"
        fill="${c === COR.vermelho ? COR.branco : COR.tinta}">${esc(txt)}</text>`, 'alerta');
    // a caixa na largura medida do texto, depois que a Montserrat carrega (a estimativa estourava: #368)
    const mede = () => { try { g.querySelector('rect').setAttribute('width', g.querySelector('text').getComputedTextLength() + 40); } catch (e) {} };
    mede(); if (document.fonts && document.fonts.ready) document.fonts.ready.then(mede);
    entra(tl, g, ini, 0);
    sai(tl, g, o.fim);
    return g;
  }

  function troca(cena, tl, T, t) {
    const g = grupo(cena, `<rect x="-700" y="-400" width="520" height="2800" fill="url(#num-luz)" transform="rotate(18 540 960)"/>`, 'troca');
    tl.set(g, {opacity: 1}, t - .2);
    tl.fromTo(g, {x: -200}, {x: 2000, duration: .45, ease: 'power2.inOut'}, t - .2);
    tl.set(g, {opacity: 0}, t + .3);
    T.som('whoosh-short', t - .2);
    return g;
  }

  function comenta(cena, tl, T, o) {
    const ini = +o.ini, palavra = String(o.palavra || 'FUNDADOR').toUpperCase(), larg = palavra.length * 62 + 80, y = +o.y || 760;
    const g = grupo(cena, `<text x="480" y="${y - 40}" text-anchor="middle" ${MONT} font-size="30" font-weight="800" letter-spacing="6" fill="${COR.azul}">${esc(String(o.sobre || 'COMENTE').toUpperCase())}</text>
      <rect class="num-caixa" x="${480 - larg / 2}" y="${y}" width="${larg}" height="150" fill="${COR.amarelo}"/>
      <text x="480" y="${y + 118}" text-anchor="middle" ${IMPACT} font-size="120" fill="${COR.tinta}">${esc(palavra)}</text>`, 'comenta');
    const mede = () => { try { const b = g.querySelectorAll('text')[1].getBBox(), r = g.querySelector('.num-caixa');
      r.setAttribute('x', b.x - 40); r.setAttribute('width', b.width + 80); r.setAttribute('y', b.y - 16); r.setAttribute('height', b.height + 32); } catch (e) {} };
    mede(); if (document.fonts && document.fonts.ready) document.fonts.ready.then(mede);
    tl.fromTo(g, {opacity: 0, scale: .85, svgOrigin: `480 ${y + 75}`}, {opacity: 1, scale: 1, duration: .3, ease: 'back.out(2)'}, ini);
    T.som('pop', ini);
    sai(tl, g, o.fim);
    return g;
  }

  const comCena = f => (tl, T) => (...a) => f(document.getElementById('cena'), tl, T, ...a);
  window.Numeros = {
    COR,
    instalar(tl, T) {
      T.numeros = {
        fundo: comCena(fundo)(tl, T), numero: comCena(numero)(tl, T), titulo: comCena(titulo)(tl, T), barra: comCena(barra)(tl, T),
        barras: comCena(barras)(tl, T), regua: comCena(regua)(tl, T), alerta: comCena(alerta)(tl, T), troca: comCena(troca)(tl, T),
        comenta: comCena(comenta)(tl, T),
      };
      return T.numeros;
    },
  };
})();
