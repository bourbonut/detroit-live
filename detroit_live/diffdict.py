def diffdict(old, new):
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
