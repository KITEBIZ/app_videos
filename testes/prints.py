"""Prints da v2 em tamanho de iPhone (390x844): python3 testes/prints.py <saida> <hash>..."""
import sys
from playwright.sync_api import sync_playwright
out = sys.argv[1]
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    for h in sys.argv[2:]:
        pg.goto("http://127.0.0.1:4400/" + h); pg.wait_for_timeout(2500)
        pg.screenshot(path=f"{out}/{h.strip('#/').replace('/', '-') or 'inicio'}.png")
    b.close()
