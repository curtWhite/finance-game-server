# Utility package for shared helpers.

def sum_of_values(arr, key):
    return sum(item.get(key, 0) for item in arr)