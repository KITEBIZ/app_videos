/* Série de fotos (estúdio v2, 19/10/2026; ele: "podemos transformar isso em elementos para não ter que construir a cada
   video?"). O desenho é o das fotos do #300, que ele aprovou ("as fotos dos dois também grandes, sem cartão, polaroide
   ou moldura", 18/10): uma foto por vez, a imagem aproxima devagar DENTRO do recorte (nunca vaza da caixa), som de clique
   na primeira, a última fica até `sai`.

   T.fotos(lista, ini, fim, o) → os elementos (um <g> por foto)
     lista: [{src, recorte, nome, credito, tam}]: src = caminho na pasta do vídeo; recorte = 'x y l a' no quadro (o pedaço
       que é foto de verdade, sem a tela do Instagram, a tarja ou a marca); tam = [largura, altura] do quadro (padrão
       [540, 960], os quadros em material/<pasta>/quadros); nome e credito são o texto da foto.
     ini, fim: o tempo dividido igual entre as fotos.
     o.modo: 'cheia' (padrão: tela cheia até y 1200, o pé escurece, nome grande e crédito embaixo, como a alta cúpula do
       #300) · 'topo' (a foto numa faixa, nome e crédito numa tarja escura no alto da foto) · 'lado' (à direita, pequena,
       desliza da direita; para ficar ao lado de um take, como as fotos dos dois no #300).
     o.caixa: [x, y, l, a] para outro lugar (cada modo tem a sua). o.faixa: um texto fixo numa pílula sobre as fotos
       (ex.: 'COM A <b>ALTA CÚPULA</b> DO PODER'; <b> fica amarelo). o.sai: quando a última sai (padrão: fim + 0,15).
     o.de, o.ate: a aproximação (padrão 1 → 1,06; no 'cheia', 1,08 → 1). o.som: false para não tocar o clique.
   Tudo em SVG, que é o que a régua mede. Zona segura: o nome e o crédito ficam em x 480 (centro da área que o celular
   mostra), longe dos ícones do app (x > 900 entre y 765 e 1645). */
(function () {
  const NS = 'http://www.w3.org/2000/svg', FONTE = 'font-family="Montserrat"';
  const MODOS = {
    cheia: {caixa: [0, 0, 1080, 1200], de: 1.08, ate: 1},
    topo: {caixa: [0, 330, 1080, 800], de: 1.1, ate: 1},
    lado: {caixa: [560, 390, 440, 560], de: 1, ate: 1.06, desliza: 80},
  };
  let conta = 0;
  const amarelo = s => String(s).replace(/<b>(.*?)<\/b>/g, '<tspan fill="#ffc933">$1</tspan>');

  function pe() {        // o degradê do pé (o mesmo foto-pe do #300), uma vez por página
    if (document.getElementById('fotos-pe')) return;
    const s = document.createElementNS(NS, 'svg');
    s.setAttribute('width', 0); s.setAttribute('height', 0); s.style.position = 'absolute';
    s.innerHTML = `<defs><linearGradient id="fotos-pe" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0a1748" stop-opacity="0"/>
      <stop offset=".55" stop-color="#0a1748" stop-opacity=".9"/><stop offset="1" stop-color="#0a1748"/></linearGradient>
      <filter id="fotos-borra" x="0" y="0" width="1" height="1"><feGaussianBlur stdDeviation="28" edgeMode="duplicate"/></filter></defs>`;
    document.body.appendChild(s);
  }

  function uma(f, modo, [x, y, w, h]) {
    // 25/10/2026 (#382, ele: "continua cortando as imagens [...] e não aproveita o topo"): sem f.tam, o tamanho real da
    // imagem (window.TAMANHOS, que a prévia traz); antes supunha 540x960 e a foto deitada de 1200x800 ficava numa faixa
    // no meio. Foto mais deitada que a caixa entra INTEIRA, na largura toda e colada no alto da caixa (nunca corta
    // gente nas bordas), com ela mesma desfocada e escura atrás, preenchendo o resto; as outras cobrem a caixa, como antes
    const real = (window.TAMANHOS || {})[f.src];
    const [W, H] = f.tam || (f.recorte ? [540, 960] : real || [540, 960]), cx = x + w / 2;
    const deitada = !f.recorte && !!(f.tam || real) && W / H > (w / h) * 1.15;
    const g = document.createElementNS(NS, 'g');
    g.setAttribute('opacity', 0);
    let html = deitada
      ? `<svg x="${x}" y="${y}" width="${w}" height="${h}" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid slice">`
        + `<image href="${f.src}" width="${W}" height="${H}" filter="url(#fotos-borra)" opacity=".5"/></svg>`
        + `<svg x="${x}" y="${y}" width="${w}" height="${h}" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMin meet">`
        + `<image class="fotos-img" href="${f.src}" width="${W}" height="${H}"/></svg>`
      : `<svg x="${x}" y="${y}" width="${w}" height="${h}" viewBox="${f.recorte || `0 0 ${W} ${H}`}" preserveAspectRatio="xMidYMid slice">`
        + `<image class="fotos-img" href="${f.src}" width="${W}" height="${H}"/></svg>`;
    if (modo === 'cheia') {
      html += `<rect x="${x}" y="${y + h * .6}" width="${w}" height="${h * .4 + 1}" fill="url(#fotos-pe)"/>`;
      if (f.nome) html += `<text class="im" x="480" y="1070" text-anchor="middle" font-size="${f.tamNome || 60}" fill="#F4F6FF">${amarelo(f.nome)}</text>`;
      if (f.credito) html += `<text ${FONTE} x="480" y="1118" text-anchor="middle" font-size="28" font-weight="800" fill="#9cbcff">${f.credito}</text>`;
    } else if (f.nome || f.credito) {          // topo e lado: tarja escura no alto da foto
      const fs = f.tamNome || (modo === 'lado' ? 21 : 30);
      html += `<rect x="${x}" y="${y}" width="${w}" height="78" fill="#0a1748" fill-opacity=".85"/>`
        + `<text ${FONTE} x="${cx}" y="${y + 34}" text-anchor="middle" font-size="${fs}" font-weight="900" fill="#F4F6FF">${amarelo(f.nome || '')}</text>`
        + `<text ${FONTE} x="${cx}" y="${y + 62}" text-anchor="middle" font-size="19" font-weight="700" fill="#9cbcff">${f.credito || ''}</text>`;
    }
    g.innerHTML = html;
    return g;
  }

  function por(cena, tl, T, lista, ini, fim, o = {}) {
    if (!lista || !lista.length) return [];
    const modo = o.modo || 'cheia', M = MODOS[modo];
    if (!M) throw new Error(`T.fotos: modo desconhecido ${modo} (use cheia, topo ou lado)`);
    pe();
    const caixa = o.caixa || M.caixa, de = o.de ?? M.de, ate = o.ate ?? M.ate, desliza = o.desliza ?? M.desliza ?? 0;
    // nada entra enquanto os selos de um T.carimbos estão na tela: a série espera eles saírem (o.junto: true, não espera)
    if (T.esperaSelos && !o.junto) { const n = T.esperaSelos(ini); if (n > ini) { fim = Math.max(fim + n - ini, n + .5 * lista.length); ini = n; } }
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('width', 1080); svg.setAttribute('height', 1920); svg.setAttribute('viewBox', '0 0 1080 1920');
    svg.style.cssText = 'position:absolute;inset:0'; svg.setAttribute('class', 'peca-fotos f' + (++conta));
    cena.appendChild(svg);
    const passo = (fim - ini) / lista.length;
    const els = lista.map((f, i) => {
      const g = uma(f, modo, caixa), t = ini + i * passo;
      svg.appendChild(g);
      if (i === 0 && o.som !== false) T.som('click-soft', t);
      tl.fromTo(g, {opacity: 0, x: desliza}, {opacity: 1, x: 0, duration: desliza ? .3 : .15, ease: 'power3.out'}, t);
      // a aproximação é na imagem, com o eixo no meio do recorte: a foto nunca vaza da sua caixa
      const real = (window.TAMANHOS || {})[f.src];
      const [vx, vy, vw, vh] = (f.recorte || `0 0 ${(f.tam || real || [540, 960]).join(' ')}`).split(' ').map(Number);
      tl.fromTo(g.querySelector('.fotos-img'), {scale: de, svgOrigin: `${vx + vw / 2} ${vy + vh / 2}`},
        {scale: ate, svgOrigin: `${vx + vw / 2} ${vy + vh / 2}`, duration: passo + .2, ease: 'none'}, t);
      if (i < lista.length - 1) tl.to(g, {opacity: 0, duration: .12}, t + passo + .12);
      return g;
    });
    if (o.faixa) {
      const fx = document.createElementNS(NS, 'g');
      fx.setAttribute('opacity', 0);
      fx.innerHTML = `<rect x="150" y="918" width="660" height="64" rx="32" fill="#0a1748" fill-opacity=".9" stroke="#ffc933" stroke-width="3"/>`
        + `<text ${FONTE} x="480" y="962" text-anchor="middle" font-size="32" font-weight="900" fill="#F4F6FF">${amarelo(o.faixa)}</text>`;
      svg.appendChild(fx);
      tl.to(fx, {opacity: 1, duration: .2}, ini);
      tl.to(fx, {opacity: 0, duration: .2}, o.sai ?? fim + .15);
    }
    tl.to(els[els.length - 1], {opacity: 0, duration: .2}, o.sai ?? fim + .15);
    return els;
  }
  window.Fotos = {por, MODOS};
})();
