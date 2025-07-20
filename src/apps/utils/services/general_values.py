def build_columns_with_jami(columns: list):
    general_columns = []

    for column in columns:
        col_id = column["statement_column_id"]
        col_name = column["statement_column_name"]
        inners = column["inners"]

        first_value = inners[0]["value"] if inners else None

        if first_value is not None:
            try:
                numeric_values = [float(inner["value"]) for inner in inners]
                total_sum = sum(numeric_values)
                general_inners = [{"value": str(int(total_sum))} if total_sum.is_integer() else total_sum]
            except (ValueError, TypeError):
                general_inners = [{"value": inner["value"]} for inner in inners]
        else:
            general_inners = []

        general_columns.append({
            "statement_column_id": col_id,
            "statement_column_name": f"{col_name} Jami",
            "inners": general_inners
        })
    return columns, general_columns