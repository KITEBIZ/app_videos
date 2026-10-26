/* Fecho (estúdio v2, 19/10/2026; ele: "e o elemento final de fechamento"). O fim do vídeo com o desenho do #300:
   fundo com uma foto escurecida, PLACAR, o resultado, o pedido de mandar (caixa amarela), o 2º convite para seguir,
   a pergunta sozinha com RESPONDE NOS COMENTÁRIOS, e a assinatura; a pergunta fica até o logo começar a se montar e
   some antes das cadeiras acenderem (nada de texto por cima do logo, conserto do 3º teste).

   T.fecho(o) → o fim do vídeo (o da assinatura)
     o.t: começo do fecho (o início do bloco do placar)
     o.fundo: {src, recorte, tam} foto atrás de tudo, escurecida (opcional)
     o.placar: um destes dois:
       {contagem: 'auto'} (PADRÃO do formato Fomos conferir, regra 7: o placar bate com os carimbos) conta os selos que o
         vídeo usou (T.selo e T.carimbos), uma linha por veredito, na cor do Verdadômetro: "2 · VERDADE", "2 · SEM PROVA";
         ou {contagem: [['VERDADE', 2], ['SEM PROVA', 2]]} na mão. tLinhas: instantes de cada linha (padrão: a cada 0,6 s)
       {frase: 'TUDO O QUE ELA FALOU', resultado: 'É VERDADE', veredito: 'VERDADE', tFrase, tResultado} (o do #300)
     o.manda: {t, linhas: ['MANDA PARA QUEM', 'AINDA ESTÁ EM DÚVIDA']} · o.seguir: instante do 2º convite (T.seguir)
     o.pergunta: {t, linhas: ['VOCÊ CONFIA EM QUEM NEGA', 'O QUE <b>FOTOS E VÍDEOS</b>', 'COMPROVAM?']}: a última linha
       vem grande e amarela; <b> fica amarelo
     o.assinatura: o instante da assinatura (padrão: o fim da voz + 0,2); false para não chamar */
(function () {
  const NS = 'http://www.w3.org/2000/svg';
  const amarelo = s => String(s).replace(/<b>(.*?)<\/b>/g, '<tspan fill="#ffc933">$1</tspan>');
  // 22/10/2026 (editor-327; #327: "...O VÍDEO DA <b>JANDIRA</b>" sumiu, amarelo na caixa amarela): dentro da caixa do
  // pedido o destaque é sublinhado no azul do texto, nunca amarelo
  const destaqueNaCaixa = s => String(s).replace(/<b>(.*?)<\/b>/g, '<tspan text-decoration="underline">$1</tspan>');

  const tr = s => (window.T && window.T.t ? window.T.t(s) : s);   // idioma-do-video: o texto fixo no idioma do vídeo
  function placar(o, VER) {
    const p = o.placar || {contagem: 'auto'};
    let h = `<text class="im fecho-titulo" x="480" y="400" text-anchor="middle" font-size="120" fill="#F4F6FF">${tr('PLACAR')}</text>`;
    const partes = [];
    if (p.frase) {
      const cor = (VER[p.veredito || 'VERDADE'] || ['#3ddc84'])[0];
      h += `<g class="fecho-frase" opacity="0"><text class="im" x="480" y="540" text-anchor="middle" font-size="80" fill="#F4F6FF">${amarelo(p.frase)}</text></g>`
        + `<g class="fecho-res" opacity="0"><rect x="110" y="590" width="740" height="180" rx="90" fill="#0a1748" stroke="${cor}" stroke-width="8"/>`
        + `<circle cx="210" cy="680" r="62" fill="${cor}"/><path d="M180 682 l22 24 l42 -48" fill="none" stroke="#0a1748" stroke-width="14" stroke-linecap="round" stroke-linejoin="round"/>`
        + `<text class="im" x="535" y="728" text-anchor="middle" font-size="130" fill="${cor}">${p.resultado || ''}</text></g>`;
      partes.push(['.fecho-frase', p.tFrase, '480 515'], ['.fecho-res', p.tResultado, '480 680']);
    } else {
      p.linhas.forEach(([palavra, n], i) => {
        const cor = (VER[palavra] || ['#F4F6FF'])[0], y = 470 + i * 120;
        h += `<g class="fecho-l${i}" opacity="0"><rect x="110" y="${y}" width="740" height="100" rx="50" fill="#0a1748" stroke="${cor}" stroke-width="6"/>`
          + `<text class="im" x="480" y="${y + 76}" text-anchor="middle" font-size="76" fill="${cor}">${n} · ${tr(palavra)}</text></g>`;
        partes.push([`.fecho-l${i}`, p.tLinhas ? p.tLinhas[i] : null, `480 ${y + 50}`]);
      });
    }
    return {html: h, partes, fimPlacar: p.frase ? 770 : 470 + p.linhas.length * 120 - 20};
  }

  function por(cena, tl, T, o) {
    const VER = (window.Verdadometro && window.Verdadometro.VEREDITOS) || {};
    const t = +o.t;
    if (o.placar && o.placar.contagem) {          // 'auto': os selos que o vídeo usou, na ordem em que apareceram
      const lista = o.placar.contagem === 'auto' ? (T.selos || []).map(s => s.palavra) : null;
      const conta = lista ? lista.reduce((m, w) => (m.set(w, (m.get(w) || 0) + 1), m), new Map()) : new Map(o.placar.contagem);
      o.placar.linhas = [...conta.entries()];
    } else if (!o.placar) o.placar = {linhas: [...(T.selos || []).reduce((m, s) => (m.set(s.palavra, (m.get(s.palavra) || 0) + 1), m), new Map()).entries()]};
    // 19/10/2026 (ele: "o placar tem que entrar na ordem da fala"): sem tLinhas, cada linha entra na palavra dita
    // ("dois ERRADOS", "um EXAGERO"...) e a ordem é a da fala; a que não for dita fica no fim, no ritmo de antes
    if (o.placar && o.placar.linhas && !o.placar.tLinhas) {
      // a palavra dita, também em espanhol e inglês (idioma-do-video): "prueba", "erróneo", "true", "wrong"...
      const CHAVE = {'VERDADE': /^(verdad|true)/, 'ERRADO': /^(errad|errone|wrong)/, 'FALSO': /^(fals)/, 'EXAGERO': /^(exager|exagg)/,
                     'SEM PROVA': /^(prova|prueba|evidence)/, 'MEIA-VERDADE': /^(meia|media|half)/, 'CONFIRMADO': /^confirm/,
                     'PREVISÃO': /^(previs|predict)/, 'OPINIÃO': /^(opini)/};
      const ate = (o.manda && o.manda.t) || (o.pergunta && o.pergunta.t) || t + 15;
      const ws = (T.palavras || []).filter(w => w[0] >= t - .3 && w[0] < ate);
      const norm = x => String(x).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z]/g, '');
      const quando = p => { const re = CHAVE[p]; const w = re && ws.find(w => re.test(norm(w[2]))); return w ? w[0] : null; };
      const comTempo = o.placar.linhas.map((l, i) => ({l, i, t: quando(l[0])}));
      comTempo.sort((x, y) => (x.t ?? 1e9) - (y.t ?? 1e9) || x.i - y.i);
      let ultimo = t + .6;
      o.placar.linhas = comTempo.map(x => x.l);
      o.placar.tLinhas = comTempo.map(x => (ultimo = x.t != null ? x.t : ultimo + .6));
    }
    const pl = placar(o, VER);
    const pg = o.pergunta;
    // 22/10/2026 (editor-327, ensaio do #327): com pergunta, o placar some quando ela entra; o pedido de mandar ficava
    // DENTRO do grupo do placar e sumia junto (nunca aparecia). Agora ele é um grupo próprio: sem pergunta, embaixo do
    // placar, como antes; com pergunta, embaixo da pergunta
    const yManda = pg ? 610 + (pg.linhas.length - 1) * 100 + 60 + 70 : pl.fimPlacar + 85;
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('width', 1080); svg.setAttribute('height', 1920); svg.setAttribute('viewBox', '0 0 1080 1920');
    svg.style.cssText = 'position:absolute;inset:0'; svg.setAttribute('class', 'peca-fecho');
    const f = o.fundo;
    svg.innerHTML = (f ? `<g class="fecho-fundo" opacity="0"><svg x="0" y="0" width="1080" height="1920" viewBox="${f.recorte || `0 0 ${(f.tam || [540, 960]).join(' ')}`}" preserveAspectRatio="xMidYMid slice"><image href="${f.src}" width="${(f.tam || [540, 960])[0]}" height="${(f.tam || [540, 960])[1]}"/></svg>`
        + `<rect x="0" y="0" width="1080" height="1920" fill="#0a1748" fill-opacity=".8"/></g>` : '')
      + `<g class="fecho-placar" opacity="0">${pl.html}</g>`;
    const linhasManda = o.manda ? (o.manda.linhas || [tr('MANDA PARA QUEM'), tr('AINDA ESTÁ EM DÚVIDA')]) : [];
    const mandaHtml = o.manda ? `<g class="fecho-manda" opacity="0"><rect x="90" y="${yManda}" width="780" height="${46 + linhasManda.length * 54}" rx="26" fill="#ffc933"/>`
      + linhasManda.map((l, i) => `<text x="480" y="${yManda + 63 + i * 54}" text-anchor="middle" font-size="44" font-weight="900" fill="#0a1748">${destaqueNaCaixa(l)}</text>`).join('')
      + `</g>` : '';
    // a linha da pergunta encolhe para caber (Impact: ~0,45 da letra por caractere; até 800 px em volta do x 480, já
    // contando o crescimento de 4%): "PROVA DE QUE É DE PROPÓSITO?" a 70 px saía de x 30 a 930 no ensaio do #327
    const cabe = (l, max) => Math.min(max, Math.floor(800 / (0.45 * Math.max(1, String(l).replace(/<[^>]+>/g, '').length))));
    const pergunta = ls => `<g class="fecho-perg" opacity="0"><rect x="200" y="400" width="560" height="70" rx="35" fill="#ffc933"/>`
      + `<text x="480" y="447" text-anchor="middle" font-size="32" font-weight="900" fill="#0a1748">${tr('RESPONDE NOS COMENTÁRIOS')}</text>`
      + ls.map((l, i) => i === ls.length - 1
        ? `<text class="im" x="480" y="${610 + i * 100 + 60}" text-anchor="middle" font-size="${cabe(l, 140)}" fill="#ffc933">${amarelo(l)}</text>`
        : `<text class="im" x="480" y="${610 + i * 100}" text-anchor="middle" font-size="${cabe(l, 70)}" fill="#F4F6FF">${amarelo(l)}</text>`).join('') + `</g>`;
    if (pg) svg.insertAdjacentHTML('beforeend', pergunta(pg.linhas));
    if (mandaHtml) svg.insertAdjacentHTML('beforeend', mandaHtml);
    cena.appendChild(svg);
    const q = s => svg.querySelector(s);
    const entra = (el, tt, origem, de = .8, o2 = {}) => tl.fromTo(el, {opacity: 0, scale: de, svgOrigin: origem},
      {opacity: 1, scale: 1, svgOrigin: origem, duration: o2.dur ?? .35, ease: o2.ease ?? 'back.out(1.8)'}, tt);
    if (f) {
      tl.to(q('.fecho-fundo'), {opacity: 1, duration: .4}, t - .1);
      tl.fromTo(q('.fecho-fundo'), {scale: 1, svgOrigin: '540 760'}, {scale: 1.06, svgOrigin: '540 760', duration: 9, ease: 'none'}, t - .1);
    }
    tl.to(q('.fecho-placar'), {opacity: 1, duration: .2}, t - .05);
    tl.fromTo(q('.fecho-titulo'), {scale: 1.3, svgOrigin: '480 360'}, {scale: 1, svgOrigin: '480 360', duration: .35, ease: 'power3.out'}, T.som('impact-bass-2', t));
    pl.partes.forEach(([sel, tt, origem], i) => entra(q(sel), T.som('pop', tt ?? t + .6 + i * .6), origem, .6));
    if (o.seguir != null) T.seguir(o.seguir);
    if (o.manda) entra(q('.fecho-manda'), o.manda.t, `480 ${yManda + 75}`);
    if (pg) {
      tl.to(q('.fecho-placar'), {opacity: 0, duration: .25}, pg.t - .1);
      entra(q('.fecho-perg'), pg.t, '480 700', .9, {dur: .45, ease: 'power2.out'});
      tl.to(q('.fecho-perg'), {scale: 1.04, svgOrigin: '480 700', duration: 4, ease: 'none'}, pg.t + .45);
    }
    if (o.assinatura === false) return T.dur;
    // a assinatura apaga a cena de tAss - 0,2 a tAss e as cadeiras vazias começam a aparecer em tAss: a pergunta some
    // nesse apagão e termina de sumir quando elas começam (19/10/2026, print dele: as cadeiras apareciam por cima da
    // pergunta; o #300 a segurava até tAss + 0,4 para não ficar tela vazia)
    return T.assinatura(o.assinatura ?? T.dur + .2);
  }
  window.Fecho = {por};
})();
