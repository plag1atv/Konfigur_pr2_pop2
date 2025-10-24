import argparse
import os
import re
import sys
from urllib.parse import urlparse


def validate_url_or_path(value):
    #Проверка, что значение — это корректный URL или существующий путь
    parsed = urlparse(value)
    if parsed.scheme in ('http', 'https', 'git'):
        return value
    if os.path.exists(value):
        return os.path.abspath(value)
    raise argparse.ArgumentTypeError(f"Некорректный путь или URL: '{value}'")


def validate_mode(value):
    #Проверка режима работы с репозиторием
    valid_modes = ['read', 'write', 'test']
    if value not in valid_modes:
        raise argparse.ArgumentTypeError(f"Режим должен быть одним из: {', '.join(valid_modes)}")
    return value


def validate_version(value):
    #Проверка корректности версии пакета
    if not re.match(r'^\d+(\.\d+){0,2}$', value):
        raise argparse.ArgumentTypeError(f"Некорректный формат версии: '{value}'. Пример: 1.0.0")
    return value


def validate_filename(value):
    #Проверка корректности имени файла
    if not re.match(r'^[\w,\s-]+\.[A-Za-z]{3,4}$', value):
        raise argparse.ArgumentTypeError(f"Некорректное имя файла: '{value}'")
    return value


def main():
    parser = argparse.ArgumentParser(
        description="Минимальный CLI-прототип конфигурационного приложения."
    )

    parser.add_argument("--package-name", required=True, help="Имя анализируемого пакета")
    parser.add_argument("--repo", required=True, type=validate_url_or_path,
                        help="URL-адрес репозитория или путь к файлу тестового репозитория")
    parser.add_argument("--mode", required=True, type=validate_mode,
                        help="Режим работы с тестовым репозиторием (read, write, test)")
    parser.add_argument("--version", required=True, type=validate_version,
                        help="Версия пакета (пример: 1.0.0)")
    parser.add_argument("--output-file", required=True, type=validate_filename,
                        help="Имя файла для сохранения изображения графа")
    parser.add_argument("--filter", required=False, default="",
                        help="Подстрока для фильтрации пакетов")

    args = parser.parse_args()

    #Вывод всех параметров в формате ключ=значение
    print("\n=== Настройки приложения ===")
    for key, value in vars(args).items():
        print(f"{key} = {value}")
    print("=============================\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)
