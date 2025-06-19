def get_root_column(column):
    visited = set()
    while column.parent_id and column.id not in visited:
        visited.add(column.id)
        column = column.parent
    return column