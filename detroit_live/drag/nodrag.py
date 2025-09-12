from ..selection import select

def nodrag(node):
    selection = select(node) #.on("dragstart.drag", noevent)
    if "onselectstart" in node:
        selection #.on("selectstart.drag", noevent)
    else:
        pass

def yesdrag(node, noclick):
    selection = select(node).on("dragstart.drag", None)
    if noclick:
        selection #.on("click.drag", noevent)
    if "onselectstart" in node:
        selection #.on("selection.drag", None)
    else:
        pass
