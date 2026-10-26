/* Plenário com foto (estúdio v2, 20/10/2026; ele: "quando falar de stf usar isso" e "ali cabe a foto dos ministro e um
   hemiciclo padrão que já usamos em outros vídeos"). Veio da v1 (ferramentas/hemiciclo.py, plenario + Semicirculo, de
   11/10/2026: "quando fala dos ministros tinha que mostrar a fotinho dos ministros [...] o mesmo elemento que dá origem
   ao nosso logo"). Usado no ana-elisa-hitler ("O SUPREMO DE HOJE · quem indicou cada ministro").

   T.plenario(o) → o <g> do plenário
     o.cadeiras: [{nome, foto, grupo, marca, curto}] da esquerda para a direita; {vaga: true, rotulo} = cadeira vazia.
       foto: o nome de uma foto da biblioteca (web/pecas/fotos/<nome>.jpg, 400x400 no rosto; lista em CREDITOS.md) ou um
       caminho na pasta do vídeo. Sem `cadeiras`: o STF de hoje (Plenario.STF, com `indicou` em cada cadeira).
     o.ini, o.fim: as cadeiras entram em ini (uma a uma) e o plenário sai em fim.
     o.grupos: {id: {cor, rotulo, acende, apaga}}: acende = instante em que o grupo acende (anel na cor; o resto apaga);
       apaga = instante em que o grupo apaga (treme). cor: vermelho, verde, amarelo, azul, laranja, roxo, cinza ou #hex.
       O rótulo vira uma pílula acima do arco, que entra junto (as pílulas se centram ao entrar).
     o.aro: {marca, t, cor, rotulo}: aro amarelo nas cadeiras com essa `marca` (ex.: "saem até 2030"); o resto apaga.
     o.centro: {texto, t, tam}: texto no vão de baixo do arco (ex.: "8 DE 11"; até ~9 letras em 80 px).
     o.nomes: true = o nome curto numa pílula em cada foto acesa.
     o.cx, o.cy (padrão 480, 1115), o.legendaY (padrão 560).
   Medidas da v1 (layout com conteúdo entre x 80 e 900): semicírculo de 2 fileiras (7 fora + 4 dentro para 11), fotos de
   ~136 px, arco de y ~640 a ~1180; a legenda nossa fica em 1340, abaixo. */
(function () {
  const NS = 'http://www.w3.org/2000/svg', FONTE = 'font-family="Montserrat"';
  const BRANCO = '#F4F6FF', AZUL = '#9cbcff', AMAR = '#ffc933', FUNDO = '#0a1748', VEU = .62;
  const CORES = {vermelho: '#ff4d5e', verde: '#3ddc84', amarelo: AMAR, azul: AZUL, laranja: '#ff9f43', roxo: '#b388ff',
                 cinza: '#8a94b8', branco: BRANCO};
  const cor = (c, padrao = AMAR) => c ? (CORES[c] || c) : padrao;
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  const foto = f => !f ? '' : /[/.]/.test(f) ? f : `/pecas/fotos/${f}.jpg`;
  let conta = 0;

  // o STF em 20/10/2026, da esquerda para a direita como na v1 (ana-elisa-hitler): primeiro os indicados por Lula e
  // Dilma, a cadeira vaga (a do Barroso; o Messias foi rejeitado no Senado), depois os outros. Conferir no roteiro.
  const STF = [
    {nome: 'Cármen Lúcia', curto: 'Cármen', foto: 'carmen', indicou: 'Lula'},
    {nome: 'Dias Toffoli', curto: 'Toffoli', foto: 'toffoli', indicou: 'Lula'},
    {nome: 'Luiz Fux', curto: 'Fux', foto: 'fux', indicou: 'Dilma'},
    {nome: 'Edson Fachin', curto: 'Fachin', foto: 'fachin', indicou: 'Dilma'},
    {nome: 'Cristiano Zanin', curto: 'Zanin', foto: 'zanin', indicou: 'Lula'},
    {nome: 'Flávio Dino', curto: 'Dino', foto: 'dino', indicou: 'Lula'},
    {vaga: true},
    {nome: 'Gilmar Mendes', curto: 'Gilmar', foto: 'gilmar', indicou: 'FHC'},
    {nome: 'Alexandre de Moraes', curto: 'Moraes', foto: 'moraes', indicou: 'Temer'},
    {nome: 'Nunes Marques', curto: 'Nunes', foto: 'nunes', indicou: 'Bolsonaro'},
    {nome: 'André Mendonça', curto: 'Mendonça', foto: 'mendonca', indicou: 'Bolsonaro'},
  ];

  // semicírculo de verdade (v1 Semicirculo): fileira de fora de 180° a 0°, a de dentro nos vãos dela
  function semicirculo(n, cx, cy, rOut = 342, rIn = 196, r = 68) {
    const m2 = Math.max(2, Math.round(n * rOut / (rIn + rOut))), m1 = n - m2;
    const d2 = Math.PI / (m2 - 1), d1 = Math.PI / Math.max(1, m1);
    const lim = [rOut * Math.sin(d2 / 2) - 7].concat(m1 > 1 ? [rIn * Math.sin(d1 / 2) - 7] : []);
    const raio = Math.floor(Math.min(r, ...lim)), pts = [];
    for (let i = 0; i < m2; i++) { const a = Math.PI - i * d2; pts.push([cx + rOut * Math.cos(a), cy - rOut * Math.sin(a), a, rOut]); }
    for (let i = 0; i < m1; i++) { const a = Math.PI - (i + .5) * d1; pts.push([cx + rIn * Math.cos(a), cy - rIn * Math.sin(a), a, rIn]); }
    pts.sort((p, q) => (q[2] - p[2]) || (p[3] - q[3]));
    return {pts, r: raio, rOut};
  }

  function por(cena, tl, T, o = {}) {
    const k = 'pl' + (++conta), cads = o.cadeiras || STF, n = cads.length;
    const cx = o.cx ?? 480, cy = o.cy ?? 1115, H = semicirculo(n, cx, cy), r = H.r;
    const grupos = o.grupos || {}, aro = o.aro, marca = c => [].concat(c.marca || []);
    const ini = +(o.ini ?? 0), fim = o.fim != null ? +o.fim : null;
    let s = '';
    cads.forEach((c, i) => {
      const [x, y, , raio] = H.pts[i], g = grupos[c.grupo] || null;
      let miolo;
      if (c.vaga) {
        miolo = `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r}" fill="${FUNDO}" stroke="${AZUL}" stroke-width="3" stroke-dasharray="8 6"/>`
          + `<text ${FONTE} x="${x.toFixed(1)}" y="${(y + 8).toFixed(1)}" text-anchor="middle" font-size="22" font-weight="900" fill="${AZUL}">${esc(c.rotulo || 'VAGA')}</text>`;
      } else {
        miolo = `<clipPath id="${k}c${i}"><circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r}"/></clipPath>`
          + `<image href="${foto(c.foto)}" x="${(x - r).toFixed(1)}" y="${(y - r).toFixed(1)}" width="${2 * r}" height="${2 * r}" clip-path="url(#${k}c${i})" preserveAspectRatio="xMidYMid slice"/>`
          + `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r + 1.5}" fill="none" stroke="${AZUL}" stroke-width="3" opacity=".7"/>`;
      }
      s += `<g class="${k}s ${k}s${i}">${miolo}`
        + `<circle class="${k}v${i}" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r + 3}" fill="${FUNDO}" opacity="0"/>`
        + (g ? `<circle class="${k}a${i}" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r + 2}" fill="none" stroke="${cor(g.cor)}" stroke-width="6" opacity="0"/>` : '')
        + (aro && marca(c).includes(aro.marca) ? `<circle class="${k}o${i}" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r + 2}" fill="none" stroke="${cor(aro.cor)}" stroke-width="7" opacity="0"/>` : '')
        + '</g>';
      if (o.nomes && !c.vaga) {      // na fileira de fora o nome vai em cima da foto, na de dentro embaixo
        const nc = String(c.curto || String(c.nome || '').split(' ')[0]).toUpperCase(), fs = 22, wn = nc.length * fs * .7 + 22;
        const yn = raio === H.rOut ? y - r - 14 : y + r - 16;
        s += `<g class="${k}nm${i}" opacity="0"><rect x="${(x - wn / 2).toFixed(1)}" y="${yn.toFixed(1)}" width="${wn.toFixed(0)}" height="30" rx="15" fill="${FUNDO}" stroke="${g ? cor(g.cor) : AZUL}" stroke-width="2"/>`
          + `<text ${FONTE} x="${x.toFixed(1)}" y="${(yn + 21).toFixed(1)}" text-anchor="middle" font-size="${fs}" font-weight="900" fill="${BRANCO}">${esc(nc)}</text></g>`;
      }
    });
    // pílulas dos grupos (e do aro), numa ou duas linhas acima do arco; cada uma entra no instante do seu grupo
    const pil = Object.entries(grupos).filter(([, g]) => g.rotulo).map(([id, g]) => ({id: 'g' + id, txt: g.rotulo, c: cor(g.cor), t: g.acende ?? g.apaga, aro: false}));
    if (aro && aro.rotulo) pil.push({id: 'aro', txt: aro.rotulo, c: cor(aro.cor), t: aro.t, aro: true});
    const tam = 30, alt = 56, gap = 16, ly = o.legendaY ?? 560;
    pil.forEach(p => { p.w = Math.round(p.txt.length * tam * .68 + 76); });
    const linhas = []; let atual = [];
    pil.forEach(p => { if (atual.length && atual.reduce((a, q) => a + q.w + gap, 0) + p.w > 820) { linhas.push(atual); atual = []; } atual.push(p); });
    if (atual.length) linhas.push(atual);
    linhas.forEach((ps, li) => {
      let x = cx - (ps.reduce((a, q) => a + q.w, 0) + gap * (ps.length - 1)) / 2;
      const y = ly - (linhas.length - 1 - li) * (alt + 10);
      ps.forEach(p => {
        s += `<g class="${k}l${p.id}" opacity="0"><rect x="${x.toFixed(0)}" y="${y}" width="${p.w}" height="${alt}" rx="${alt / 2}" fill="${FUNDO}" stroke="${p.c}" stroke-width="3"/>`
          + (p.aro ? `<circle cx="${(x + 30).toFixed(0)}" cy="${y + alt / 2}" r="10" fill="none" stroke="${p.c}" stroke-width="5"/>`
                   : `<circle cx="${(x + 30).toFixed(0)}" cy="${y + alt / 2}" r="11" fill="${p.c}"/>`)
          + `<text ${FONTE} x="${(x + 50).toFixed(0)}" y="${y + 38}" font-size="${tam}" font-weight="900" fill="${BRANCO}">${esc(p.txt)}</text></g>`;
        p.cx = x + p.w / 2; x += p.w + gap;
      });
    });
    // o texto do centro vai no vão de baixo do arco (20/10/2026: em cy + 20, como na v1, "6 DE 10" cobria o Toffoli e o nome dele)
    if (o.centro) s += `<g class="${k}m" opacity="0"><text ${FONTE} x="${cx}" y="${cy + 84}" text-anchor="middle" font-size="${o.centro.tam || 80}" font-weight="900" fill="${o.centro.cor || BRANCO}">${esc(o.centro.texto)}</text></g>`;

    const el = document.createElementNS(NS, 'svg');
    el.setAttribute('width', 1080); el.setAttribute('height', 1920); el.setAttribute('viewBox', '0 0 1080 1920');
    el.style.cssText = 'position:absolute;inset:0;overflow:visible';
    el.innerHTML = `<g class="${k}">${s}</g>`;
    cena.appendChild(el);
    const raiz = el.firstChild, q = sel => el.querySelectorAll(sel), sels = (pre, ids) => ids.map(i => `.${k}${pre}${i}`).join(', ');
    const todos = cads.map((_, i) => i);

    // entrada: as cadeiras uma a uma, do centro (a v1 entrava 0,25 s depois do início do bloco)
    tl.fromTo(q(`.${k}s`), {opacity: 0, scale: .3, transformOrigin: '50% 50%'},
              {opacity: 1, scale: 1, transformOrigin: '50% 50%', duration: .35, stagger: .05, ease: 'back.out(2)'}, ini);
    if (T.som) T.som('pop', ini);
    // nomes ligados e nenhum grupo para acender: todos os nomes entram logo depois das cadeiras
    // eventos na ordem do tempo: acende (o grupo fica aceso, o resto apaga), apaga (o grupo apaga e treme), aro
    const ev = [];
    for (const [id, g] of Object.entries(grupos)) {
      if (g.acende != null) ev.push({t: +g.acende, tipo: 'acende', id});
      if (g.apaga != null) ev.push({t: +g.apaga, tipo: 'apaga', id});
    }
    if (aro && aro.t != null) ev.push({t: +aro.t, tipo: 'aro'});
    ev.sort((a, b) => a.t - b.t);
    let acesos = new Set(todos), nomesOn = new Set(), vistos = [];
    const nomes = (ids, t, liga) => {
      if (!o.nomes) return;
      const muda = ids.filter(i => !cads[i].vaga && nomesOn.has(i) !== liga);
      if (!muda.length) return;
      tl.to(sels('nm', muda), {opacity: liga ? 1 : 0, duration: .25}, t + (liga ? .1 : 0));
      muda.forEach(i => liga ? nomesOn.add(i) : nomesOn.delete(i));
    };
    const pilula = (pid, t) => {        // a pílula entra e as que já estão se centram com ela
      const p = pil.find(x => x.id === pid);
      if (!p || vistos.includes(pid)) return;
      vistos.push(pid);
      if (linhas.length === 1) {
        const vs = pil.filter(x => vistos.includes(x.id)), meio = (vs[0].cx - vs[0].w / 2 + vs[vs.length - 1].cx + vs[vs.length - 1].w / 2) / 2;
        tl.set(`.${k}l${pid}`, {x: cx - meio}, t - .01);
        if (vs.length > 1) tl.to(vs.filter(x => x.id !== pid).map(x => `.${k}l${x.id}`).join(', '), {x: cx - meio, duration: .25, ease: 'power2.out'}, t - .15);
      }
      tl.fromTo(`.${k}l${pid}`, {opacity: 0, scale: .6, transformOrigin: '50% 50%'}, {opacity: 1, scale: 1, transformOrigin: '50% 50%', duration: .3, ease: 'back.out(2)'}, t + (vistos.length > 1 ? .1 : 0));
    };
    if (o.nomes && !ev.some(e => e.tipo !== 'apaga')) nomes(todos, ini + .3, true);
    for (const e of ev) {
      if (e.tipo === 'aro') {
        const ids = todos.filter(i => marca(cads[i]).includes(aro.marca)), resto = todos.filter(i => !ids.includes(i));
        tl.fromTo(sels('o', ids), {opacity: 0, scale: 1.5, transformOrigin: '50% 50%'}, {opacity: 1, scale: 1, transformOrigin: '50% 50%', duration: .35, stagger: .06, ease: 'back.out(2)'}, e.t);
        if (aro.resto_apaga !== false) {
          const apagar = resto.filter(i => acesos.has(i));
          if (apagar.length) tl.to(sels('v', apagar), {opacity: VEU, duration: .3}, e.t);
          apagar.forEach(i => acesos.delete(i)); nomes(resto, e.t, false);
        }
        const acender = ids.filter(i => !acesos.has(i));
        if (acender.length) tl.to(sels('v', acender), {opacity: 0, duration: .3}, e.t);
        ids.forEach(i => acesos.add(i)); nomes(ids, e.t, true); pilula('aro', e.t);
        continue;
      }
      const g = grupos[e.id], ids = todos.filter(i => cads[i].grupo === e.id);
      if (!ids.length) continue;
      if (q(sels('a', ids)).length) tl.to(sels('a', ids), {opacity: 1, duration: .3}, e.t);
      pilula('g' + e.id, e.t);
      if (e.tipo === 'acende') {
        const acender = ids.filter(i => !acesos.has(i));
        if (acender.length) tl.to(sels('v', acender), {opacity: 0, duration: .3}, e.t);
        ids.forEach(i => acesos.add(i));
        const jaAcesos = new Set(ev.filter(x => x.tipo === 'acende' && x.t < e.t).flatMap(x => todos.filter(i => cads[i].grupo === x.id)));
        const resto = g.resto_apaga === false ? [] : todos.filter(i => !ids.includes(i) && acesos.has(i) && !jaAcesos.has(i));
        if (resto.length) tl.to(sels('v', resto), {opacity: VEU, duration: .3}, e.t);
        resto.forEach(i => acesos.delete(i)); nomes(resto, e.t, false); nomes(ids, e.t, true);
        tl.fromTo(sels('s', ids), {scale: 1}, {scale: 1.04, transformOrigin: '50% 50%', duration: .18, yoyo: true, repeat: 1, stagger: .04, immediateRender: false}, e.t + .05);
        if (T.som) T.som('pop', e.t);
      } else {
        tl.to(sels('v', ids), {opacity: VEU, duration: .3}, e.t);
        ids.forEach(i => acesos.delete(i)); nomes(ids, e.t, false);
        tl.fromTo(sels('s', ids), {x: 0}, {x: 7, duration: .06, yoyo: true, repeat: 5, ease: 'sine.inOut', immediateRender: false}, e.t + .05);
      }
    }
    if (o.centro) {
      const tc = o.centro.t != null ? +o.centro.t : (ev.length ? ev[ev.length - 1].t : ini + .6);
      tl.fromTo(`.${k}m`, {opacity: 0, scale: .4, transformOrigin: '50% 50%'}, {opacity: 1, scale: 1, transformOrigin: '50% 50%', duration: .35, ease: 'back.out(2)'}, tc);
    }
    if (fim != null) tl.to(raiz, {opacity: 0, duration: .25}, fim);
    return raiz;
  }

  window.Plenario = {por, STF, semicirculo};
})();
