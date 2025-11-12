from dependencies import get_dependencies, build_dependency_graph
import argparse
import sys
import json


def main():
    parser = argparse.ArgumentParser(description="CLI-приложение для анализа зависимостей APK.")
    parser.add_argument("--package-name", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--mode", required=True, help="Режим работы: real или test")
    parser.add_argument("--version", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--filter", required=False, default="")

    args = parser.parse_args()

    print("\n=== Настройки приложения ===")
    for key, value in vars(args).items():
        print(f"{key} = {value}")
    print("=============================\n")

    try:
        print("Построение графа зависимостей...\n")
        graph = build_dependency_graph(
            repo_source=args.repo,
            package=args.package_name,
            version=args.version,
            mode=args.mode,
            exclude_substring=args.filter
        )

        print("Граф зависимостей (в формате JSON):")
        print(json.dumps(graph, indent=4, ensure_ascii=False))

        with open(args.output_file, "w", encoding="utf-8") as f:
            json.dump(graph, f, indent=4, ensure_ascii=False)

        print(f"\nГраф сохранён в файл: {args.output_file}")

    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
