#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from schwab_market_data import SchwabAuthError, get_schwab_provider


def print_json(value):
    print(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description="Test Charles Schwab Market Data API access.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("auth-url", help="Print the OAuth URL to open in a browser.")

    exchange = sub.add_parser("exchange-code", help="Exchange an OAuth authorization code for tokens.")
    exchange.add_argument("code", help="The code shown on the Schwab redirect page.")

    sub.add_parser("refresh", help="Refresh the access token using the stored refresh token.")

    quote = sub.add_parser("quote", help="Fetch quote data for one or more symbols.")
    quote.add_argument("symbols", nargs="+", help="Symbols such as AAPL MSFT QQQ.")
    quote.add_argument("--fields", default="quote,reference,regular", help="Schwab fields value.")

    history = sub.add_parser("history", help="Fetch price history for a symbol.")
    history.add_argument("symbol")
    history.add_argument("--period-type", default="day")
    history.add_argument("--period", type=int, default=10)
    history.add_argument("--frequency-type", default="minute")
    history.add_argument("--frequency", type=int, default=5)

    chain = sub.add_parser("chain", help="Fetch option chain data for a symbol.")
    chain.add_argument("symbol")
    chain.add_argument("--contract-type", choices=["CALL", "PUT", "ALL"], default=None)
    chain.add_argument("--strike-count", type=int, default=10)

    sub.add_parser("status", help="Show local Schwab config/token status.")

    args = parser.parse_args()
    provider = get_schwab_provider()

    try:
        if args.command == "auth-url":
            print(provider.get_authorization_url())
        elif args.command == "exchange-code":
            print_json(provider.exchange_code(args.code))
        elif args.command == "refresh":
            print_json(provider.refresh_access_token())
        elif args.command == "quote":
            print_json(provider.get_quotes(args.symbols, fields=args.fields))
        elif args.command == "history":
            print_json(
                provider.get_price_history(
                    args.symbol,
                    period_type=args.period_type,
                    period=args.period,
                    frequency_type=args.frequency_type,
                    frequency=args.frequency,
                )
            )
        elif args.command == "chain":
            print_json(
                provider.get_option_chain(
                    args.symbol,
                    contractType=args.contract_type,
                    strikeCount=args.strike_count,
                )
            )
        elif args.command == "status":
            print_json(provider.status())
    except SchwabAuthError as exc:
        print(f"Auth error: {exc}", file=sys.stderr)
        sys.exit(2)
    except Exception as exc:
        print(f"Schwab test failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
