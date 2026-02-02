def calculate_diff_and_percent(plan, actual):
    diff = actual - plan
    percent = (actual / plan * 100) if plan else 0
    return diff, round(percent, 2)

