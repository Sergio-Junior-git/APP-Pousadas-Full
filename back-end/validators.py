import re
from datetime import date
from typing import Any

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def only_digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def is_valid_cpf(cpf: str) -> bool:
    digits = only_digits(cpf)
    if len(digits) != 11 or digits == digits[0] * 11:
        return False

    for size in (9, 10):
        total = sum(int(digits[i]) * ((size + 1) - i) for i in range(size))
        expected = (total * 10 % 11) % 10
        if expected != int(digits[size]):
            return False

    return True


def normalize_cpf(cpf: str) -> str:
    digits = only_digits(cpf)
    if not is_valid_cpf(digits):
        raise ValueError("CPF inválido")
    return digits


def validate_name(name: str, field: str = "Nome", min_length: int = 3) -> str:
    cleaned = (name or "").strip()
    if len(cleaned) < min_length:
        raise ValueError(f"{field} deve conter no mínimo {min_length} caracteres")
    return cleaned


def validate_email(email: str) -> str:
    cleaned = (email or "").strip().lower()
    if not EMAIL_PATTERN.match(cleaned):
        raise ValueError("E-mail inválido")
    return cleaned


def enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def ensure_period(start: date, end: date) -> None:
    if end < start:
        raise ValueError("A data final não pode ser anterior à data inicial")
