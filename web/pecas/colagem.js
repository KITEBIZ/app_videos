/* Colagem de mini documentário (estúdio v2, 24/10/2026, "aprovo o plano colagem-documental"; ele: "quero que ele comece
   com o estilo mini documentario [...] pegar fotos do lula criação e tudo mais e fazer a colagem na parte que nào temos
   imagens"). Referência: Brainstorm, "O estilo de vídeo mais pirado que você já viu: colagem" (youtube PC0fhvuR7GU):
   fundo de papel ou cor chapada, foto em preto e branco recortada com borda de papel e sombra entrando pelo canto,
   título em serifa itálica com marca-texto, círculo de cor atrás, mapa antigo com o lugar acendendo, cartaz com fita.
   Pouco movimento em cada peça, mas sempre algum (deriva lenta), e uma leve tremida de recorte feito à mão.

   Tudo em SVG (a régua mede). Zona segura: o que se lê fica em x 80-880 e y 260-1250 (legenda embaixo, ícones do app
   à direita). Foto só com direito de uso (Agência Brasil, Wikimedia Commons, Arquivo Nacional) e crédito na tela.

   T.colagem.papel(ini, fim, o)       fundo de papel (o.cor, padrão creme) com grão; o.rasga: entra rasgando da direita
   T.colagem.circulo(o)               {x, y, r, cor, ini, fim}: cresce do centro
   T.colagem.mapa(o)                  {ini, fim, acende: [[uf, t, cor]], rota: [ufDe, ufPara, tIni, tFim], icone: 'caminhao'}
   T.colagem.recorte(o)               {src, x, y, w, h, ini, fim, de: 'esquerda'|'direita'|'baixo', girar, pb: true}
   T.colagem.cartaz(o)                {src, x, y, w, h, ini, fim, girar, fita: true}: foto com borda branca e fita adesiva
   T.colagem.titulo(o)                {texto, x, y, tam, ini, fim, marca: t (marca-texto amarelo entra em t), cor}
   T.colagem.rotulo(o)                {texto, credito, x, y, ini, fim}: o tracinho com o lugar/data e o crédito embaixo
   Cada uma devolve o <g> e some em `fim` (sem fim: fica até o fim do vídeo). */
(function () {
  const NS = 'http://www.w3.org/2000/svg';
  // estilo inline: o CSS da página ("#root svg text {Montserrat}") vence o atributo font-family (amostra 1 do #367)
  const SERIFA = `style="font-family:'Playfair Display',Georgia,serif;font-style:italic;font-weight:900"`;
  // as cores do canal (as bolinhas do logo do Instituto BR360 e o azul-marinho das telas), 24/10/2026 (ele: "tem que ter
  // um leve alinhamento com as cores do nosso canal. tem que usar nosso logo do instituto")
  const COR = {marinho: '#0a1748', amarelo: '#ffc933', vermelho: '#ff4d5e', azul: '#9cbcff', papel: '#efe6d2', tinta: '#0a1748'};
  let conta = 0, raiz = null;

  function fontes() {
    if (document.getElementById('colagem-fontes')) return;
    const st = document.createElement('style'); st.id = 'colagem-fontes';
    st.textContent = '@font-face{font-family:"Playfair Display";font-style:italic;font-weight:900;src:url("/fontes/playfair-italico-latin.woff2") format("woff2")}';
    document.head.appendChild(st);
  }

  function palco(cena) {          // um <svg> só para a colagem, embaixo do resto da cena
    if (raiz && raiz.isConnected) return raiz;
    fontes();
    raiz = document.createElementNS(NS, 'svg');
    raiz.setAttribute('width', 1080); raiz.setAttribute('height', 1920); raiz.setAttribute('viewBox', '0 0 1080 1920');
    raiz.setAttribute('class', 'peca-colagem'); raiz.style.cssText = 'position:absolute;inset:0';
    raiz.innerHTML = `<defs>
      <filter id="col-grao" x="0" y="0" width="100%" height="100%">
        <feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="7" result="r"/>
        <feColorMatrix in="r" type="matrix" values="0 0 0 0 .25  0 0 0 0 .2  0 0 0 0 .12  0 0 0 .18 0"/>
        <feComposite in2="SourceGraphic" operator="in"/>
      </filter>
      <filter id="col-fibra" x="0" y="0" width="100%" height="100%">
        <feTurbulence type="fractalNoise" baseFrequency=".012 .05" numOctaves="3" seed="3" result="r"/>
        <feColorMatrix in="r" type="matrix" values="0 0 0 0 .35  0 0 0 0 .28  0 0 0 0 .18  0 0 0 .12 0"/>
        <feComposite in2="SourceGraphic" operator="in"/>
      </filter>
      <filter id="col-recorte" x="-10%" y="-10%" width="120%" height="120%">
        <feColorMatrix in="SourceGraphic" type="saturate" values="0" result="pb"/>
        <feComponentTransfer in="pb" result="contraste"><feFuncR type="linear" slope="1.25" intercept="-.08"/>
          <feFuncG type="linear" slope="1.25" intercept="-.08"/><feFuncB type="linear" slope="1.25" intercept="-.08"/></feComponentTransfer>
        <feMorphology in="SourceAlpha" operator="dilate" radius="7" result="borda"/>
        <feFlood flood-color="#fbf7ee"/><feComposite in2="borda" operator="in" result="papel"/>
        <feGaussianBlur in="borda" stdDeviation="9" result="b"/><feOffset in="b" dx="10" dy="14" result="bo"/>
        <feFlood flood-color="#1b1408" flood-opacity=".45"/><feComposite in2="bo" operator="in" result="sombra"/>
        <feMerge><feMergeNode in="sombra"/><feMergeNode in="papel"/><feMergeNode in="contraste"/></feMerge>
      </filter>
      <filter id="col-cor" x="-10%" y="-10%" width="120%" height="120%">
        <feGaussianBlur in="SourceAlpha" stdDeviation="9" result="b"/><feOffset in="b" dx="10" dy="14" result="bo"/>
        <feFlood flood-color="#1b1408" flood-opacity=".4"/><feComposite in2="bo" operator="in" result="sombra"/>
        <feMerge><feMergeNode in="sombra"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
    </defs>`;
    cena.insertBefore(raiz, cena.firstChild);
    return raiz;
  }

  const naTela = [];             // as peças da cena de agora (o capítulo seguinte empurra todas para fora)
  function grupo(cena, html, cls) {
    const g = document.createElementNS(NS, 'g');
    g.setAttribute('class', 'col-' + cls + ' col' + (++conta)); g.setAttribute('opacity', 0);
    g.innerHTML = html; palco(cena).appendChild(g);
    if (cls !== 'papel') naTela.push(g);
    return g;
  }
  const escura = c => { const h = c.replace('#', ''), n = parseInt(h.length === 3 ? h.replace(/./g, x => x + x) : h, 16);
    return (.299 * (n >> 16 & 255) + .587 * (n >> 8 & 255) + .114 * (n & 255)) / 255 < .45; };

  function sai(tl, g, fim, d = .2) { if (fim != null) tl.to(g, {opacity: 0, duration: d}, fim); }

  // a tremida de recorte feito à mão: 3 passos de rotação pequena, sem suavizar
  function tremida(tl, alvo, ini, fim, graus = .6) {
    for (let t = ini + .35, i = 0; t < (fim ?? ini + 6) - .2; t += .5, i++)
      tl.to(alvo, {rotation: (i % 2 ? 1 : -1) * graus, duration: .01, ease: 'none', svgOrigin: '540 960'}, t);
  }

  function papel(cena, tl, T, ini, fim, o = {}) {
    // a legenda vira tira curta enquanto há papel na tela (24/10/2026, ele escolheu "tira curta, como o reel")
    const cor = o.cor || COR.papel, dark = escura(cor);
    (T._colagemJanelas = T._colagemJanelas || []).push([ini, fim ?? 1e9, dark]);
    const borda = 'M1080 0 L1080 1920 L40 1920 ' + Array.from({length: 40}, (_, i) =>
      `L${30 + (i % 2 ? 26 : 0) + (i * 37 % 19)} ${1920 - i * 48}`).join(' ') + ' L40 0 Z';
    const g = grupo(cena, `<g class="col-folha"><path d="${o.rasga ? borda : 'M0 0H1080V1920H0Z'}" fill="${cor}"/>
      <rect width="1080" height="1920" fill="${cor}" filter="url(#col-fibra)"/>
      <rect width="1080" height="1920" fill="${cor}" filter="url(#col-grao)"/>
      <g transform="rotate(1.5 480 1462)"><rect x="300" y="1424" width="360" height="78" rx="6" fill="${dark ? 'none' : COR.marinho}"/>
        <image href="/logos/instituto-br360.png" x="318" y="1431" width="324" height="64"/></g></g>`, 'papel');
    if (o.rasga) {
      tl.set(g.querySelector('.col-folha'), {x: 1120}, 0);
      tl.set(g, {opacity: 1}, ini);
      tl.to(g.querySelector('.col-folha'), {x: 0, duration: .35, ease: 'power3.out'}, ini);
      T.som('papel-rasga', ini);
    } else if (ini <= .05) tl.set(g, {opacity: 1}, 0);   // abre o vídeo: já no papel, sem o fundo azul aparecer antes (24/10/2026)
    else tl.to(g, {opacity: 1, duration: .25}, ini);
    sai(tl, g, fim);
    return g;
  }

  function circulo(cena, tl, T, o) {
    const g = grupo(cena, `<circle cx="${o.x}" cy="${o.y}" r="${o.r}" fill="${o.cor || COR.vermelho}"/>`, 'circulo');
    tl.fromTo(g, {opacity: 0, scale: 0, svgOrigin: `${o.x} ${o.y}`}, {opacity: 1, scale: 1, duration: .45, ease: 'back.out(1.6)'}, o.ini);
    tl.to(g, {scale: 1.06, duration: (o.fim ?? o.ini + 5) - o.ini, ease: 'none', svgOrigin: `${o.x} ${o.y}`}, o.ini + .45);
    sai(tl, g, o.fim);
    return g;
  }

  const ICONES = {
    // caminhão pau de arara de perfil, desenhado (não é foto), virado para a esquerda; origem no meio do eixo
    caminhao: `<g transform="translate(-60 -46)"><rect x="34" y="8" width="86" height="44" rx="3" fill="#2a2118"/>
      <path d="M34 8 v-10 h86 v10 M48 -2 v-10 M64 -2 v-10 M80 -2 v-10 M96 -2 v-10 M112 -2 v-10" stroke="#2a2118" stroke-width="4" fill="none"/>
      <path d="M0 52 V26 Q2 14 14 12 H34 V52 Z" fill="#ff4d5e"/><rect x="8" y="18" width="18" height="12" fill="#efe4cc"/>
      <circle cx="22" cy="56" r="11" fill="#1a140e"/><circle cx="96" cy="56" r="11" fill="#1a140e"/>
      <circle cx="22" cy="56" r="4" fill="#efe4cc"/><circle cx="96" cy="56" r="4" fill="#efe4cc"/></g>`,
  };

  function mapa(cena, tl, T, o) {
    const UF = window.BRASIL_UF;
    if (!UF) throw new Error('T.colagem.mapa: falta /pecas/brasil-uf.js no tocador');
    const tinta = o.tinta || COR.tinta, base = o.base || '#e9dcc2';
    const estados = Object.entries(UF).map(([u, v]) =>
      `<path class="col-uf-${u}" d="${v.d}" fill="${base}" stroke="${tinta}" stroke-width="2" stroke-linejoin="round"/>`).join('');
    let rota = '';
    if (o.rota) {
      const [a, b] = [UF[o.rota[0]], UF[o.rota[1]]];
      const mx = (a.cx + b.cx) / 2 + 170, my = (a.cy + b.cy) / 2 - 40;
      rota = `<path class="col-rota" d="M${a.cx} ${a.cy} Q${mx} ${my} ${b.cx} ${b.cy}" fill="none" stroke="${COR.vermelho}" stroke-width="7"
        stroke-dasharray="18 12" stroke-linecap="round"/>
        <circle cx="${a.cx}" cy="${a.cy}" r="12" fill="${COR.vermelho}"/><circle class="col-chega" cx="${b.cx}" cy="${b.cy}" r="12" fill="${COR.vermelho}" opacity="0"/>
        <g class="col-icone" opacity="0">${ICONES[o.icone] || ''}</g>`;
    }
    const s = o.escala || 1, cx = 540, cy = 780;
    const g = grupo(cena, `<g transform="translate(${cx} ${cy}) scale(${s}) translate(-540 -780)"><g class="col-mapa" filter="url(#col-cor)">${estados}</g>${rota}</g>`, 'mapa');
    tl.fromTo(g, {opacity: 0, scale: 1.08, rotation: -4, svgOrigin: '540 780'}, {opacity: 1, scale: 1, rotation: -2, duration: .5, ease: 'power2.out'}, o.ini);
    tl.to(g, {scale: 1.04, duration: (o.fim ?? o.ini + 6) - o.ini, ease: 'none', svgOrigin: '540 780'}, o.ini + .5);
    for (const [u, t, cor] of o.acende || []) {
      tl.to(g.querySelector('.col-uf-' + u), {fill: cor || COR.vermelho, duration: .2}, t);
      T.som('pop', t);
    }
    if (o.rota) {
      const p = g.querySelector('.col-rota'), L = p.getTotalLength(), ic = g.querySelector('.col-icone');
      const [t0, t1] = [o.rota[2], o.rota[3]], N = 16, passo = (t1 - t0) / N;
      tl.fromTo(p, {strokeDashoffset: L, strokeDasharray: `${L} ${L}`}, {strokeDashoffset: 0, duration: t1 - t0, ease: 'none'}, t0);
      // o caminhão anda pelos pontos da rota, calculados agora (sem onUpdate: a prévia pula de segundo em segundo)
      const pts = Array.from({length: N + 1}, (_, i) => p.getPointAtLength(i / N * L));
      const ang = i => Math.atan2(pts[Math.min(N, i + 1)].y - pts[Math.max(0, i - 1)].y, pts[Math.min(N, i + 1)].x - pts[Math.max(0, i - 1)].x) * 180 / Math.PI + 180;
      tl.set(ic, {x: pts[0].x, y: pts[0].y, rotation: ang(0), opacity: 1}, t0);
      for (let i = 1; i <= N; i++) tl.to(ic, {x: pts[i].x, y: pts[i].y, rotation: ang(i), duration: passo, ease: 'none'}, t0 + (i - 1) * passo);
      tl.to(g.querySelector('.col-chega'), {opacity: 1, duration: .15}, t1);
    }
    sai(tl, g, o.fim);
    return g;
  }

  function recorte(cena, tl, T, o) {
    const de = o.de || 'esquerda', dx = de === 'esquerda' ? -o.w : de === 'direita' ? o.w : 0, dy = de === 'baixo' ? o.h : 0;
    const g = grupo(cena, `<g class="col-foto"><image href="${o.src}" x="${o.x}" y="${o.y}" width="${o.w}" height="${o.h}"
      preserveAspectRatio="xMidYMid meet" filter="url(#${o.pb === false ? 'col-cor' : 'col-recorte'})"/></g>`, 'recorte');
    const ox = o.x + o.w / 2, oy = o.y + o.h / 2, gr = o.girar ?? -3;
    tl.fromTo(g, {opacity: 0, x: dx, y: dy, rotation: gr - 6, svgOrigin: `${ox} ${oy}`},
      {opacity: 1, x: 0, y: 0, rotation: gr, duration: .4, ease: 'power3.out'}, o.ini);
    // deriva lenta: a foto nunca fica parada
    tl.to(g.querySelector('.col-foto'), {x: de === 'direita' ? -18 : 18, y: -10, duration: (o.fim ?? o.ini + 6) - o.ini, ease: 'none'}, o.ini + .4);
    sai(tl, g, o.fim);
    return g;
  }

  function cartaz(cena, tl, T, o) {
    const m = 14, gr = o.girar ?? 6, ox = o.x + o.w / 2, oy = o.y + o.h / 2;
    const fita = o.fita === false ? '' : `<rect x="${ox - 70}" y="${o.y - m - 22}" width="140" height="44" fill="#f3e6a8" fill-opacity=".85"
      transform="rotate(-4 ${ox} ${o.y})"/>`;
    const g = grupo(cena, `<g filter="url(#col-cor)"><rect x="${o.x - m}" y="${o.y - m}" width="${o.w + 2 * m}" height="${o.h + 2 * m}" fill="#fbf7ee"/>
      <image href="${o.src}" x="${o.x}" y="${o.y}" width="${o.w}" height="${o.h}" preserveAspectRatio="xMidYMid slice"/></g>${fita}`, 'cartaz');
    tl.fromTo(g, {opacity: 0, scale: 1.35, rotation: gr + 10, svgOrigin: `${ox} ${oy}`},
      {opacity: 1, scale: 1, rotation: gr, duration: .3, ease: 'power4.in'}, o.ini);
    o.fita !== false && T.som('fita', o.ini + .25);
    tl.to(g, {scale: 1.03, duration: (o.fim ?? o.ini + 5) - o.ini - .3, ease: 'none', svgOrigin: `${ox} ${oy}`}, o.ini + .3);
    sai(tl, g, o.fim);
    return g;
  }

  // 24/10/2026 (ele, sobre o reel De0bSjaxHqP: "a fonte que ele usa é bem legivel. acho que vc pode usar a fonte que usamos
  // nos outros videos"): título na Impact das nossas telas, em CAIXA ALTA, numa tira de papel colada (preta com letra
  // branca ou branca com letra preta), levemente torta; o marca-texto amarelo só na palavra-chave (<b>palavra</b>)
  const IMPACT = `style="font-family:Impact,'Anton',sans-serif"`;
  const largImpact = (t, tam) => String(t).replace(/<[^>]+>/g, '').length * tam * .47;

  function titulo(cena, tl, T, o) {
    const tam = o.tam || 96, x = o.x ?? 480, y = o.y, tira = o.tira || 'branca';
    const bruto = String(o.texto).toUpperCase(), limpo = bruto.replace(/<\/?B>/g, '');
    const larg = largImpact(limpo, tam), x0 = x - larg / 2, pad = tam * .22;
    const [fundo, letra] = tira === 'preta' ? [COR.marinho, '#ffffff'] : [tira === 'nenhuma' ? 'none' : '#fbf7ee', COR.marinho];
    // a palavra-chave: o marca-texto cobre só o pedaço dela (a conta da largura é a mesma da Impact)
    let marca = '';
    const m = bruto.match(/<B>(.*?)<\/B>/);
    if (m) {
      const antes = bruto.slice(0, m.index).replace(/<\/?B>/g, '');
      marca = `<rect class="col-marca" x="${x0 + largImpact(antes, tam) - 6}" y="${y - tam * .78}" width="${largImpact(m[1], tam) + 12}"
        height="${tam * .82}" fill="${COR.amarelo}"/>`;
    }
    const gr = o.girar ?? (((conta * 7) % 5) - 2) * .6;
    const g = grupo(cena, `<g transform="rotate(${gr} ${x} ${y})">
      <rect x="${x0 - pad}" y="${y - tam * .95}" width="${larg + 2 * pad}" height="${tam * 1.18}" fill="${fundo}" filter="url(#col-cor)"/>
      ${marca}<text x="${x}" y="${y}" text-anchor="middle" font-size="${tam}" ${IMPACT} fill="${letra}">${limpo}</text></g>`, 'titulo');
    // entra como papel colado: cai de leve com um pequeno passo além e volta
    tl.fromTo(g, {opacity: 0, scale: 1.15, svgOrigin: `${x} ${y}`}, {opacity: 1, scale: 1, duration: .22, ease: 'back.out(2.5)'}, o.ini);
    // 24/10/2026 (ele: "tem um som chiado ainda"; eram 101 efeitos em 62 s, 42 deles pops de título): o título entra calado
    const mk = g.querySelector('.col-marca');
    if (mk && o.marca != null)
      tl.fromTo(mk, {scaleX: 0, svgOrigin: `${mk.getAttribute('x')} ${y}`}, {scaleX: 1, duration: .25, ease: 'power2.out'}, o.marca), (o.som ?? tam >= 96) && T.som('click-soft', o.marca);   // o guincho só nos títulos grandes
    sai(tl, g, o.fim);
    return g;
  }

  function rotulo(cena, tl, T, o) {
    // a etiqueta preta com o lugar/data (como "4 DE OUTUBRO" no reel de referência) e o crédito embaixo
    const x = o.x ?? 90, y = o.y, txt = String(o.texto).toUpperCase(), larg = largImpact(txt, 34) + 28;
    const [fd, lt, cr] = o.claro ? ['#fbf7ee', COR.marinho, '#c9d2ee'] : [COR.marinho, '#ffffff', '#3c4a73'];   // claro: sobre papel escuro
    const g = grupo(cena, `<rect x="${x}" y="${y - 34}" width="${larg}" height="46" fill="${fd}"/>
      <text x="${x + 14}" y="${y}" font-size="34" ${IMPACT} fill="${lt}">${txt}</text>
      ${o.credito ? `<text x="${x}" y="${y + 40}" font-size="21" font-weight="700" fill="${cr}">${o.credito}</text>` : ''}`, 'rotulo');
    tl.fromTo(g, {opacity: 0, x: -30}, {opacity: 1, x: 0, duration: .25, ease: 'power2.out'}, o.ini);
    sai(tl, g, o.fim);
    return g;
  }


  // sons (24/10/2026, ele tirou marca-texto, papel deslizando e caneta: "eles são ruins"): capítulo = whoosh-short,
  // marca-texto e seta = click-soft, risco = carimbo; ficam papel-rasga, fita, maquina e impacto-doc
  // ---- do reel De0bSjaxHqP (24/10/2026): capítulo, faixa, risco, seta, manchete, painel, "comenta aqui" ----

  // troca de capítulo: tudo o que está na tela sai empurrado para a esquerda (o papel de fundo fica); o novo entra depois
  function capitulo(cena, tl, T, t) {
    const vai = naTela.splice(0);
    if (!vai.length) return t;
    tl.to(vai, {x: '-=1150', duration: .24, ease: 'power2.in'}, t);
    tl.set(vai, {opacity: 0}, t + .25);
    T.som('whoosh-short', t);
    return t + .22;
  }

  // faixa de papel rasgado na cor do capítulo (vertical num lado, ou horizontal atrás do assunto)
  function faixa(cena, tl, T, o) {
    const [x, y, w, h] = o.caixa || (o.lado === 'horizontal' ? [-40, 520, 1160, 420] : o.lado === 'esquerda' ? [-30, 300, 340, 980] : [650, 300, 460, 980]);
    const dente = (n, a, b, fixo, vert) => Array.from({length: n}, (_, i) => { const v = a + (b - a) * i / (n - 1), d = (i * 53 % 17) - 8;
      return vert ? `L${fixo + d} ${v}` : `L${v} ${fixo + d}`; }).join(' ');
    const d = o.lado === 'horizontal'
      ? `M${x} ${y} ${dente(24, x, x + w, y, false)} L${x + w} ${y + h} ${dente(24, x + w, x, y + h, false)} Z`
      : `M${x} ${y} L${x + w} ${y} ${dente(22, y, y + h, x + w, true)} L${x} ${y + h} Z`;
    const g = grupo(cena, `<path d="${d}" fill="${o.cor || COR.vermelho}" filter="url(#col-cor)"/>`, 'faixa');
    const de = o.lado === 'horizontal' ? {x: -1200} : o.lado === 'esquerda' ? {x: -500} : {x: 600};
    tl.fromTo(g, {opacity: 0, ...de}, {opacity: 1, x: 0, y: 0, duration: .3, ease: 'power3.out'}, o.ini);
    sai(tl, g, o.fim);
    return g;
  }

  // risco vermelho feito à mão por cima de uma palavra ou foto (como o "PEDIR VOTO" riscado)
  function risco(cena, tl, T, o) {
    const {x1, y1, x2, y2} = o, my = (y1 + y2) / 2 - 10;
    const g = grupo(cena, `<path d="M${x1} ${y1} Q${(x1 + x2) / 2} ${my} ${x2} ${y2}" stroke="${o.cor || COR.vermelho}" stroke-width="${o.grossura || 12}"
      stroke-linecap="round" fill="none"/>`, 'risco');
    const p = g.querySelector('path'), L = p.getTotalLength();
    tl.set(g, {opacity: 1}, o.t);
    tl.fromTo(p, {strokeDasharray: `${L} ${L}`, strokeDashoffset: L}, {strokeDashoffset: 0, duration: .22, ease: 'power2.out'}, o.t);
    T.som('carimbo', o.t);
    sai(tl, g, o.fim);
    return g;
  }

  // seta feita à mão, curva, de um ponto a outro
  function seta(cena, tl, T, o) {
    const [ax, ay] = o.de, [bx, by] = o.para, cx = (ax + bx) / 2 + (o.curva ?? 60), cy = (ay + by) / 2 - (o.curva ?? 60);
    const ang = Math.atan2(by - cy, bx - cx), k = 26;
    const pta = `M${bx - k * Math.cos(ang - .5)} ${by - k * Math.sin(ang - .5)} L${bx} ${by} L${bx - k * Math.cos(ang + .5)} ${by - k * Math.sin(ang + .5)}`;
    const cor = o.cor || COR.marinho;
    const g = grupo(cena, `<path class="col-haste" d="M${ax} ${ay} Q${cx} ${cy} ${bx} ${by}" stroke="${cor}" stroke-width="7" fill="none" stroke-linecap="round"/>
      <path class="col-ponta" d="${pta}" stroke="${cor}" stroke-width="7" fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="0"/>`, 'seta');
    const h = g.querySelector('.col-haste'), L = h.getTotalLength();
    tl.set(g, {opacity: 1}, o.t);
    tl.fromTo(h, {strokeDasharray: `${L} ${L}`, strokeDashoffset: L}, {strokeDashoffset: 0, duration: .3, ease: 'power1.inOut'}, o.t);
    T.som('click-soft', o.t);
    tl.to(g.querySelector('.col-ponta'), {opacity: 1, duration: .05}, o.t + .28);
    sai(tl, g, o.fim);
    return g;
  }

  // recorte de manchete: papel de jornal com o nosso texto e a fonte embaixo (sem nome nem marca de jornal nenhum)
  function manchete(cena, tl, T, o) {
    const w = o.w || 520, x = o.x, y = o.y, linhas = String(o.titulo).split('\n'), tam = o.tam || 44;
    const topo = y + (o.chapeu ? 62 : 26) + tam * .85;          // a 1ª linha do título, abaixo do chapéu (não por cima)
    const h = topo - y + (linhas.length - 1) * tam * 1.05 + (o.sub ? 44 : 0) + 76;
    const txt = linhas.map((l, i) => `<text x="${x + 26}" y="${topo + i * tam * 1.05}" font-size="${tam}" ${IMPACT} fill="#111">${l.toUpperCase()}</text>`).join('');
    const corpo = Array.from({length: 3}, (_, i) => `<rect x="${x + 26}" y="${y + h - 62 + i * 14}" width="${w - 52 - (i === 2 ? 120 : 0)}" height="6" fill="#b9b2a2"/>`).join('');
    const g = grupo(cena, `<g transform="rotate(${o.girar ?? -2} ${x + w / 2} ${y + h / 2})">
      <rect x="${x}" y="${y}" width="${w}" height="${h}" fill="#f4efe2" filter="url(#col-cor)"/>
      <rect x="${x + 26}" y="${y + 22}" width="${w - 52}" height="4" fill="#111"/>
      ${o.chapeu ? `<text x="${x + 26}" y="${y + 50}" font-size="20" font-weight="800" fill="${COR.vermelho}">${o.chapeu.toUpperCase()}</text>` : ''}
      ${txt}${o.sub ? `<text x="${x + 26}" y="${topo + (linhas.length - 1) * tam * 1.05 + 38}" font-size="22" font-weight="700" fill="#444">${o.sub}</text>` : ''}
      ${corpo}</g>`, 'manchete');
    tl.fromTo(g, {opacity: 0, scale: 1.2, svgOrigin: `${x + w / 2} ${y + h / 2}`}, {opacity: 1, scale: 1, duration: .25, ease: 'power3.out'}, o.ini);
    T.som('maquina', o.ini);
    sai(tl, g, o.fim);
    return g;
  }

  // painel de papel azul-marinho rasgado: onde os nossos elementos (plenário, selos) entram dentro da colagem
  function painel(cena, tl, T, o) {
    const [x, y, w, h] = o.caixa || [40, 300, 1000, 960];
    const borda = (a, b, fixo) => Array.from({length: 26}, (_, i) => `L${a + (b - a) * i / 25} ${fixo + ((i * 41 % 15) - 7)}`).join(' ');
    const g = grupo(cena, `<path d="M${x} ${y} ${borda(x, x + w, y)} L${x + w} ${y + h} ${borda(x + w, x, y + h)} Z" fill="${o.cor || COR.marinho}" filter="url(#col-cor)"/>
      <rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${o.cor || COR.marinho}" filter="url(#col-grao)" opacity=".5"/>`, 'painel');
    tl.fromTo(g, {opacity: 0, y: 1300}, {opacity: 1, y: 0, duration: .35, ease: 'power3.out'}, o.ini);
    T.som('papel-rasga', o.ini);
    sai(tl, g, o.fim);
    return g;
  }

  // o convite como peça: "COMENTA AQUI" com a seta descendo para o botão de comentar do Instagram (à direita, y ~1390)
  function comenta(cena, tl, T, o) {
    const t = titulo(cena, tl, T, {texto: o.texto || 'comenta <b>aqui</b>', x: o.x ?? 640, y: o.y ?? 1060, tam: o.tam || 78, ini: o.t, marca: o.t + .15});
    seta(cena, tl, T, {de: [820, 1090], para: [985, 1330], curva: -70, t: o.t + .2, cor: COR.vermelho});
    return t;
  }

  const comCena = f => (tl, T) => (...a) => f(document.getElementById('cena'), tl, T, ...a);
  window.Colagem = {
    COR,
    instalar(tl, T) {
      T.colagem = {
        papel: comCena(papel)(tl, T), circulo: comCena(circulo)(tl, T), mapa: comCena(mapa)(tl, T),
        recorte: comCena(recorte)(tl, T), cartaz: comCena(cartaz)(tl, T), titulo: comCena(titulo)(tl, T),
        rotulo: comCena(rotulo)(tl, T), tremida: (alvo, ini, fim, g) => tremida(tl, alvo, ini, fim, g),
        capitulo: comCena(capitulo)(tl, T), faixa: comCena(faixa)(tl, T), risco: comCena(risco)(tl, T),
        seta: comCena(seta)(tl, T), manchete: comCena(manchete)(tl, T), painel: comCena(painel)(tl, T),
        comenta: comCena(comenta)(tl, T),
      };
      return T.colagem;
    },
  };
})();
