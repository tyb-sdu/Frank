"""Celery Worker entry point."""

from __future__ import annotations

import sys


def main():
    from .celery_app import celery_app
    argv = ["worker", "--loglevel=info", "-c", "2"]
    if len(sys.argv) > 1:
        argv = sys.argv[1:]
    celery_app.worker_main(argv)


if __name__ == "__main__":
    main()
