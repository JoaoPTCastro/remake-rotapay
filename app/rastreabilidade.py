"""Horários apresentados com UTC explícito; datas de negócio continuam separadas."""
from datetime import timezone


def horario_utc(value):
    if value is None:
        return None
    return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)).isoformat()
