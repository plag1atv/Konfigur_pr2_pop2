from dependencies import get_dependencies, get_dependencies_from_file
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
        # Проверяем, является ли repo файлом (тестовый режим)
        if args.repo.endswith('.txt'):
            deps_graph = get_dependencies_from_file(args.repo, args.package_name, args.version, args.filter)
        else:
            deps_graph = get_dependencies(args.repo, args.package_name, args.version, args.filter)

        if deps_graph:
            print(f"\nГраф зависимостей для {args.package_name}-{args.version}:")
            for package, dependencies in deps_graph.items():
                print(f"  {package} -> {dependencies}")

            # Сохраняем в файл
            with open(args.output_file, 'w') as f:
                for package, dependencies in deps_graph.items():
                    f.write(f"{package}: {', '.join(dependencies)}\n")
            print(f"\nРезультат сохранен в {args.output_file}")
        else:
            print("Зависимостей не найдено.")
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()