from dependencies import get_dependencies
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="CLI-приложение для анализа зависимостей APK.")
    parser.add_argument("--package-name", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--filter", required=False, default="")

    args = parser.parse_args()

    print("\n=== Настройки приложения ===")
    for key, value in vars(args).items():
        print(f"{key} = {value}")
    print("=============================\n")

    try:
        deps = get_dependencies(args.repo, args.package_name, args.version)
        if deps:
            print(f"Зависимости для {args.package_name}-{args.version}:")
            for dep in deps:
                print(f"  - {dep}")
        else:
            print("Зависимостей не найдено.")
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()