from .config import get_settings
from .repository import Repository


def main():
    repo = Repository(get_settings().sqlite_path)
    print(f"Seeded demo database: {repo.path}")


if __name__ == "__main__":
    main()

