from hashlib import sha1

def hashpath(path: str) -> str:
    """
    Returns a hashed 16-character hexadecimal string given the specific path.

    Parameters
    ----------
    path : str
        Element path

    Returns
    -------
    str
        16-character hexadecimal string
    """
    return sha1(path.encode()).hexdigest()[:16]
