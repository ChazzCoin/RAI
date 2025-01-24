from typing import Any, Dict


class StringComparator:

    @staticmethod
    def are_strings_identical(string1, string2):
        if len(string1) == len(string2): return True
        return False

class DictComparator:
    @staticmethod
    def are_dicts_identical(
            dict1: Dict[Any, Any],
            dict2: Dict[Any, Any],
            ignore_order_for_lists: bool = False,
            strict_type_checks: bool = True
    ) -> bool:
        """
        Recursively checks whether two dictionaries (potentially nested) are identical.

        :param dict1: The first dictionary to compare.
        :param dict2: The second dictionary to compare.
        :param ignore_order_for_lists: If True, list order is ignored in the comparison
                                       (i.e., [1, 2, 3] is considered equal to [3, 2, 1]).
                                       Defaults to False.
        :param strict_type_checks: If True, the function will require that objects
                                   have the exact same type to be considered equal.
                                   (e.g., 1 (int) vs. 1.0 (float) would be unequal).
                                   If False, it will attempt type-coerced comparisons
                                   where reasonable. Defaults to True.

        :return: True if the two dictionaries are identical in both structure and values;
                 otherwise, False.
        """

        # Quick check for top-level key sets
        if dict1.keys() != dict2.keys():
            return False

        for key in dict1:
            val1 = dict1[key]
            val2 = dict2[key]

            # Check type if strict
            if strict_type_checks and type(val1) is not type(val2):
                return False

            # If both values are dictionaries, recurse
            if isinstance(val1, dict) and isinstance(val2, dict):
                if not DictComparator.are_dicts_identical(
                        val1,
                        val2,
                        ignore_order_for_lists=ignore_order_for_lists,
                        strict_type_checks=strict_type_checks
                ):
                    return False

            # If both values are lists, compare list contents
            elif isinstance(val1, list) and isinstance(val2, list):
                if ignore_order_for_lists:
                    # Sort copies of the lists before comparing
                    if not DictComparator._compare_lists_ignoring_order(val1, val2, strict_type_checks):
                        return False
                else:
                    if not DictComparator._compare_lists_in_order(val1, val2, strict_type_checks):
                        return False

            # If both values are sets or tuples, handle similarly
            elif isinstance(val1, (set, tuple)) and isinstance(val2, (set, tuple)):
                if not DictComparator._compare_other_iterables(val1, val2, strict_type_checks):
                    return False

            # Otherwise just do a direct comparison
            else:
                if strict_type_checks:
                    if val1 != val2:
                        return False
                else:
                    # Attempt type-coerced comparison
                    if not DictComparator._loose_compare(val1, val2):
                        return False

        return True

    @staticmethod
    def _compare_lists_in_order(list1: list, list2: list, strict_type_checks: bool) -> bool:
        """Compare two lists element by element in the given order."""
        if len(list1) != len(list2):
            return False

        for x, y in zip(list1, list2):
            # If both items are dictionaries, recurse
            if isinstance(x, dict) and isinstance(y, dict):
                if not DictComparator.are_dicts_identical(x, y, strict_type_checks=strict_type_checks):
                    return False
            else:
                # For any other type, do direct or loose compare
                if strict_type_checks:
                    if x != y:
                        return False
                else:
                    if not DictComparator._loose_compare(x, y):
                        return False

        return True

    @staticmethod
    def _compare_lists_ignoring_order(list1: list, list2: list, strict_type_checks: bool) -> bool:
        """
        Compare two lists ignoring order. A robust way is to sort them
        by a stable criterion. However, if they contain un-sortable items
        (like dicts), we have to compare frequencies of items.
        """
        if len(list1) != len(list2):
            return False

        # If items are sortable primitives, try sorting
        # But if they contain nested dicts, fallback to frequency-based approach
        try:
            sorted_list1 = sorted(list1)
            sorted_list2 = sorted(list2)
            return DictComparator._compare_lists_in_order(sorted_list1, sorted_list2, strict_type_checks)
        except TypeError:
            # Fallback: build frequency maps
            return DictComparator._compare_frequencies(list1, list2, strict_type_checks)

    @staticmethod
    def _compare_frequencies(list1: list, list2: list, strict_type_checks: bool) -> bool:
        """
        Compare if two lists contain the same elements with the same frequencies,
        ignoring order. This is a fallback for cases where the items are not sortable
        (like nested dicts).
        """
        # Convert each element into a representation that can be counted.
        # This might involve recursively converting dicts into frozendict or something hashable.
        from collections import Counter

        def to_hashable(item: Any) -> Any:
            if isinstance(item, dict):
                # Convert dict to a frozenset-based structure
                return frozenset((k, to_hashable(v)) for k, v in item.items())
            elif isinstance(item, list):
                return tuple(to_hashable(x) for x in item)
            elif isinstance(item, set):
                return frozenset(to_hashable(x) for x in item)
            elif isinstance(item, tuple):
                return tuple(to_hashable(x) for x in item)
            else:
                return item

        transformed_list1 = [to_hashable(x) for x in list1]
        transformed_list2 = [to_hashable(x) for x in list2]

        # If strict type checks are off, we might want to do a separate approach to
        # handle type differences, but that can get very tricky in hash-based compares.
        # For simplicity, assume hashing implies type-based identity.

        return Counter(transformed_list1) == Counter(transformed_list2)

    @staticmethod
    def _compare_other_iterables(it1, it2, strict_type_checks: bool) -> bool:
        """Compare sets or tuples directly."""
        if type(it1) != type(it2):
            return False

        # If they are sets, we can compare them directly (order doesn't matter for sets).
        if isinstance(it1, set):
            return it1 == it2

        # For tuples, we compare element by element in order.
        if isinstance(it1, tuple):
            if len(it1) != len(it2):
                return False
            for x, y in zip(it1, it2):
                if isinstance(x, dict) and isinstance(y, dict):
                    if not DictComparator.are_dicts_identical(x, y, strict_type_checks=strict_type_checks):
                        return False
                else:
                    if strict_type_checks:
                        if x != y:
                            return False
                    else:
                        if not DictComparator._loose_compare(x, y):
                            return False
            return True

        return False

    @staticmethod
    def _loose_compare(val1: Any, val2: Any) -> bool:
        """
        Compares two values loosely, attempting to convert them to the same type
        for comparison if they are numeric or string-compatible.
        """
        # If both are numeric, compare float-converted values
        if _is_numeric(val1) and _is_numeric(val2):
            return float(val1) == float(val2)

        # Otherwise, try string comparison
        # (This is arbitrary; you can implement custom logic.)
        return str(val1) == str(val2)


def _is_numeric(value: Any) -> bool:
    """Helper function to check if a value is numeric."""
    return isinstance(value, (int, float, complex)) or (
            isinstance(value, str) and value.isdigit()
    )
