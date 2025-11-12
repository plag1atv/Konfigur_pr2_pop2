import tarfile
import tempfile
import urllib.request
import os


def download_apkindex(repo_url):
    if not repo_url.endswith("/"):
        repo_url += "/"
    arch = "x86_64"
    apkindex_url = f"{repo_url}/{arch}/APKINDEX.tar.gz"

    print(f"Скачиваю {apkindex_url}")
    tmp_path = tempfile.mktemp(suffix=".tar.gz")

    try:
        urllib.request.urlretrieve(apkindex_url, tmp_path)
        print("Файл успешно скачан.")
    except Exception as e:
        raise RuntimeError(f"Ошибка при загрузке APKINDEX: {e}")

    return tmp_path


def extract_apkindex(filepath):
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
    entries = index_text.split("\n\n")
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


def get_dependencies(repo_url, package_name, version):
    tmp_file = download_apkindex(repo_url)
    index_data = extract_apkindex(tmp_file)
    os.remove(tmp_file)
    deps = parse_dependencies(index_data, package_name, version)
    return deps


# === Новый код для Этапа 3 ===
def parse_test_repo(file_path):
    """
    Парсит тестовый репозиторий.
    Формат файла: каждая строка вида
    A: B C D
    где A зависит от B, C, D.
    """
    repo = {}
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or ":" not in line:
                continue
            pkg, deps_str = line.split(":", 1)
            deps = deps_str.strip().split() if deps_str.strip() else []
            repo[pkg.strip()] = deps
    return repo


def build_dependency_graph(repo_source, package, version, mode="real", exclude_substring=""):
    """
    Строит граф зависимостей рекурсивно (DFS).
    Поддерживает режим 'test' для локальных текстовых файлов.
    """
    graph = {}
    visited = set()
    stack = set()

    def dfs(pkg):
        if exclude_substring and exclude_substring in pkg:
            return []

        if pkg in stack:
            print(f"⚠️ Обнаружен цикл в зависимостях: {pkg}")
            return []

        if pkg in visited:
            return graph.get(pkg, [])

        stack.add(pkg)
        visited.add(pkg)

        if mode == "test":
            deps = test_repo.get(pkg, [])
        else:
            try:
                deps = get_dependencies(repo_source, pkg, version)
            except Exception:
                deps = []

        deps = [d for d in deps if exclude_substring not in d]

        graph[pkg] = deps

        for dep in deps:
            dfs(dep)

        stack.remove(pkg)
        return deps

    if mode == "test":
        test_repo = parse_test_repo(repo_source)

    dfs(package)
    return graph
