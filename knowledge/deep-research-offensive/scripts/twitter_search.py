#!/usr/bin/env python3
"""
twitter_search.py — X/Twitter search via twikit 2.x

Usage examples:
  # First run: login with username + password, save cookies for future runs
  python twitter_search.py "CVE-2024-12345 PoC exploit" \
      --auth-info-1 your_username --password yourpassword \
      --cookies-file cookies.json

  # Recommended: also provide email as second auth factor
  python twitter_search.py "CVE-2024-12345 PoC exploit" \
      --auth-info-1 your_username --auth-info-2 you@example.com \
      --password yourpassword --cookies-file cookies.json

  # Subsequent runs: cookies file exists, login is skipped automatically
  python twitter_search.py "CVE-2024-12345 PoC exploit" \
      --cookies-file cookies.json

  # Fully filtered: date range, min likes, Latest mode, JSON output
  python twitter_search.py "nmap red team" --cookies-file cookies.json \
      --mode Latest --count 20 --pages 3 \
      --since 2025-01-01 --until 2026-02-18 \
      --min-likes 5 --json -o results.json

  # Search tweets from a specific user
  python twitter_search.py "exploit" --cookies-file cookies.json \
      --from-user taviso --mode Latest

  # Fetch user profile only
  python twitter_search.py --user malwareunicorn --cookies-file cookies.json

  # With TOTP/2FA secret
  python twitter_search.py "malware" \
      --auth-info-1 your_username --password yourpassword \
      --totp-secret JBSWY3DPEHPK3PXP --cookies-file cookies.json

  # Paginate: get 3 pages of 20 results (up to 60 tweets)
  python twitter_search.py "CVE-2025" --cookies-file cookies.json \
      --count 20 --pages 3 --json -o all_results.json

Dependencies:
  pip install twikit

Notes:
  - Requires a real X/Twitter account. Guest mode is blocked by Cloudflare in twikit 2.x.
  - On first use: provide --auth-info-1 (username/phone) + --password.
    --cookies-file is passed directly to twikit login(), which handles load AND save.
  - Subsequent runs: only --cookies-file needed; session is reused without re-login.
  - With 2FA/TOTP: add --totp-secret (base32 TOTP secret string from your authenticator app).
  - Keep cookies.json secure — it provides full account access.
  - twikit max count per search_tweet() call: 20. Use --pages to paginate via .next().
  - Each result includes fxtwitter_url — use with Firecrawl extract to get full thread content.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional


def build_query(
    base: str,
    since: Optional[str] = None,
    until: Optional[str] = None,
    min_likes: Optional[int] = None,
    min_retweets: Optional[int] = None,
    from_user: Optional[str] = None,
    lang: Optional[str] = None,
    exclude_retweets: bool = True,
    exclude_replies: bool = True,
    only_links: bool = False,
) -> str:
    """Build a Twitter advanced search query string from structured parameters."""
    parts = [base.strip()]

    if since:
        parts.append(f"since:{since}")
    if until:
        parts.append(f"until:{until}")
    if min_likes and min_likes > 0:
        parts.append(f"min_faves:{min_likes}")
    if min_retweets and min_retweets > 0:
        parts.append(f"min_retweets:{min_retweets}")
    if from_user:
        parts.append(f"from:{from_user.lstrip('@')}")
    if lang:
        parts.append(f"lang:{lang}")
    if exclude_retweets:
        parts.append("-filter:nativeretweets")
    if exclude_replies:
        parts.append("-filter:replies")
    if only_links:
        parts.append("filter:links")

    return " ".join(parts)


def tweet_to_dict(tweet) -> dict:
    """Serialize a twikit Tweet object to a plain dict."""
    try:
        media_urls: list[str] = []
        if hasattr(tweet, "media") and tweet.media:
            for m in tweet.media:
                url = getattr(m, "media_url", None) or getattr(m, "url", None)
                if url:
                    media_urls.append(url)

        # twikit 2.x: tweet.text is primary; full_text is an alias (str | None)
        text = (
            getattr(tweet, "full_text", None)
            or getattr(tweet, "text", "")
            or ""
        )

        return {
            "id": tweet.id,
            "url": f"https://twitter.com/i/status/{tweet.id}",
            "fxtwitter_url": f"https://api.fxtwitter.com/status/{tweet.id}",
            "author": getattr(tweet.user, "screen_name", ""),
            "author_name": getattr(tweet.user, "name", ""),
            "author_followers": getattr(tweet.user, "followers_count", None),
            "created_at": str(getattr(tweet, "created_at", "")),
            "text": text,
            "likes": getattr(tweet, "favorite_count", 0),
            "retweets": getattr(tweet, "retweet_count", 0),
            "replies": getattr(tweet, "reply_count", 0),
            "views": getattr(tweet, "view_count", None),
            "lang": getattr(tweet, "lang", ""),
            "media": media_urls,
            "is_retweet": getattr(tweet, "retweeted_tweet", None) is not None,
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc), "raw": str(tweet)}


def print_tweet(t: dict, index: int) -> None:
    """Print a single tweet to stdout in a readable format."""
    print(f"\n[{index}] @{t['author']} ({t['author_name']}) — {t['created_at']}")
    print(f"    {t['text']}")
    print(
        f"    ♥ {t['likes']}  RT {t['retweets']}  💬 {t['replies']}"
        + (f"  👁 {t['views']}" if t["views"] else "")
        + ("  [RT]" if t["is_retweet"] else "")
    )
    if t["media"]:
        print(f"    Media: {', '.join(t['media'])}")
    print(f"    URL: {t['url']}")
    print(f"    FxTwitter: {t['fxtwitter_url']}")


async def _get_client(args: argparse.Namespace):
    """Initialize and authenticate a twikit Client.

    twikit 2.x login() signature:
        login(*, auth_info_1, auth_info_2=None, password,
              totp_secret=None, cookies_file=None, enable_ui_metrics=True)

    When cookies_file is provided to login(), twikit will:
      - Load the file if it already exists (skip re-login)
      - Save cookies to it after a fresh login
    """
    try:
        from twikit import Client  # type: ignore[import]
    except ImportError:
        print("ERROR: twikit is not installed. Run: pip install twikit", file=sys.stderr)
        sys.exit(1)

    client = Client(language="en-US")

    cookies_file: Optional[str] = getattr(args, "cookies_file", None)
    auth_info_1: Optional[str] = getattr(args, "auth_info_1", None)
    password: Optional[str] = getattr(args, "password", None)

    if auth_info_1 and password:
        # First run (or forced re-login): twikit login handles cookies_file load/save
        if not getattr(args, "quiet", False):
            print("Logging in...", file=sys.stderr)
        await client.login(
            auth_info_1=auth_info_1,
            auth_info_2=getattr(args, "auth_info_2", None),
            password=password,
            totp_secret=getattr(args, "totp_secret", None),
            cookies_file=cookies_file,  # None is fine; twikit handles it
        )
        if not getattr(args, "quiet", False):
            print("Login successful.", file=sys.stderr)

    elif cookies_file and Path(cookies_file).exists():
        # Session reuse: load existing cookies without touching the network
        client.load_cookies(cookies_file)
        if not getattr(args, "quiet", False):
            print(f"Session loaded from {cookies_file}", file=sys.stderr)

    else:
        print(
            "ERROR: No credentials or cookies found.\n"
            "       First run:        --auth-info-1 <user> --password <pass> --cookies-file cookies.json\n"
            "       Subsequent runs:  --cookies-file cookies.json",
            file=sys.stderr,
        )
        sys.exit(1)

    return client


async def search_tweets(args: argparse.Namespace) -> list[dict]:
    """Run the tweet search using twikit 2.x."""
    client = await _get_client(args)

    query = build_query(
        args.query,
        since=args.since,
        until=args.until,
        min_likes=args.min_likes,
        min_retweets=args.min_retweets,
        from_user=args.from_user,
        lang=args.lang,
        exclude_retweets=not args.include_retweets,
        exclude_replies=not args.include_replies,
        only_links=args.only_links,
    )

    pages: int = getattr(args, "pages", 1)

    if not args.quiet:
        print(f"Query: {query}", file=sys.stderr)
        print(f"Mode:  {args.mode} | Count: {args.count} | Pages: {pages}", file=sys.stderr)

    # twikit 2.x: search_tweet(query, product: 'Top'|'Latest'|'Media', count: int)
    # count is capped at 20 per call; paginate with result.next()
    results_page = await client.search_tweet(query, args.mode, count=args.count)
    all_results = [tweet_to_dict(t) for t in results_page]

    for page_num in range(2, pages + 1):
        if not args.quiet:
            print(f"Fetching page {page_num}...", file=sys.stderr)
        try:
            results_page = await results_page.next()
            if not results_page:
                break
            all_results.extend(tweet_to_dict(t) for t in results_page)
        except Exception as exc:  # noqa: BLE001
            if not args.quiet:
                print(f"Pagination stopped at page {page_num}: {exc}", file=sys.stderr)
            break

    return all_results


async def get_user(args: argparse.Namespace) -> dict:
    """Fetch a user profile by screen name."""
    client = await _get_client(args)
    # twikit 2.x: get_user_by_screen_name(screen_name: str) -> User
    user = await client.get_user_by_screen_name(args.user.lstrip("@"))

    return {
        "id": getattr(user, "id", ""),
        "screen_name": user.screen_name,
        "name": user.name,
        "description": getattr(user, "description", ""),
        "followers": getattr(user, "followers_count", None),
        "following": getattr(user, "following_count", None),
        "tweets": getattr(user, "statuses_count", None),
        "verified": getattr(user, "verified", False) or getattr(user, "is_blue_verified", False),
        "created_at": str(getattr(user, "created_at", "")),
        "profile_url": f"https://twitter.com/{user.screen_name}",
        "fxtwitter_url": f"https://api.fxtwitter.com/{user.screen_name}",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search X/Twitter via twikit 2.x — requires a real X account.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Target — mutually exclusive: search OR user lookup
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("query", nargs="?", help="Search query string")
    target.add_argument("--user", metavar="USERNAME",
                        help="Fetch user profile (no search)")

    # Authentication
    auth = parser.add_argument_group("authentication")
    auth.add_argument("--auth-info-1", metavar="USER/PHONE/EMAIL",
                      help="Username, phone, or email (required on first use)")
    auth.add_argument("--auth-info-2", metavar="EMAIL",
                      help="Second auth info — email recommended (optional but helps avoid challenges)")
    auth.add_argument("--password", metavar="PASS",
                      help="Account password (required on first use)")
    auth.add_argument("--totp-secret", metavar="SECRET",
                      help="Base32 TOTP secret string for 2FA accounts")
    auth.add_argument("--cookies-file", metavar="FILE", default="cookies.json",
                      help="Cookie file path — twikit auto load/save (default: cookies.json)")

    # Search controls
    search = parser.add_argument_group("search")
    search.add_argument("--mode", choices=["Latest", "Top", "Media"], default="Latest",
                        help="Result ordering (default: Latest)")
    search.add_argument("--count", type=int, default=20, metavar="N",
                        help="Results per page, twikit max is 20 (default: 20)")
    search.add_argument("--pages", type=int, default=1, metavar="N",
                        help="Number of pages to fetch via pagination (default: 1)")

    # Filters
    filters = parser.add_argument_group("filters")
    filters.add_argument("--since", metavar="YYYY-MM-DD", help="Start date (inclusive)")
    filters.add_argument("--until", metavar="YYYY-MM-DD", help="End date (inclusive)")
    filters.add_argument("--min-likes", type=int, default=0, metavar="N",
                         help="Minimum likes (default: 0)")
    filters.add_argument("--min-retweets", type=int, default=0, metavar="N",
                         help="Minimum retweets (default: 0)")
    filters.add_argument("--from-user", metavar="USERNAME",
                         help="Restrict to tweets from a specific user")
    filters.add_argument("--lang", metavar="CODE",
                         help="Language code filter (e.g. en, it, de)")
    filters.add_argument("--include-retweets", action="store_true",
                         help="Include native retweets (excluded by default)")
    filters.add_argument("--include-replies", action="store_true",
                         help="Include replies (excluded by default)")
    filters.add_argument("--only-links", action="store_true",
                         help="Only return tweets containing external links")

    # Output
    output = parser.add_argument_group("output")
    output.add_argument("--json", action="store_true", help="Output results as JSON")
    output.add_argument("-o", "--output", metavar="FILE",
                        help="Save JSON output to file (implies --json)")
    output.add_argument("-q", "--quiet", action="store_true",
                        help="Suppress progress messages")

    return parser.parse_args()


def _write_output(data: list | dict, args: argparse.Namespace) -> None:
    """Write JSON to file or stdout."""
    output = json.dumps(data, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        if not args.quiet:
            print(f"Saved to {args.output}", file=sys.stderr)
    else:
        print(output)


async def main() -> None:
    args = parse_args()

    # --output implies --json
    if args.output:
        args.json = True

    if args.user:
        data = await get_user(args)
        if not args.quiet:
            print(
                f"\n@{data['screen_name']} — {data['name']}\n"
                f"  Followers: {data['followers']}  Following: {data['following']}\n"
                f"  Bio: {data['description']}\n"
                f"  Profile:   {data['profile_url']}\n"
                f"  FxTwitter: {data['fxtwitter_url']}"
            )
        if args.json:
            _write_output(data, args)
        return

    results = await search_tweets(args)

    if not args.quiet:
        print(f"\nFound {len(results)} tweets total.", file=sys.stderr)

    if args.json:
        _write_output(results, args)
    else:
        for i, t in enumerate(results, 1):
            print_tweet(t, i)


if __name__ == "__main__":
    asyncio.run(main())
