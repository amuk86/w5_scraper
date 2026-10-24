"""Entry point for the polite scraper. Run:  python src/main.py <command>"""
import argparse
import sys

import config

COMMANDS = {}


def command(name):
    def register(fn):
        COMMANDS[name] = fn
        return fn
    return register


@command("robots")
def cmd_robots(args):
    """Stage 0 - one request to robots.txt, result saved to output/robots-check.json."""
    from robots_check import check_robots
    result = check_robots(args.base_url)
    print(f"robots.txt -> status={result['status']}  {result['note']}")


@command("fetch")
def cmd_fetch(args):
    """Stage 1 - fetch catalogue page 1 (or read it from the cache)."""
    from fetcher import PoliteFetcher
    url = args.base_url.rstrip("/") + config.START_PATH
    result = PoliteFetcher().get(url)
    print(f"{'CACHE HIT' if result.from_cache else 'FETCH'}  {url}  {result.size} bytes")


# ---- add new commands above this line ----

def main(argv=None):
    parser = argparse.ArgumentParser(description="FlyRank A9 - the polite scraper")
    parser.add_argument("command", nargs="?", default=list(COMMANDS)[-1], choices=list(COMMANDS))
    parser.add_argument("--base-url", default=config.BASE_URL, help="target site (default: Books to Scrape)")
    args = parser.parse_args(argv)
    COMMANDS[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
