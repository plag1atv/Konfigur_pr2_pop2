import tarfile
import tempfile
import urllib.request
import os


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


def get_dependencies(repo_url, package_name, version, filter_str=""):
    """Основная функция получения графа зависимостей"""
    print("Строим граф зависимостей...")

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

    # Парсим все пакеты
    all_packages = parse_all_packages(index_data)
    print(f"Загружено {len(all_packages)} пакетов из тестового файла")

    # Строим граф с помощью DFS
    visited = set()
    graph = {}
    current_path = []

    dfs_build_graph(package_name, version, all_packages, visited, graph, filter_str, current_path)

    return graph