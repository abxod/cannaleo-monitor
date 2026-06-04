def deep_get(d, *keys, default=None):
    for key in keys[:-1]:
        if not isinstance(d, dict):
            return default
        d = d.get(key)
        if d is None:
            return default
    if not isinstance(d, dict):
        return default
    return d.get(keys[-1], default)
