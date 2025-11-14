import tarfile
import tempfile
import urllib.request
import os
from collections import deque, defaultdict
import subprocess
import tempfile


def download_apkindex(repo_url):
    """Скачивает APKINDEX.tar.gz из заданного репозитория"""
    if not repo_url.endswith("/"):
        repo_url += "/"
    arch = "x86_64"
    apkindex_url = f"{repo_url}/{arch}/APKINDEX.tar.gz"

    print(f"Скачивает {apkindex_url}")
    tmp_path = tempfile.mktemp(suffix=".tar.gz")

    try:
        urllib.request.urlretrieve(apkindex_url, tmp_path)
        print("Файл успешно скачан.")
    except Exception as e:
        raise RuntimeError(f"Ошибка при загрузке APKINDEX: {e}")

    return tmp_path


def extract_apkindex(filepath):
    """Извлекает содержимое файла APKINDEX из архива."""
    with tarfile.open(filepath, "r:gz") as tar:
        for member in tar.getmembers():
            if member.name == "APKINDEX":
                f = tar.extractfile(member)
                if f is None:
                    raise RuntimeError("Файл APKINDEX не найден в архиве.")
                data = f.read().decode("utf-8")
                return data
    raise RuntimeError("Файл APKINDEX не найден.")


def parse_dependencies(index_text, package_name, version):
    """Находит и возвращает список зависимостей пакета."""
    entries = index_text.split("\n\n")  # каждый пакет отделён пустой строкой
    for entry in entries:
        lines = entry.splitlines()
        pkg = None
        ver = None
        deps = []
        for line in lines:
            if line.startswith("P:"):
                pkg = line[2:].strip()
            elif line.startswith("V:"):
                ver = line[2:].strip()
            elif line.startswith("D:"):
                deps = line[2:].strip().split()
        if pkg == package_name and ver.startswith(version):
            return deps
    raise ValueError(f"Пакет '{package_name}' версии '{version}' не найден.")


def parse_all_packages(index_text):
    """Парсит все пакеты из APKINDEX и возвращает словарь"""
    packages = {}
    entries = index_text.split("\n\n")

    for entry in entries:
        if not entry.strip():
            continue
        lines = entry.splitlines()
        pkg = None
        deps = []
        for line in lines:
            if line.startswith("P:"):
                pkg = line[2:].strip()
            elif line.startswith("D:"):
                deps_str = line[2:].strip()
                deps = deps_str.split() if deps_str else []
        if pkg:
            packages[pkg] = deps

    return packages


def dfs_build_graph(package_name, version, all_packages, visited, graph, filter_str, current_path):
    """Рекурсивно строит граф зависимостей с помощью DFS"""

    # Проверка циклических зависимостей
    if package_name in current_path:
        print(f"Обнаружена циклическая зависимость: {' -> '.join(current_path)} -> {package_name}")
        return

    # Проверка фильтра
    if filter_str and filter_str in package_name:
        print(f"Пропущен пакет {package_name} (фильтр: {filter_str})")
        return

    # Если пакет уже посещен, возвращаем его зависимости из графа
    if package_name in visited:
        return

    visited.add(package_name)
    current_path.append(package_name)

    # Находим зависимости пакета
    dependencies = []
    if package_name in all_packages:
        dependencies = all_packages[package_name]

    # Очищаем зависимости от версий
    clean_deps = []
    for dep in dependencies:
        # Убираем версии и условия
        # Для простоты оставляем как есть, но можно добавить более сложную логику
        clean_dep = dep.split('>')[0].split('<')[0].split('=')[0]
        clean_deps.append(clean_dep)

    graph[package_name] = clean_deps

    # Рекурсивно обходим зависимости
    for dep in clean_deps:
        if dep in all_packages:  # Проверяем, существует ли пакет в репозитории
            dfs_build_graph(dep, "", all_packages, visited, graph, filter_str, current_path.copy())
        else:
            print(f"Пакет {dep} не найден в репозитории, пропускаем")

    current_path.pop()


def topological_sort(graph, start_package):
    """Топологическая сортировка графа зависимостей"""
    visited = set()
    temp_visited = set()
    order = []
    cycles = []

    def visit(node, path):
        if node in temp_visited:
            # Найден цикл
            cycle_start = path.index(node)
            cycle = path[cycle_start:] + [node]
            cycles.append(cycle)
            return
        if node in visited:
            return

        temp_visited.add(node)
        path.append(node)

        # Рекурсивно посещаем всех соседей
        for neighbor in graph.get(node, []):
            if neighbor in graph:  # Проверяем, что сосед существует в графе
                visit(neighbor, path.copy())

        temp_visited.remove(node)
        visited.add(node)
        order.append(node)

    # Начинаем обход с целевого пакета
    visit(start_package, [])

    # Выводим предупреждения о циклах
    for cycle in cycles:
        print(f"Обнаружен цикл: {' -> '.join(cycle)}")

    return order


def get_install_order(deps_graph, package_name):
    """Определяет порядок установки зависимостей"""
    print("Определяем порядок установки")

    # Создаем инвертированный граф для топологической сортировки
    inverted_graph = defaultdict(list)
    all_nodes = set()

    for node, deps in deps_graph.items():
        all_nodes.add(node)
        for dep in deps:
            if dep in deps_graph:  # Добавляем только существующие пакеты
                inverted_graph[dep].append(node)
                all_nodes.add(dep)

    # Топологическая сортировка
    install_order = topological_sort(deps_graph, package_name)

    # Переворачиваем порядок, чтобы зависимости шли перед пакетами, которые от них зависят
    install_order.reverse()

    # Убеждаемся, что целевой пакет идет последним
    if package_name in install_order:
        install_order.remove(package_name)
    install_order.append(package_name)

    print(f"Всего пакетов для установки: {len(install_order)}")
    return install_order


def get_dependencies(repo_url, package_name, version, filter_str=""):
    """Основная функция получения графа зависимостей"""
    print("Строим граф зависимостей")

    tmp_file = download_apkindex(repo_url)
    index_data = extract_apkindex(tmp_file)
    os.remove(tmp_file)

    # Парсим все пакеты
    all_packages = parse_all_packages(index_data)
    print(f"Загружено {len(all_packages)} пакетов из репозитория")

    # Строим граф с помощью DFS
    visited = set()
    graph = {}
    current_path = []

    dfs_build_graph(package_name, version, all_packages, visited, graph, filter_str, current_path)

    return graph


def get_dependencies_from_file(file_path, package_name, version, filter_str=""):
    """Режим тестирования - загрузка из файла"""
    print(f"Тестовый режим: загружаем из файла {file_path}")

    with open(file_path, 'r') as f:
        index_data = f.read()

    # Парсим все пакеты (формат как в APKINDEX)
    all_packages = parse_all_packages(index_data)
    print(f"Загружено {len(all_packages)} пакетов из тестового файла")

    # Строим граф с помощью DFS
    visited = set()
    graph = {}
    current_path = []

    dfs_build_graph(package_name, version, all_packages, visited, graph, filter_str, current_path)

    return graph


def generate_mermaid_graph(deps_graph, root_package):
    """Генерирует Mermaid диаграмму графа зависимостей"""

    mermaid_lines = [
        "%% Граф зависимостей для пакета: " + root_package,
        "graph TD",
    ]

    # Добавляем корневой пакет с особым стилем
    mermaid_lines.append(f"    {root_package}[{root_package}]")
    mermaid_lines.append(f"    style {root_package} fill:#ff6b6b,color:#fff")

    # Собираем все узлы и связи
    added_nodes = {root_package}

    for package, dependencies in deps_graph.items():
        if package not in added_nodes:
            mermaid_lines.append(f"    {package}[{package}]")
            added_nodes.add(package)

        for dep in dependencies:
            if dep not in added_nodes and dep in deps_graph:
                mermaid_lines.append(f"    {dep}[{dep}]")
                added_nodes.add(dep)

            if dep in deps_graph:  # Связываем только существующие пакеты
                mermaid_lines.append(f"    {package} --> {dep}")

    # Добавляем пакеты без зависимостей (листья)
    for package in deps_graph:
        if package not in added_nodes:
            mermaid_lines.append(f"    {package}[{package}]")
            added_nodes.add(package)

    mermaid_lines.append("")

    return "\n".join(mermaid_lines)


def save_graph_as_png(deps_graph, root_package, output_file):
    """Сохраняет граф зависимостей как PNG изображение используя Mermaid CLI"""

    try:
        # Генерируем Mermaid код
        mermaid_code = generate_mermaid_graph(deps_graph, root_package)

        # Создаем временный файл с Mermaid кодом
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as temp_file:
            temp_file.write(mermaid_code)
            temp_mmd_file = temp_file.name

        # Пытаемся использовать mermaid-cli для генерации PNG
        try:
            # Способ 1: mermaid-cli (mmdc)
            result = subprocess.run([
                'mmdc',
                '-i', temp_mmd_file,
                '-o', output_file,
                '-t', 'default',
                '-b', 'white',
                '-w', '1600',
                '-H', '1200'
            ], capture_output=True, text=True, check=True)

            print("PNG сгенерирован с помощью mermaid-cli")
            success = True

        except (subprocess.CalledProcessError, FileNotFoundError):
            # Способ 2: Попробуем использовать Python библиотеку
            try:
                import pygraphviz as pgv

                # Создаем граф с помощью pygraphviz
                graph = pgv.AGraph(directed=True)
                graph.node_attr.update(style='filled', fillcolor='lightblue', fontname='Arial')

                # Добавляем корневой узел с другим цветом
                graph.add_node(root_package, fillcolor='lightcoral')

                # Добавляем все узлы и связи
                for package, dependencies in deps_graph.items():
                    graph.add_node(package)
                    for dep in dependencies:
                        if dep in deps_graph:
                            graph.add_edge(package, dep)

                # Сохраняем как PNG
                graph.draw(output_file, prog='dot', format='png')
                print("PNG сгенерирован с помощью pygraphviz")
                success = True

            except ImportError:
                print("Для генерации PNG установите один из пакетов:")
                print("    - mermaid-cli: npm install -g @mermaid-js/mermaid-cli")
                print("    - pygraphviz: pip install pygraphviz")
                success = False

        # Удаляем временный файл
        os.unlink(temp_mmd_file)

        return success

    except Exception as e:
        print(f"Ошибка при генерации PNG: {e}")
        return False


def compare_with_apk_graph(package_name, deps_graph):
    """Сравнивает наш граф с выводом штатных инструментов apk"""
    print(f"\nСравнение графа с инструментами apk...")

    try:
        import subprocess

        # Получаем дерево зависимостей через apk
        result = subprocess.run(['apk', 'info', '-R', package_name],
                                capture_output=True, text=True, check=True)

        # Анализируем вывод apk
        apk_deps = set()
        for line in result.stdout.split('\n'):
            if line.strip() and not line.startswith(package_name):
                dep = line.split('-')[0] if '-' in line else line.strip()
                if dep:
                    apk_deps.add(dep)

        # Наш граф зависимостей
        our_deps = set(deps_graph.keys())
        our_deps.add(package_name)

        print(f"Наш анализ: {len(our_deps)} пакетов")
        print(f"APK анализ: {len(apk_deps)} пакетов")

        # Анализ расхождений
        only_our = our_deps - apk_deps
        only_apk = apk_deps - our_deps
        common = our_deps & apk_deps

        print(f"\nРезультаты сравнения:")
        print(f"Общие пакеты: {len(common)}")
        print(f"Только в нашем анализе: {len(only_our)}")
        print(f"Только в apk: {len(only_apk)}")

        if only_our:
            print(f"   Пакеты: {', '.join(sorted(only_our))}")
        if only_apk:
            print(f"   Пакеты: {', '.join(sorted(only_apk))}")

        # Возможные причины расхождений
        if only_our or only_apk:
            print(f"\nВозможные причины расхождений:")
            print("1. Разные алгоритмы разрешения зависимостей")
            print("2. Учет версий пакетов в apk")
            print("3. Влияние уже установленных пакетов")
            print("4. Обработка опциональных зависимостей")
            print("5. Различия в парсинге имен пакетов")

        return common, only_our, only_apk

    except subprocess.CalledProcessError as e:
        print(f"Ошибка при вызове apk: {e}")
        return set(), set(), set()
    except FileNotFoundError:
        print("Команда apk не найдена")
        return set(), set(), set()