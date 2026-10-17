def compare_profiles(current, previous):
    current_summary = current["summary"]
    previous_summary = previous["summary"]

    current_columns = {
        item["column"]: item for item in current["columns"]
    }
    previous_columns = {
        item["column"]: item for item in previous["columns"]
    }

    current_names = set(current_columns)
    previous_names = set(previous_columns)

    added_columns = sorted(current_names - previous_names)
    removed_columns = sorted(previous_names - current_names)

    type_changes = []
    missing_changes = []

    for column in sorted(current_names & previous_names):
        current_item = current_columns[column]
        previous_item = previous_columns[column]

        if current_item["dtype"] != previous_item["dtype"]:
            type_changes.append(
                {
                    "column": column,
                    "previous": previous_item["dtype"],
                    "current": current_item["dtype"],
                }
            )

        delta = current_item["missing_count"] - previous_item["missing_count"]
        if delta:
            missing_changes.append(
                {
                    "column": column,
                    "previous": previous_item["missing_count"],
                    "current": current_item["missing_count"],
                    "delta": delta,
                }
            )

    return {
        "previous_source": previous_summary["source"],
        "current_source": current_summary["source"],
        "row_delta": current_summary["rows"] - previous_summary["rows"],
        "column_delta": current_summary["columns"] - previous_summary["columns"],
        "duplicate_row_delta": (
            current_summary["duplicate_rows"]
            - previous_summary["duplicate_rows"]
        ),
        "added_columns": added_columns,
        "removed_columns": removed_columns,
        "type_changes": type_changes,
        "missing_value_changes": missing_changes,
    }
