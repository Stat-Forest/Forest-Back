import re


def is_number(value: str) -> bool:
    if value is None:
        return False
    return re.match(r'^\d+(\.\d+)?$', str(value)) is not None
