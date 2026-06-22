from focusaway.config import load_config
from focusaway.server import FocusAwayApp


def main() -> None:
    app = FocusAwayApp(load_config())
    app.run()


if __name__ == "__main__":
    main()

