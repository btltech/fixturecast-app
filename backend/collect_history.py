import os
import sys

try:
    from .collect_all_leagues import main as collect_all_leagues_main
except ImportError:
    from collect_all_leagues import main as collect_all_leagues_main

LEAGUE_ID = int(os.environ.get("LEAGUE_ID", "39"))


def collect_data():
    argv = sys.argv[:1] + [str(LEAGUE_ID)]
    original_argv = sys.argv
    try:
        sys.argv = argv
        collect_all_leagues_main()
    finally:
        sys.argv = original_argv


if __name__ == "__main__":
    collect_data()
