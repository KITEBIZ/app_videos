import sys
from playwright.sync_api import sync_playwright
NOVA = open(sys.argv[1]).read()
MEDE = """() => { const m = document.querySelector('#meio').getBoundingClientRect(), g = document.querySelector('#msgs').getBoundingClientRect(), a = document.querySelector('#alca');
  const vis = [...document.querySelectorAll('#meio .bloco-no > summary')].filter(b => { const x = b.getBoundingClientRect(); return x.top >= m.top - 2 && x.bottom <= m.bottom + 2 }).length;
  const cx = document.querySelector('#caixa').getBoundingClientRect();
  return {roteiro_px: Math.round(m.height), mensagens_px: Math.round(g.height), blocos_a_vista: vis + ' de ' + document.querySelectorAll('.bloco-no').length,
          alca_visivel: !!a.getClientRects().length, caixa_a_vista: cx.bottom <= innerHeight} }"""
erros = []
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    pg = ctx.new_page(); pg.on("pageerror", lambda e: erros.append(str(e)))
    ctx.route(lambda u: u.split("#")[0].rstrip("/").endswith(":4400"), lambda r: r.fulfill(status=200, content_type="text/html; charset=utf-8", body=NOVA))
    pg.goto("http://127.0.0.1:4400/#/item/327"); pg.wait_for_timeout(4500)
    print("1 padrão          ", pg.evaluate(MEDE)); pg.screenshot(path="alca-1.png")
    a = pg.locator("#alca").bounding_box(); x, y = a["x"] + a["width"] / 2, a["y"] + a["height"] / 2
    pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x, y - 120, steps=8); pg.mouse.up(); pg.wait_for_timeout(400)
    print("2 arrastou p/ cima", pg.evaluate(MEDE)); pg.screenshot(path="alca-2.png")
    a = pg.locator("#alca").bounding_box(); y = a["y"] + a["height"] / 2
    pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x, y + 900, steps=8); pg.mouse.up(); pg.wait_for_timeout(400)
    print("3 arrastou p/ baixo até o limite", pg.evaluate(MEDE))
    pg.reload(); pg.wait_for_timeout(4500)
    print("4 recarregou      ", pg.evaluate(MEDE))
    pg.tap("#caixa"); pg.wait_for_timeout(400)
    print("5 escrevendo      ", pg.evaluate("() => ({alca_visivel: !!document.querySelector('#alca').getClientRects().length})"))
    pg2 = b.new_page(viewport={"width": 1440, "height": 900})
    pg2.route(lambda u: u.split("#")[0].rstrip("/").endswith(":4400"), lambda r: r.fulfill(status=200, content_type="text/html; charset=utf-8", body=NOVA))
    pg2.goto("http://127.0.0.1:4400/#/item/327"); pg2.wait_for_timeout(4000)
    print("6 computador      ", pg2.evaluate("() => ({alca_visivel: !!document.querySelector('#alca').getClientRects().length, grade: getComputedStyle(document.querySelector('#app')).display})"))
    b.close()
print("erros de JavaScript:", erros or "nenhum")
