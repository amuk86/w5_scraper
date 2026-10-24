"""Run the mock site for manual CLI testing:  python tests/serve_mock.py  (port 8765)"""
import sys, time
from http.server import HTTPServer
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import mock_site
HTTPServer(("127.0.0.1", 8765), mock_site.Handler).serve_forever()
