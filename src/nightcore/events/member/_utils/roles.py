def roles_difference(
    old_roles: list[int], new_roles: list[int]
) -> tuple[list[int], list[int]]:
    old_set = set(old_roles)
    new_set = set(new_roles)

    added = list(new_set - old_set)
    removed = list(old_set - new_set)
    return added, removed
