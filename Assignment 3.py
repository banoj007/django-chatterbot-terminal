"""
Hands-On Assignment 3: Create a Simple Q&A Chatbot with Python (Terminal Client)
Course: Advance Artificial Intelligence — Bi-Term 1

File: chatbot_terminal.py
Purpose:
- Run a simple terminal-based chatbot using Django + ChatterBot.
- Uses a local SQLite database to persist conversations.

How to run (after installing packages):
1) (Recommended) Create a virtual environment
2) Install dependencies:
   pip install django chatterbot chatterbot-corpus

3) Run:
   python chatbot_terminal.py

Notes:
- ChatterBot has had version compatibility issues across Python versions.
  If you hit install/runtime errors, try pinning versions (example):
    pip install "Django<4" "chatterbot==1.0.8" "chatterbot-corpus==1.2.0"
- This script configures Django programmatically, so you do NOT need to create
  a full Django project for a terminal client. (Still satisfies “using Django/Python”.)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Optional

# ----------------------------
# Logging setup
# ----------------------------
LOGGER = logging.getLogger("chatbot_terminal")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


def configure_django(db_path: str) -> None:
    """
    Configure minimal Django settings in-code so we can use ChatterBot's
    Django storage adapter in a terminal app.
    """
    # Importing Django only after args are parsed is fine,
    # but importing here keeps the logic contained.
    from django.conf import settings

    if settings.configured:
        return

    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

    settings.configure(
        DEBUG=False,
        SECRET_KEY="chatterbot-terminal-client-secret-key",
        INSTALLED_APPS=(
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "chatterbot.ext.django_chatterbot",
        ),
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": db_path,
            }
        },
        TIME_ZONE="UTC",
        USE_TZ=True,
    )

    import django  # noqa: WPS433 (allowed here)
    django.setup()


def migrate_database() -> None:
    """
    Ensure required DB tables exist. We run migrations programmatically
    (no need for manage.py in this terminal-only assignment).
    """
    from django.core.management import call_command

    # Create tables if not present. interactive=False avoids prompts.
    call_command("migrate", interactive=False, run_syncdb=True, verbosity=0)


def build_bot(bot_name: str, trainer: str, read_only: bool = False):
    """
    Create a ChatterBot instance backed by Django storage.
    """
    from chatterbot import ChatBot

    bot = ChatBot(
        bot_name,
        storage_adapter="chatterbot.storage.DjangoStorageAdapter",
        read_only=read_only,
        # You can adjust logic adapters if you want different behavior.
        # Default logic adapters generally work fine for a simple assignment.
    )

    # Optional training setup:
    if not read_only:
        train_bot(bot, trainer)

    return bot


def train_bot(bot, trainer: str) -> None:
    """
    Train the bot using either:
    - "corpus": chatterbot-corpus (English greetings/conversations)
    - "list": small built-in list trainer for predictable responses
    - "none": skip training
    """
    trainer = trainer.lower().strip()

    if trainer == "none":
        LOGGER.info("Skipping training (trainer=none).")
        return

    if trainer == "corpus":
        try:
            from chatterbot.trainers import ChatterBotCorpusTrainer

            bot_trainer = ChatterBotCorpusTrainer(bot)
            LOGGER.info("Training with ChatterBot corpus (this may take a moment)...")
            bot_trainer.train(
                "chatterbot.corpus.english.greetings",
                "chatterbot.corpus.english.conversations",
            )
            LOGGER.info("Corpus training complete.")
            return
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Corpus training failed: %s", exc)
            LOGGER.warning("Falling back to list training.")

    if trainer in {"list", "corpus"}:
        from chatterbot.trainers import ListTrainer

        bot_trainer = ListTrainer(bot)
        LOGGER.info("Training with a small built-in conversation list...")
        bot_trainer.train(
            [
                "Good morning! How are you doing?",
                "I am doing very well, thank you for asking.",
                "You're welcome.",
                "Do you like hats?",
                "Sometimes. What kind of hats do you like?",
                "I like caps.",
                "Caps are cool! 😄",
                "What is your name?",
                f"My name is {getattr(bot, 'name', 'ChatBot')}.",
                "Bye",
                "Goodbye! Have a great day!",
            ]
        )
        LOGGER.info("List training complete.")
        return

    raise ValueError("Invalid trainer. Use: corpus, list, or none.")


def chat_loop(bot, exit_word: str = "exit") -> None:
    """
    Terminal I/O loop for chatting with the bot.
    """
    print("\n" + "=" * 60)
    print(f"Chat started. Type '{exit_word}' (or Ctrl+C) to quit.")
    print("=" * 60 + "\n")

    while True:
        try:
            user_text = input("user: ").strip()
            if not user_text:
                continue

            if user_text.lower() == exit_word.lower():
                print("bot: Goodbye! 👋")
                break

            response = bot.get_response(user_text)
            print(f"bot: {response}")

        except KeyboardInterrupt:
            print("\nbot: Goodbye! 👋")
            break
        except EOFError:
            print("\nbot: Goodbye! 👋")
            break
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Unexpected error: %s", exc)
            print("bot: Sorry, something went wrong. Please try again.")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Terminal Q&A Chatbot using Django + ChatterBot"
    )
    parser.add_argument(
        "--db",
        default="data/chatterbot.sqlite3",
        help="Path to SQLite database file (default: data/chatterbot.sqlite3)",
    )
    parser.add_argument(
        "--name",
        default="SimpleBot",
        help="Bot name (default: SimpleBot)",
    )
    parser.add_argument(
        "--trainer",
        choices=["corpus", "list", "none"],
        default="corpus",
        help="Training method (default: corpus)",
    )
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Run bot in read-only mode (no learning/training).",
    )
    parser.add_argument(
        "--exit-word",
        default="exit",
        help="Word to exit chat (default: exit)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)

    # 1) Configure Django settings and DB
    configure_django(args.db)

    # 2) Create DB tables
    migrate_database()

    # 3) Create and (optionally) train bot
    bot = build_bot(args.name, trainer=args.trainer, read_only=args.read_only)

    # 4) Start chat
    chat_loop(bot, exit_word=args.exit_word)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
