"""A tiny local imitation of Books to Scrape (same HTML structure) for offline testing.

3 catalogue pages x 20 books. Book #7 has no description. Mirrors the real quirks:
relative links, a second price in the info table, whitespace inside tags, "£" in UTF-8.
"""
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

PER_PAGE, PAGES = 20, 3
RATINGS = ["One", "Two", "Three", "Four", "Five"]


def book(i):
    return {
        "i": i,
        "slug": f"mock-book-{i}_{1000 + i}",
        "title": f"Mock Book {i}",
        "price": f"£{10 + i}.{(i * 7) % 100:02d}",
        "stock": 5 + i,
        "rating": RATINGS[i % 5],
        "description": None if i == 7 else f"Description of mock book {i}. It's \"quoted\" & rich.",
    }


def catalogue_html(n):
    items = []
    for k in range(PER_PAGE):
        b = book((n - 1) * PER_PAGE + k + 1)
        items.append(f'<li class="col-xs-6"><article class="product_pod"><h3>'
                     f'<a href="{b["slug"]}/index.html" title="{b["title"]}">{b["title"][:12]}...</a></h3>'
                     f'<div class="product_price"><p class="price_color">{b["price"]}</p></div></article></li>')
    nxt = f'<li class="next"><a href="page-{n + 1}.html">next</a></li>' if n < PAGES else ""
    # a second page of real site also links "previous"; irrelevant here
    return (f'<html><body><section><ol class="row">{"".join(items)}</ol>'
            f'<ul class="pager"><li class="current">Page {n} of {PAGES}</li>{nxt}</ul></section></body></html>')


def product_html(b):
    desc = ("" if b["description"] is None else f'<p>{b["description"].replace("&", "&amp;")}</p>')
    return f'''<html><body><article class="product_page"><div class="row">
<div class="col-sm-6 product_main">
<h1>{b["title"]}</h1>
<p class="price_color">{b["price"]}</p>
<p class="instock availability">
    <i class="icon-ok"></i>

        In stock ({b["stock"]} available)

</p>
<p class="star-rating {b["rating"]}"><i class="icon-star"></i></p>
</div></div>
<div id="product_description" class="sub_header"><h2>Product Description</h2></div>{desc}
<table class="table table-striped"><tr><th>Price (incl. tax)</th><td>£99.99</td></tr></table>
</article></body></html>'''


class Handler(BaseHTTPRequestHandler):
    log = []          # every request path, so tests can count traffic
    flaky = {}        # path -> remaining 500 responses

    def log_message(self, *a):
        pass

    def _send(self, code, body=b"", ctype="text/html; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        Handler.log.append((self.path, self.headers.get("User-Agent")))
        p = self.path
        if Handler.flaky.get(p, 0) > 0:
            Handler.flaky[p] -= 1
            return self._send(500)
        if p.startswith("/catalogue/page-") and p.endswith(".html"):
            n = int(p[len("/catalogue/page-"):-5])
            if 1 <= n <= PAGES:
                return self._send(200, catalogue_html(n).encode("utf-8"))
        elif p.startswith("/catalogue/mock-book-") and p.endswith("/index.html"):
            i = int(p.split("/")[2].split("_")[0].replace("mock-book-", ""))
            if 1 <= i <= PER_PAGE * PAGES:
                return self._send(200, product_html(book(i)).encode("utf-8"))
        self._send(404, b"not found")


def start():
    Handler.log, Handler.flaky = [], {}
    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"
