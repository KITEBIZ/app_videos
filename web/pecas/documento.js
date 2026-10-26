/* Documento (estúdio v2, 19/10/2026; ele: "podemos transformar isso em elementos para não ter que construir a cada
   video?"). Os três cartões do #300, com o mesmo desenho: a nota do Planalto (bloco 6), as notas do MEC e das
   Comunicações (bloco 10) e as mensagens da PF (bloco 9).

   T.documento(o) → o <g> do cartão
     o.t: quando entra · o.sai: quando sai (sem ele, fica) · o.estilo:
       'nota'     cartão branco, cabeçalho escuro, a citação GRANDE (Impact) com grifo amarelo; para a frase-prova do bloco
       'curto'    cartão branco menor, quem disse em azul e a frase em letra normal; para pôr 2 ou 3 notas uma embaixo da outra
       'mensagem' cartão escuro com um balão de conversa; para mensagem, post ou print de conversa
     o.cabecalho: 'NOTA DO PLANALTO (SECOM) · 17/10/2026' (no 'curto', quem disse: 'MEC')
     o.linhas: as linhas da citação, já quebradas como devem aparecer. Linha que começa com '!' é o destaque: grifo
       amarelo atrás ('nota', 'curto') ou letra amarela ('mensagem'). Uma linha pode ser {texto, tam} para mudar o tamanho.
     o.grifo: o instante do grifo (padrão: t + 0,4); os destaques seguintes vêm em sequência, 0,35 s cada.
     o.titulo: texto grande acima do cartão (<b> fica amarelo), ex.: 'O PLANALTO <b>REPETIU</b>'
     o.autor: linha pequena dentro do cartão, embaixo ('Presidência da República, sobre Roberta Luchsinger')
     o.fonte: linha pequena embaixo do cartão ('Fonte: Secom · via Metrópoles, 17/10/2026')
     o.y: o alto do cartão (padrão: 'nota' 450, 'curto' 430, 'mensagem' 300). Largura e x fixos, na zona segura.
   Se os selos de um T.carimbos estiverem na tela nesse instante, o documento espera os selos saírem (o.junto: true para entrar junto).
   O grifo mede a linha depois que a letra carrega (e mede de novo se ela trocar), para não errar como o "br360". */
(function () {
  const NS = 'http://www.w3.org/2000/svg', F = 'font-family="Montserrat"';
  const amarelo = s => String(s).replace(/<b>(.*?)<\/b>/g, '<tspan fill="#ffc933">$1</tspan>');
  const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
  let conta = 0;

  // mede de novo quando qualquer letra terminar de carregar (o "br360" errou por medir só uma vez, com a provisória)
  function quandoFonte(f) {
    f();
    if (!document.fonts) return;
    document.fonts.ready.then(f);
    document.fonts.addEventListener && document.fonts.addEventListener('loadingdone', f);
  }

  function linhas(o) {
    return (o.linhas || []).map(l => {
      const x = typeof l === 'string' ? {texto: l} : {...l};
      x.destaque = x.destaque ?? x.texto.startsWith('!');
      x.texto = x.texto.replace(/^!/, '');
      return x;
    });
  }

  function nota(o, y) {
    const ls = linhas(o), n = ls.length;
    const tam = l => l.tam || (l.texto.length > 15 ? Math.max(48, Math.min(70, Math.floor(1290 / l.texto.length))) : 70);
    const base = i => y + 172 + 90 * i, ultimo = base(n - 1), autor = ultimo + 58, fundo = (o.autor ? autor : ultimo) + 60;
    let h = (o.titulo ? `<text class="im" x="480" y="${y - 60}" text-anchor="middle" font-size="84" fill="#F4F6FF">${amarelo(o.titulo)}</text>` : '')
      + `<g class="doc-card" filter="url(#doc-sombra)">`
      + `<rect x="100" y="${y}" width="760" height="${fundo - y}" rx="22" fill="#F4F6FF"/>`
      + `<rect x="100" y="${y}" width="760" height="76" rx="22" fill="#0a1748"/><rect x="100" y="${y + 50}" width="760" height="26" fill="#0a1748"/>`
      + `<text ${F} x="130" y="${y + 50}" font-size="27" font-weight="900" fill="#ffc933">${esc(o.cabecalho || '')}</text>`;
    ls.forEach((l, i) => {
      if (l.destaque) h += `<rect class="doc-grifo" data-i="${i}" x="128" y="${base(i) - 62}" width="10" height="76" fill="#ffc933"/>`;
    });
    ls.forEach((l, i) => { h += `<text class="im doc-l" data-i="${i}" x="140" y="${base(i)}" font-size="${tam(l)}" fill="#0a1748">${esc(l.texto)}</text>`; });
    if (o.autor) h += `<text ${F} x="140" y="${autor}" font-size="26" font-weight="700" fill="#1c3fae">${esc(o.autor)}</text>`;
    h += `</g>`;
    if (o.fonte) h += `<text ${F} x="480" y="${fundo + 55}" text-anchor="middle" font-size="24" font-weight="600" fill="#9cbcff">${esc(o.fonte)}</text>`;
    return {html: h, centro: `480 ${(y + fundo) / 2}`, grifoX: 128, folga: 12};
  }

  function curto(o, y) {
    const ls = linhas(o), base = i => y + 116 + 44 * i, fundo = base(ls.length - 1) + 34;
    let h = (o.titulo ? `<text class="im" x="480" y="${y - 45}" text-anchor="middle" font-size="90" fill="#F4F6FF">${amarelo(o.titulo)}</text>` : '')
      + `<g class="doc-card" filter="url(#doc-sombra)">`
      + `<rect x="90" y="${y}" width="780" height="${fundo - y}" rx="20" fill="#F4F6FF"/>`
      + `<text ${F} x="120" y="${y + 52}" font-size="30" font-weight="900" fill="#1c3fae">${esc(o.cabecalho || '')}</text>`;
    ls.forEach((l, i) => {
      if (l.destaque) h += `<rect class="doc-grifo" data-i="${i}" x="118" y="${base(i) - 38}" width="10" height="50" fill="#ffc933"/>`;
    });
    ls.forEach((l, i) => { h += `<text ${F} class="doc-l" data-i="${i}" x="125" y="${base(i)}" font-size="${l.tam || 36}" font-weight="800" fill="#0a1748">${esc(l.texto)}</text>`; });
    h += `</g>`;
    if (o.fonte) h += `<text ${F} x="480" y="${fundo + 40}" text-anchor="middle" font-size="24" font-weight="600" fill="#9cbcff">${esc(o.fonte)}</text>`;
    return {html: h, centro: `480 ${(y + fundo) / 2}`, grifoX: 118, folga: 14};
  }

  function mensagem(o, y) {
    const ls = linhas(o), base = i => y + 155 + 45 * i, balao = base(ls.length - 1) + 17, rodape = balao + 50, fundo = (o.autor ? rodape : balao + 26) + 18;
    let h = (o.titulo ? `<text class="im" x="480" y="${y - 45}" text-anchor="middle" font-size="84" fill="#F4F6FF">${amarelo(o.titulo)}</text>` : '')
      + `<g class="doc-card" filter="url(#doc-sombra)">`
      + `<rect x="100" y="${y}" width="760" height="${fundo - y}" rx="22" fill="#0a1748" stroke="#9cbcff" stroke-opacity=".5" stroke-width="2"/>`
      + `<text ${F} x="130" y="${y + 54}" font-size="26" font-weight="900" fill="#ffc933">${esc(o.cabecalho || '')}</text>`
      + `<path d="M140 ${y + 100} h600 a22 22 0 0 1 22 22 v${balao - y - 144} a22 22 0 0 1 -22 22 h-560 l-40 26 v-26 a22 22 0 0 1 0 -4 v${-(balao - y - 126)} a22 22 0 0 1 22 -22 z" fill="#1c3fae"/>`;
    ls.forEach((l, i) => { h += `<text ${F} class="doc-l" x="170" y="${base(i)}" font-size="${l.tam || 36}" font-weight="${l.destaque ? 900 : 800}" fill="${l.destaque ? '#ffc933' : '#F4F6FF'}">${esc(l.texto)}</text>`; });
    if (o.autor) h += `<text ${F} x="480" y="${rodape}" text-anchor="middle" font-size="22" font-weight="600" fill="#9cbcff">${esc(o.autor)}</text>`;
    h += `</g>`;
    if (o.fonte) h += `<text ${F} x="480" y="${fundo + 40}" text-anchor="middle" font-size="24" font-weight="600" fill="#9cbcff">${esc(o.fonte)}</text>`;
    return {html: h, centro: `480 ${(y + fundo) / 2}`};
  }

  const ESTILOS = {nota: [nota, 450], curto: [curto, 430], mensagem: [mensagem, 300]};

  function por(cena, tl, T, o) {
    const [fazer, y0] = ESTILOS[o.estilo || 'nota'] || [];
    if (!fazer) throw new Error(`T.documento: estilo desconhecido ${o.estilo} (use nota, curto ou mensagem)`);
    let t = +o.t;
    if (T.esperaSelos && !o.junto) t = T.esperaSelos(t);          // os selos de um T.carimbos saem antes
    const d = fazer(o, o.y ?? y0);
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('width', 1080); svg.setAttribute('height', 1920); svg.setAttribute('viewBox', '0 0 1080 1920');
    svg.style.cssText = 'position:absolute;inset:0;opacity:0'; svg.setAttribute('class', 'peca-documento d' + (++conta));
    svg.innerHTML = `<defs><filter id="doc-sombra" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="#05081a" flood-opacity=".7"/></filter></defs>` + d.html;
    cena.appendChild(svg);
    const card = svg.querySelector('.doc-card');
    if (o.som !== false) T.som('click-soft', t);
    tl.to(svg, {opacity: 1, duration: .25}, t);
    tl.fromTo(card, {scale: .9, svgOrigin: d.centro}, {scale: 1, svgOrigin: d.centro, duration: .35, ease: 'back.out(1.6)'}, t);
    tl.to(card, {scale: 1.03, svgOrigin: d.centro, duration: Math.min(3, Math.max(.5, (o.sai ?? t + 3) - t - .35)), ease: 'none'}, t + .35);
    // grifo: cada destaque na sua vez, da esquerda para a direita, na largura da linha medida
    const grifos = [...svg.querySelectorAll('.doc-grifo')];
    quandoFonte(() => grifos.forEach(r => {
      const l = svg.querySelector(`.doc-l[data-i="${r.dataset.i}"]`);
      const w = l && l.getComputedTextLength ? l.getComputedTextLength() : 0;
      if (w > 0) r.setAttribute('width', (w + 2 * d.folga).toFixed(1));
    }));
    let tg = o.grifo ?? t + .4;
    grifos.forEach(r => {
      const y = +r.getAttribute('y') + +r.getAttribute('height') / 2;
      tl.fromTo(r, {scaleX: 0, svgOrigin: `${d.grifoX} ${y}`}, {scaleX: 1, svgOrigin: `${d.grifoX} ${y}`, duration: .35, ease: 'none'}, tg);
      tg += .35;
    });
    if (o.sai != null) tl.to(svg, {opacity: 0, duration: .2}, o.sai);
    return svg;
  }
  window.Documento = {por};
})();
