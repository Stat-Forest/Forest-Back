# apps/e_imzo/utils.py
def split_full_name(full_name: str):
    parts = full_name.strip().split()
    first_name = last_name = father_name = ""

    if len(parts) == 1:
        last_name = parts[0]
    elif len(parts) == 2:
        first_name, last_name = parts
    elif len(parts) >= 3:
        first_name, last_name, father_name = parts[:3]

    return first_name, last_name, father_name
