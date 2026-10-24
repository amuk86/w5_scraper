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


@command("discover")
def cmd_discover(args):
    """Stage 2 - walk the first three catalogue pages and list the book URLs."""
    from fetcher import PoliteFetcher
    from pipeline import discover
    start = args.base_url.rstrip("/") + config.START_PATH
    fetcher = PoliteFetcher()
    found = discover(fetcher, start)
    print(f"catalogue_pages={found.catalogue_pages}, discovered={found.discovered}, "
          f"unique_urls={len(found.urls)}  (cache hits: {fetcher.cache_hits}, real requests: {fetcher.network_fetches})")


@command("extract")
def cmd_extract(args):
    """Stage 3 - extract raw records from all book pages and print one."""
    import json
    from fetcher import PoliteFetcher
    from pipeline import discover, extract_all
    fetcher = PoliteFetcher()
    found = discover(fetcher, args.base_url.rstrip("/") + config.START_PATH)
    raws, failures = extract_all(fetcher, found.urls, found.source_page)
    print(json.dumps(raws[0], indent=2, ensure_ascii=False))
    print(f"detail_pages={len(raws)}  failed={len(failures)}")


@command("run")
def cmd_run(args):
    """Stages 2-5 - the whole pipeline: books.json, errors.json, run-report.json."""
    import pipeline
    from fetcher import PoliteFetcher
    pipeline.run(args.base_url, fetcher=PoliteFetcher(delay=args.delay), extra_urls=args.extra_url)


# ---- add new commands above this line ----

def main(argv=None):
    parser = argparse.ArgumentParser(description="FlyRank A9 - the polite scraper")
    parser.add_argument("command", nargs="?", default=list(COMMANDS)[-1], choices=list(COMMANDS))
    parser.add_argument("--base-url", default=config.BASE_URL, help="target site (default: Books to Scrape)")
    parser.add_argument("--delay", type=float, default=config.MIN_DELAY_SECONDS,
                        help=f"seconds between real requests (minimum {config.MIN_DELAY_SECONDS})")
    parser.add_argument("--extra-url", action="append", default=[], metavar="URL",
                        help="add a URL to the list (use a made-up one to test failure handling)")
    args = parser.parse_args(argv)
    if args.delay < config.MIN_DELAY_SECONDS:
        parser.error(f"--delay must be at least {config.MIN_DELAY_SECONDS} seconds - be polite")
    COMMANDS[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
