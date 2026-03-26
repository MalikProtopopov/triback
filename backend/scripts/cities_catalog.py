"""Каталог городов для импорта: нормализация имён, извлечение из строк с «обл., г.».

Исходные строки — файл data/cities_source_lines.txt (по одному городу/строке импорта на строку).
Дополнительные города — EXTRA_CITIES (если ещё не в списке после дедупликации).
"""

from __future__ import annotations

import re
from pathlib import Path

# Дополнительные крупные города, если их не оказалось в исходном списке
EXTRA_CITIES: tuple[str, ...] = (
    "Астрахань",
    "Брянск",
    "Владикавказ",
    "Геленджик",
    "Иваново",
    "Калуга",
    "Кемерово",
    "Новороссийск",
    "Сочи",
    "Тамбов",
    "Улан-Удэ",
    "Чебоксары",
    "Якутск",
)

# Предпочтительное написание (ключ — lower)
SPELLING: dict[str, str] = {
    "санкт-петербург": "Санкт-Петербург",
    "г. санкт-петербург": "Санкт-Петербург",
    "москва": "Москва",
    "г. москва": "Москва",
    "нижний новгород": "Нижний Новгород",
    "г. нижний новгород": "Нижний Новгород",
    "ростов-на-дону": "Ростов-на-Дону",
    "нальчик": "Нальчик",
    "назрань": "Назрань",
    "щёлково": "Щёлково",
    "тольятти": "Тольятти",
    "королёв": "Королёв",
    "симферополь": "Симферополь",
    "севастополь": "Севастополь",
    "майкоп": "Майкоп",
    "грозный": "Грозный",
    "махачкала": "Махачкала",
    "г. ставрополь": "Ставрополь",
    "г. тверь": "Тверь",
    "г. челябинск": "Челябинск",
    "г. оренбург": "Оренбург",
    "г. архангельск": "Архангельск",
    "г. брянск": "Брянск",
    "г. пятигорск": "Пятигорск",
    "г. орёл": "Орёл",
    "г. омск": "Омск",
    "минск": "Минск",
    "г. минск": "Минск",
}


def cities_source_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "cities_source_lines.txt"


def load_raw_lines() -> list[str]:
    p = cities_source_path()
    if not p.is_file():
        return []
    return [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines()]


def normalize_city_name(name: str) -> str:
    s = name.strip()
    s = re.sub(r"(?i)^г\.\s*", "", s)
    s = re.sub(r"(?i)^г\s+", "", s)
    s = re.sub(r"\s+", " ", s)
    key = s.lower().replace("ё", "е")
    if key in SPELLING:
        return SPELLING[key]
    # Титульный регистр для одного слова не делаем — кириллица как в источнике
    return s


def _is_address_junk(fragment: str) -> bool:
    pl = fragment.lower()
    junk = (
        "обл.",
        "обл,",
        "р-он",
        "р-н",
        "район",
        "пгт",
        "дер.",
        "д.",
        "дер ",
        "ао,",
        "ао.",
        "респ.",
        "село",
        "свердловская обл",
        "тульская обл",
    )
    return any(x in pl for x in junk)


def extract_city_from_line(line: str) -> str | None:
    """Из строки вида «Саратовская обл., г. Балаково» извлекает «Балаково»; мусор пропускает."""
    line = line.strip()
    if not line or len(line) < 2:
        return None
    if "узбекистан" in line.lower():
        return None
    line = line.replace("Белогородская", "Белгородская")
    parts = [p.strip() for p in line.split(",")]
    for p in reversed(parts):
        p = re.sub(r"(?i)^г\.\s*", "", p).strip()
        p = re.sub(r"(?i)^г\s+", "", p).strip()
        if len(p) < 2:
            continue
        if _is_address_junk(p):
            continue
        return normalize_city_name(p)
    # одна часть без запятых
    one = re.sub(r"(?i)^г\.\s*", "", line).strip()
    if _is_address_junk(one):
        return None
    return normalize_city_name(one)


def build_canonical_city_names(raw_lines: list[str] | None = None) -> list[str]:
    """Уникальные нормализованные названия, отсортированные по алфавиту."""
    lines = raw_lines if raw_lines is not None else load_raw_lines()
    by_lower: dict[str, str] = {}
    for line in lines:
        if not line.strip():
            continue
        c = extract_city_from_line(line)
        if not c:
            continue
        key = c.lower().replace("ё", "е")
        if key not in by_lower:
            by_lower[key] = c
    for ex in EXTRA_CITIES:
        key = ex.lower().replace("ё", "е")
        if key not in by_lower:
            by_lower[key] = ex
    return sorted(by_lower.values(), key=lambda x: x.lower())


def canonical_key(name: str) -> str:
    return name.strip().lower().replace("ё", "е")
