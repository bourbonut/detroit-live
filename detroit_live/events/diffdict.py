from typing import Any

def diffdict(old: dict[str, Any], new: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """
    Compares two dictionary and returns the removed attributes and changes as
    dictionary.

    Parameters
    ----------
    old : dict[str, Any]
        Old version of version
    new : dict[str, Any]
       New version of values 

    Returns
    -------
    dict[str, dict[str, Any]]
        Differences between :code:`old` and :code:`new`
    """
    change = []
    remove = []
    okeys = old.keys()
    nkeys = new.keys()
    for key in nkeys - okeys:
        change.append([key, new[key]])
    for key in okeys & nkeys:
        if old[key] != new[key]:
            change.append([key, new[key]])
    for key in okeys - nkeys:
        remove.append([key, old[key]])
    return {"remove": remove, "change": change}
