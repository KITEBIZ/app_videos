/* Take com crédito e locutor (estúdio v2, 17/10/2026, "aprovo o plano pecas-take-e-locutor"). Desenho aprovado no estudo
   regras/pecas/take/estudo.html (ele: "perfeito é isso"; locutor A1 sem fundo, foto de autor).

   T.take({ini, fim, corte, rotulo, credito, eleDisse, src, foco, zoom, filtro}): o trecho de vídeo de alguém, sempre no
   mesmo lugar: rótulo em cima (pílula com o símbolo do Instituto, topo y 236), vídeo na largura toda (y 330-1130, sombra
   embaixo), crédito com as três bolinhas (y 1148). eleDisse: o selo vermelho ELE DISSE sobre o pé do vídeo
   (eleDisse: 'ELA DISSE' escreve esse texto; 19/10/2026, o #300 trocava o texto à mão). O título do
   bloco, se houver, o animador desenha sobre o pé do vídeo, entre y 990 e 1120 (T.TAKE.titulo). Entra e sai sozinho.
   cheia (19/10/2026, ele: "o vídeo do Lula aparece cortado [...] usar o padrão do Wagner Moura"): o vídeo em TELA CHEIA
   como no #298, o rosto no alto, o vídeo usa o alto da tela também; o pé escuro de y 900, já opaco em ~1175 (some a legenda gravada no vídeo; 19/10, #302: ainda aparecia por trás da nossa
   do canal, que brigava com a nossa); rótulo, ELE DISSE e crédito nos mesmos lugares.
     cheia: true             vídeo em pé (9:16): cobre a tela inteira, nada do quadro se perde (foco/zoom valem)
     cheia: {x, y, s}        vídeo deitado (16:9): o rosto (x, y em pixels do quadro com 540 de largura, o da prévia) vai para x 480, y 640,
                             ampliado s vezes (padrão 2.1; o #298 usava 2.1 a 2.9)
     logo: [x, y, l, a]      embaça só esse canto (o logo do canal), com a borda suave
   T.locutor(t, dur): ALEXANDRE MOTA com a foto e INSTITUTO br360, x 60 y 1440, no primeiro bloco com a voz dele.
   Tudo em SVG (texto e caixas), que é o que a régua mede. As posições ficam longe do que o Instagram corta: texto abaixo
   de y 205, entre x 50 e 1030, antes de x 900 na faixa dos ícones (y 765-1645); o crédito termina uns 100 px acima da
   legenda (a régua pede 20). */
(function () {
  const NS = 'http://www.w3.org/2000/svg';
  const SIMB = [[141,287,'#ff4d5e'],[81,287,'#ff4d5e'],[21,287,'#ff4d5e'],[37,195,'#ff4d5e'],[102,196,'#ff4d5e'],[170,199,'#ff4d5e'],
    [84,113,'#9cbcff'],[160,123,'#9cbcff'],[156,53,'#9cbcff'],[245,144,'#9cbcff'],[244,82,'#9cbcff'],[244,21,'#9cbcff'],
    [338,21,'#ffc933'],[338,82,'#ffc933'],[337,144,'#ffc933'],[426,53,'#ffc933'],[422,123,'#ffc933'],[498,113,'#ffc933'],
    [412,199,'#ffc933'],[480,196,'#ffc933'],[545,195,'#ffc933'],[441,287,'#ffc933'],[501,287,'#ffc933'],[561,287,'#ffc933']];
  // o símbolo com altura h e canto de cima-esquerda em (x, y)
  const simb = (x, y, h) => { const k = h / 308;
    return `<g class="simb" transform="translate(${x.toFixed(1)} ${y.toFixed(1)}) scale(${k.toFixed(4)})">`
      + SIMB.map(([a, b, c]) => `<circle cx="${a}" cy="${b}" r="21" fill="${c}"/>`).join('') + '</g>'; };
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  const tr = s => (window.T && window.T.t ? window.T.t(s) : s);   // idioma-do-video: o texto fixo no idioma do vídeo

  const TAKE = {rotulo: 236, video: [330, 1130], titulo: [990, 1120], credito: 1148};
  // enquadramento-automatico (22/10/2026): o alto da cabeça em y 120, o rosto com ~540 px de altura e o vídeo pode subir
  // até o pé escuro (opaco em ~1175) cobrir o fim. Medido no #335: o queixo fica 1,5 rosto abaixo do alto da cabeça e
  // precisa ficar acima do ELE DISSE (y 1040). opaco: daqui para baixo o pé escuro já esconde a legenda gravada no vídeo
  const ROSTO = {topo: 120, alto: 540, pe: 1200, opaco: 1175};
  const FONTE = 'font-family="Montserrat"';
  // depois que a fonte carrega, as larguras de verdade; antes, uma estimativa
  // mede de novo quando qualquer letra terminar de carregar (19/10/2026: o "br360" do locutor errou por medir só uma vez,
  // com a letra provisória; a pílula do rótulo usa esta mesma medida)
  const quandoFonte = f => { f(); if (!document.fonts) return; document.fonts.ready.then(f);
    if (document.fonts.addEventListener) document.fonts.addEventListener('loadingdone', f); };

  function take(cena, tl, T, o) {
    const ini = +o.ini, fim = +o.fim, foco = o.foco || '50% 50%', zoom = o.zoom || 1;
    // 24/10/2026 (ele: "porque continua cortando o vídeo e não usando a área toda"; #373 aos 9,7 s o Lula ficou na janela
    // do meio): a TELA CHEIA é o padrão; a janela (y 330-1130) só com janela: true ou cheia: false
    const ch = (o.cheia === undefined || o.cheia === null) ? !o.janela : o.cheia, topo = ch ? 0 : TAKE.video[0], alto = ch ? 1920 : TAKE.video[1] - TAKE.video[0];
    // 25/10/2026 (ele, #373: o rótulo "AO VIVO · DEBATE" ficou nos olhos do Lula): na tela cheia o alto é o rosto; o
    // rótulo desce para o pé do vídeo, logo acima do título (no peito); na janela continua acima do vídeo
    const ry = ch ? 900 : TAKE.rotulo;
    const caixa = document.createElement('div');
    caixa.className = 'peca-take'; caixa.style.cssText = 'position:absolute;inset:0;opacity:0';
    caixa.innerHTML = `
      <div style="position:absolute;left:0;top:${topo}px;width:1080px;height:${alto}px;overflow:hidden">
        <video class="trecho take" data-ini="${ini}" data-fim="${fim}" data-corte="${+o.corte || 0}" src="${esc(o.src || 'referencia/video.mp4')}"
          muted playsinline preload="metadata" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:${esc(foco)};
          transform:scale(${+zoom});transform-origin:${esc(foco)};${o.filtro ? 'filter:' + esc(o.filtro) : ''}"></video>
      </div>
      <svg width="1080" height="1920" viewBox="0 0 1080 1920" style="position:absolute;inset:0">
        <defs><linearGradient id="take-sombra" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0a1748" stop-opacity="0"/>
          <stop offset="1" stop-color="#0a1748" stop-opacity=".92"/></linearGradient>
          <linearGradient id="take-cheia" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0a1748" stop-opacity="0"/>
          <stop offset=".2" stop-color="#0a1748" stop-opacity=".93"/><stop offset=".27" stop-color="#0a1748"/><stop offset="1" stop-color="#0a1748"/></linearGradient>
          <linearGradient id="take-alto" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#050a23"/><stop offset=".72" stop-color="#050a23"/>
          <stop offset="1" stop-color="#050a23" stop-opacity="0"/></linearGradient></defs>
        ${ch ? '<rect class="take-pe" x="0" y="900" width="1080" height="1020" fill="url(#take-cheia)"/>'
             : `<rect class="take-pe" x="0" y="${TAKE.video[1] - 300}" width="1080" height="300" fill="url(#take-sombra)"/>`}
        ${o.rotulo ? `<g class="take-rotulo"><rect x="0" y="${ry}" width="10" height="66" rx="33" fill="#0a1748" fill-opacity=".85"
          stroke="#9cbcff" stroke-opacity=".55" stroke-width="2"/><g class="take-rs"></g>
          <text x="0" y="${ry + 44}" ${FONTE} font-size="30" font-weight="800" fill="#ffc933" letter-spacing="1">${esc(o.rotulo)}</text></g>` : ''}
        ${o.eleDisse ? `<g class="take-eledisse"><rect x="320" y="1040" width="320" height="64" rx="32" fill="#ff4d5e"/>
          <text x="480" y="1084" text-anchor="middle" ${FONTE} font-size="34" font-weight="900" fill="#ffffff" letter-spacing="2">${tr(typeof o.eleDisse === 'string' ? o.eleDisse : 'ELE DISSE')}</text></g>` : ''}
        ${o.credito ? `<g class="take-credito"><g class="take-pontos"></g>
          <text x="0" y="${TAKE.credito + 24}" ${FONTE} font-size="24" font-weight="600" fill="#9cbcff">${esc(o.credito)}</text></g>` : ''}
      </svg>`;
    // o logo do canal: só aquele canto fica embaçado (ele, 19/10/2026: "aquela parte de cima tem que ser usada"; a faixa
    // escura de cima tirava o alto do vídeo). logo: [x, y, largura, altura] na tela 1080x1920
    if (o.logo) {
      const [lx, ly, lw, lh] = o.logo.map(Number), mancha = document.createElement('div');
      mancha.className = 'take-logo';
      mancha.style.cssText = `position:absolute;left:${lx}px;top:${ly}px;width:${lw}px;height:${lh}px;backdrop-filter:blur(30px) saturate(.35);`
        + '-webkit-backdrop-filter:blur(30px) saturate(.35);mask-image:radial-gradient(farthest-side,#000 70%,transparent);'
        + '-webkit-mask-image:radial-gradient(farthest-side,#000 70%,transparent)';
      caixa.insertBefore(mancha, caixa.querySelector('svg'));
    }
    // 22/10/2026 ("aprovo o plano enquadramento-automatico"; ele: "o enquadramento da cabeça de quem fala tem que aproveitar
    // bem a área e ficar no topo da área superior"): com o rosto achado pelo detector (T.rostos, do animacao.py), a peça
    // põe o alto da cabeça no topo (y ROSTO.topo, o cabelo pode passar por baixo do rótulo), o rosto no centro útil (x 480) e com ROSTO.alto px de
    // altura; o animador não calcula x e y. cheia.s (zoom) e cheia.subir (px a mais para cima; negativo desce) ajustam a
    // partir daí; cheia.manual: true volta à conta de x e y à mão.
    // A trava de baixo é o pé escuro (opaco a partir de ~1175), não o fim da tela: no #335, com o vídeo em pé a 2,4x, a
    // trava em 1920 deixava a cabeça subir só 384 px e os dois pedidos de "sobe" não mexeram nada
    const chave = `${o.src || 'referencia/video.mp4'}@${(+o.corte || 0).toFixed(2)}`;
    const rosto = ch && !(typeof ch === 'object' && ch.manual) ? (T.rostos || {})[chave] : null;
    // conferir-o-pedido-e-faixa-preta (23/10/2026; #354: a tarja preta gravada no vídeo da Veja ficou na tela depois de dois
    // pedidos): [cima, baixo] da tarja, medida pelo animacao.py (T.tarjas); o vídeo é posto de modo que ela fique fora da
    // tela. Sem tarja medida, nada muda
    const tj = (T.tarjas || {})[chave] || [0, 0], temTarja = tj[0] > 0 || tj[1] > 0;
    if (!ch && temTarja) {
      const v = caixa.querySelector('video');
      const janela = () => {
        const vw = v.videoWidth || 1080, vh = v.videoHeight || 1920, util = vh * (1 - tj[0] - tj[1]);
        const k = Math.max(1080 / vw, alto / util), W = vw * k, H = vh * k;
        Object.assign(v.style, {inset: 'auto', left: ((1080 - W) / 2) + 'px', top: (-tj[0] * H + (alto - util * k) / 2) + 'px',
          width: W + 'px', height: H + 'px', objectFit: 'fill'});
      };
      janela(); v.addEventListener('loadedmetadata', janela);
    }
    // 24/10/2026 (#373, o preso: o borrão desenhado à mão ficou fora do rosto): borrar: 'outros' borra, DENTRO do vídeo,
    // todo rosto que o detector viu no take e não é o de quem fala; acompanha o zoom e o enquadramento
    const todosRostos = (T.rostosTodos || {})[chave] || [];
    const camadaB = o.borrar === 'outros' && todosRostos.length ? document.createElement('div') : null;
    if (camadaB) {
      camadaB.className = 'take-borroes'; camadaB.style.cssText = 'position:absolute;inset:0;pointer-events:none';
      caixa.firstElementChild.appendChild(camadaB);
    }
    const poeBorroes = (k, x0, y0, alvo) => {
      if (!camadaB) return;
      const maior = todosRostos.reduce((m, b) => (b[2] * b[3] > m[2] * m[3] ? b : m), todosRostos[0]);
      const quem = alvo || [maior[0] + maior[2] / 2, maior[1] + maior[3] / 2];
      camadaB.innerHTML = todosRostos.filter(b => Math.hypot(b[0] + b[2] / 2 - quem[0], b[1] + b[3] / 2 - quem[1]) > Math.max(b[2], b[3]) * .8)
        .map(([bx, by, bw, bh]) => `<div style="position:absolute;left:${(x0 + (bx - bw * .35) * k).toFixed(0)}px;top:${(y0 + (by - bh * .35) * k).toFixed(0)}px;`
          + `width:${(bw * 1.7 * k).toFixed(0)}px;height:${(bh * 1.7 * k).toFixed(0)}px;border-radius:50%;backdrop-filter:blur(26px);-webkit-backdrop-filter:blur(26px)"></div>`).join('');
    };
    if (camadaB && !(ch && (typeof ch === 'object' || rosto || temTarja))) {
      // sem enquadramento calculado: o vídeo cobre a área (object-fit: cover, centrado)
      const v = caixa.querySelector('video');
      const cobre = () => { const h540 = v.videoHeight ? v.videoHeight * 540 / v.videoWidth : 960, k = Math.max(1080 / 540, alto / h540);
        poeBorroes(k, (1080 - 540 * k) / 2, (alto - h540 * k) / 2, null); };
      cobre(); v.addEventListener('loadedmetadata', cobre);
    }
    if (ch && (typeof ch === 'object' || rosto || temTarja)) {
      const v = caixa.querySelector('video'), cfg = typeof ch === 'object' ? ch : {};
      // a conta é sempre sobre o quadro de 540 de largura (a cópia leve, que a prévia, a régua e os Olhos carregam): com o
      // original (1280 no #316) o vídeo final saía 2,4 vezes mais ampliado que a prévia (21/10/2026, "aprovo o plano
      // enquadramento-igual")
      const pos = () => {
        const e = 540 / (v.videoWidth || 540), h540 = v.videoHeight ? v.videoHeight * e : 304;
        const kMin = temTarja ? ROSTO.pe / (h540 * (1 - tj[0] - tj[1])) : 0;     // a parte sem tarja cobre até o pé
        let k, alvoX, alvoY;
        if (rosto) {
          const [fx, fy, fw, fh] = rosto;
          k = Math.max(kMin, +cfg.s || Math.min(4, Math.max(1080 / 540, ROSTO.alto / Math.max(1, fh))));
          // o alto da cabeça fica ~metade da altura do rosto (testa e cabelo) acima da caixa do detector
          alvoX = 480 - (fx + fw / 2) * k; alvoY = ROSTO.topo - (fy - .5 * fh) * k - (+cfg.subir || 0);
        } else if (typeof ch !== 'object') {
          // cheia: true sem rosto achado, num vídeo com tarja: cobre a tela com a parte sem tarja, a partir do alto
          k = Math.max(kMin, 1080 / 540); alvoX = (1080 - 540 * k) / 2; alvoY = -tj[0] * h540 * k;
        } else {
          // a conta do #298; sem x e y (cheia: {s} num take em que o detector não achou rosto), o meio do quadro, um pouco acima
          k = Math.max(kMin, +cfg.s || 2.1); alvoX = 480 - (cfg.x ?? 270) * k; alvoY = 640 - (cfg.y ?? .4 * h540) * k - (+cfg.subir || 0);
        }
        const W = 540 * k, H = h540 * k;
        const x0 = Math.min(0, Math.max(1080 - W, alvoX)), y0 = Math.min(-tj[0] * H, Math.max(ROSTO.pe - H * (1 - tj[1]), alvoY));
        Object.assign(v.style, {inset: 'auto', left: x0 + 'px', top: y0 + 'px', width: W + 'px', height: H + 'px',
          objectFit: 'fill', transform: 'none'});
        // quem fala é o rosto que o detector achou, mesmo com o enquadramento à mão (#373 aos 37 s: o ponto manual estava
        // mais baixo e o borrão caiu no sargento); o ponto manual só vale sem rosto medido
        const medido = (T.rostos || {})[chave];
        poeBorroes(k, x0, y0, medido ? [medido[0] + medido[2] / 2, medido[1] + medido[3] / 2]
          : (typeof ch === 'object' && ch.manual ? [cfg.x ?? 270, cfg.y ?? .4 * h540] : null));
        // a legenda que o canal de origem gravou no vídeo (enquadramento-automatico.1, o 5º e o 6º números do detector):
        // embaça só essa faixa, do jeito do logo; descer o vídeo para o pé escuro cobri-la escondia a boca no #335
        const [, , , , la, lp] = rosto || [];
        if (la != null) {
          const a = y0 + la * k, z = Math.min(ROSTO.opaco, y0 + lp * k);
          Object.assign(faixa.style, {display: z - a > 10 ? 'block' : 'none', top: (a - 12) + 'px', height: (z - a + 24) + 'px'});
        } };
      const faixa = document.createElement('div');
      faixa.className = 'take-legenda-gravada';
      faixa.style.cssText = 'display:none;position:absolute;left:0;width:1080px;backdrop-filter:blur(22px) saturate(.6);'
        + '-webkit-backdrop-filter:blur(22px) saturate(.6);mask-image:linear-gradient(transparent,#000 25%,#000 75%,transparent);'
        + '-webkit-mask-image:linear-gradient(transparent,#000 25%,#000 75%,transparent)';
      caixa.insertBefore(faixa, caixa.querySelector('svg'));
      pos(); v.addEventListener('loadedmetadata', pos);
    }
    cena.insertBefore(caixa, cena.firstChild);        // por baixo do que o animador desenha (o título vai por cima)
    quandoFonte(() => {
      const r = caixa.querySelector('.take-rotulo');
      if (r) {
        const tx = r.querySelector('text'), tw = tx.getComputedTextLength ? tx.getComputedTextLength() : 19 * o.rotulo.length;
        const w = 22 + 76 + 18 + tw + 30, x0 = 540 - w / 2;
        const rc = r.querySelector('rect'); rc.setAttribute('x', x0.toFixed(1)); rc.setAttribute('width', w.toFixed(1));
        r.querySelector('.take-rs').innerHTML = simb(x0 + 22, ry + 13, 40);
        tx.setAttribute('x', (x0 + 22 + 76 + 18).toFixed(1));
      }
      const c = caixa.querySelector('.take-credito');
      if (c) {
        const tx = c.querySelector('text'), tw = tx.getComputedTextLength ? tx.getComputedTextLength() : 13 * o.credito.length;
        const w = 48 + 14 + tw, x0 = 470 - w / 2;
        c.querySelector('.take-pontos').innerHTML = ['#ff4d5e', '#9cbcff', '#ffc933']
          .map((cor, i) => `<circle cx="${(x0 + 6 + i * 18).toFixed(1)}" cy="${TAKE.credito + 16}" r="6" fill="${cor}"/>`).join('');
        tx.setAttribute('x', (x0 + 62).toFixed(1));
      }
    });
    tl.to(caixa, {opacity: 1, duration: .25}, Math.max(0, ini - .05));
    tl.to(caixa, {opacity: 0, duration: .25}, fim - .2);
    if (o.eleDisse) tl.fromTo(caixa.querySelector('.take-eledisse'), {scale: .6, svgOrigin: '480 1072'},
      {scale: 1, svgOrigin: '480 1072', duration: .3, ease: 'back.out(3)'}, ini + .1);
    return caixa;
  }

  function locutor(cena, tl, T, t, dur) {
    const caixa = document.createElement('div');
    caixa.className = 'peca-locutor'; caixa.style.cssText = 'position:absolute;inset:0;opacity:0';
    // o anel nas três cores do logo: três arcos de 120 graus em volta da foto (centro 120, 1500; raio 57)
    const cx = 120, cy = 1500, R = 57, arco = (a0, a1, cor) => { const p = a => [cx + R * Math.sin(a * Math.PI / 180), cy - R * Math.cos(a * Math.PI / 180)];
      const [x0, y0] = p(a0), [x1, y1] = p(a1);
      return `<path d="M${x0.toFixed(1)} ${y0.toFixed(1)} A${R} ${R} 0 0 1 ${x1.toFixed(1)} ${y1.toFixed(1)}" fill="none" stroke="${cor}" stroke-width="6"/>`; };
    caixa.innerHTML = `<svg width="1080" height="1920" viewBox="0 0 1080 1920" style="position:absolute;inset:0">
      <defs><clipPath id="loc-foto"><circle cx="${cx}" cy="${cy}" r="50"/></clipPath>
        <filter id="loc-sombra" x="-10%" y="-40%" width="120%" height="180%"><feDropShadow dx="0" dy="2" stdDeviation="5" flood-color="#0a1748" flood-opacity=".8"/></filter></defs>
      <circle cx="${cx}" cy="${cy}" r="54" fill="#0a1748"/>
      <image href="/pecas/alexandre.jpg" x="${cx - 50}" y="${cy - 50}" width="100" height="100" preserveAspectRatio="xMidYMin slice" clip-path="url(#loc-foto)"/>
      ${arco(0, 120, '#ff4d5e')}${arco(120, 240, '#9cbcff')}${arco(240, 360, '#ffc933')}
      <text x="204" y="1488" ${FONTE} font-size="44" font-weight="900" fill="#F4F6FF" letter-spacing="1" filter="url(#loc-sombra)">ALEXANDRE MOTA</text>
      ${simb(204, 1506, 42)}
      <text x="${204 + 80 + 16}" y="1541" ${FONTE} font-size="26" font-weight="800" fill="#b8c2e6" letter-spacing="7">INSTITUTO<tspan
        class="loc-br" dx="16" dy="5" font-size="42" font-weight="900" letter-spacing="0"><tspan fill="#009c3b">b</tspan><tspan
        fill="#ffdf00">r</tspan><tspan fill="#eef1fb">360</tspan></tspan></text>
    </svg>`;
    // 19/10/2026 (print dele: "br360" em cima do "INSTITUTO"): o br360 era posto medindo o INSTITUTO, e no navegador dele
    // a medida saía com a letra provisória, mais estreita; agora vem na mesma linha e o navegador encaixa sozinho
    cena.appendChild(caixa);
    tl.fromTo(caixa, {opacity: 0, x: -40}, {opacity: 1, x: 0, duration: .4, ease: 'power2.out'}, t);
    tl.to(caixa, {opacity: 0, x: -20, duration: .35}, t + dur - .35);
    return caixa;
  }

  window.Take = {take, locutor, TAKE};
})();
