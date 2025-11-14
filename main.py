from dependencies import get_dependencies, get_dependencies_from_file, get_install_order, generate_mermaid_graph, \
    save_graph_as_png
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="CLI-приложение для анализа зависимостей APK.")
    parser.add_argument("--package-name", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--mode", required=True, choices=["graph", "install-order", "visualize"],
                        help="graph - вывод графа, install-order - порядок установки, visualize - визуализация")
    parser.add_argument("--version", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--filter", required=False, default="")
    parser.add_argument("--compare-with-apk", action="store_true",
                        help="Сравнить с реальным менеджером пакетов apk")
    parser.add_argument("--visualize-format", choices=["mermaid", "png", "both"], default="both",
                        help="Формат визуализации: mermaid, png или оба")

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
            if args.mode == "graph":
                print(f"\nГраф зависимостей для {args.package_name}-{args.version}:")
                for package, dependencies in deps_graph.items():
                    print(f"  {package} -> {dependencies}")

            elif args.mode == "install-order":
                install_order = get_install_order(deps_graph, args.package_name)
                print(f"\nПорядок установки зависимостей для {args.package_name}:")
                for i, package in enumerate(install_order, 1):
                    print(f"  {i}. {package}")

                # Сравнение с реальным менеджером пакетов
                if args.compare_with_apk and not args.repo.endswith('.txt'):
                    compare_with_apk(args.package_name, install_order)

            elif args.mode == "visualize":
                print(f"\nВизуализация графа зависимостей для {args.package_name}...")

                # Генерация Mermaid диаграммы
                if args.visualize_format in ["mermaid", "both"]:
                    mermaid_code = generate_mermaid_graph(deps_graph, args.package_name)
                    mermaid_file = args.output_file.replace('.png', '.mmd')
                    with open(mermaid_file, 'w') as f:
                        f.write(mermaid_code)
                    print(f"Mermaid диаграмма сохранена в {mermaid_file}")

                    # Вывод части кода для предпросмотра
                    print("\nПредпросмотр Mermaid диаграммы:")
                    lines = mermaid_code.split('\n')[:10]
                    for line in lines:
                        print(f"  {line}")
                    if len(mermaid_code.split('\n')) > 10:
                        print("")

                # Генерация PNG
                if args.visualize_format in ["png", "both"]:
                    png_file = args.output_file if args.output_file.endswith('.png') else args.output_file + '.png'
                    success = save_graph_as_png(deps_graph, args.package_name, png_file)
                    if success:
                        print(f"PNG изображение сохранено в {png_file}")
                    else:
                        print("Не удалось сгенерировать PNG изображение")

            # Сохраняем в файл (для режимов graph и install-order)
            if args.mode in ["graph", "install-order"]:
                with open(args.output_file, 'w') as f:
                    if args.mode == "graph":
                        for package, dependencies in deps_graph.items():
                            f.write(f"{package}: {', '.join(dependencies)}\n")
                    elif args.mode == "install-order":
                        f.write("Порядок установки:\n")
                        for i, package in enumerate(install_order, 1):
                            f.write(f"{i}. {package}\n")

                print(f"\nРезультат сохранен в {args.output_file}")

        else:
            print("Зависимостей не найдено.")
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def compare_with_apk(package_name, our_order):
    """Сравнивает наш порядок установки с реальным менеджером пакетов apk"""
    print(f"\nСравнение с реальным менеджером пакетов apk...")

    try:
        import subprocess
        # Получаем информацию о зависимостях через apk
        result = subprocess.run(['apk', 'info', '-R', package_name],
                                capture_output=True, text=True, check=True)

        apk_dependencies = []
        for line in result.stdout.split('\n'):
            if line.strip() and not line.startswith(package_name):
                # Извлекаем имя пакета (убираем версии)
                dep = line.split('-')[0] if '-' in line else line.strip()
                if dep and dep not in apk_dependencies:
                    apk_dependencies.append(dep)

        print("Зависимости, определенные apk:")
        for i, dep in enumerate(apk_dependencies, 1):
            print(f"  {i}. {dep}")

        print("\nСравнение порядков:")
        print("Наш порядок установки:")
        print(" -> ".join(our_order))

        print("Зависимости apk (порядок может отличаться):")
        print(" -> ".join(apk_dependencies))

        # Анализ расхождений
        our_set = set(our_order)
        apk_set = set(apk_dependencies)

        if our_set == apk_set:
            print("Оба метода нашли одинаковый набор зависимостей")
        else:
            print("Обнаружены расхождения в наборе зависимостей:")
            if our_set - apk_set:
                print(f"  Только в нашем анализе: {our_set - apk_set}")
            if apk_set - our_set:
                print(f"  Только в apk: {apk_set - our_set}")

    except subprocess.CalledProcessError:
        print("Не удалось получить информацию от apk (возможно, пакет не установлен)")
    except FileNotFoundError:
        print("Команда apk не найдена (требуется Alpine Linux или apk-tools)")


if __name__ == "__main__":
    main()