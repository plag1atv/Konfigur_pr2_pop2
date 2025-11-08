import tarfile
import tempfile
import urllib.request
import os


def download_apkindex(repo_url):
    #Скачивает APKINDEX.tar.gz из заданного репозитория
    if not repo_url.endswith("/"):
        repo_url += "/"
    arch = "x86_64"
    apkindex_url = f"{repo_url}/{arch}/APKINDEX.tar.gz"

    print(f"Скачиваю {apkindex_url} ...")
    tmp_path = tempfile.mktemp(suffix=".tar.gz")

    try:
        urllib.request.urlretrieve(apkindex_url, tmp_path)
        print("Файл успешно скачан.")
    except Exception as e:
        raise RuntimeError(f"Ошибка при загрузке APKINDEX: {e}")

    return tmp_path


def extract_apkindex(filepath):
    #Извлекает содержимое файла APKINDEX из архива."""
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
    #Находит и возвращает список зависимостей пакета."""
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


def get_dependencies(repo_url, package_name, version):
    #Основная функция получения зависимостей.
    tmp_file = download_apkindex(repo_url)
    index_data = extract_apkindex(tmp_file)
    os.remove(tmp_file)
    deps = parse_dependencies(index_data, package_name, version)
    return deps
