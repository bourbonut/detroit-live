# Sorry for those who struggle to read this JavaScript code
# This code is minified and it is JavaScript ...
EVENT_HEADERS = """
const socket = new WebSocket("ws://localhost:5000/ws");

function f(o, t, u) {
    o.elementId = u;
    o.typename = t;
    point = pointer(o, document.querySelector("svg"));
    o.pageX = point[0];
    o.pageY = point[1];
    socket.send(JSON.stringify(o, null, 0));
}

function sourceEvent(event) {
  let sourceEvent;
  while (sourceEvent = event.sourceEvent) event = sourceEvent;
  return event;
}

function pointer(event, node) {
  event = sourceEvent(event);
  if (node === undefined) node = event.currentTarget;
  if (node) {
    var svg = node.ownerSVGElement || node;
    if (svg.createSVGPoint) {
      var point = svg.createSVGPoint();
      point.x = event.clientX, point.y = event.clientY;
      point = point.matrixTransform(node.getScreenCTM().inverse());
      return [point.x, point.y];
    }
    if (node.getBoundingClientRect) {
      var rect = node.getBoundingClientRect();
      return [event.clientX - rect.left - node.clientLeft, event.clientY - rect.top - node.clientTop];
    }
  }
  return [event.pageX, event.pageY];
}

function p(e) {
    if (!e) return;
    if (e === document.body) return 'body';
    let t = e.parentNode;
    if (null == t) return '';
    let r = Array.from(t.children).filter((t => t.tagName === e.tagName)),
        n = r.indexOf(e) + 1,
        a = e.tagName.toLowerCase(),
        o = p(t) + '/' + a;
    return r.length > 1 && (o += `[${n}]`), o
}

function q(u) {
    var n, s = u.split(" "), t = s[s.length - 2], els = document.querySelectorAll(u);
    if ((n = els.length) === 1 || t === undefined) {
        return els[0];
    } else {
        for (var i = 0, el; i < n; i++){
            el = els[i];
            if (el.parentNode.tagName === t) {
                return el;
            }
        }
    }
}

socket.addEventListener('message', (e) => {
    const fr = new FileReader();
    fr.onload = function(o) {
        const t = JSON.parse(o.target.result);
        for (var i1 = 0, r, n = t.length; i1 < n; ++i1) {
            r = t[i1];
            const el = q(r.elementId);
            if (el == undefined) {
                continue;
            }
            if (r.diff != undefined) {
                var c = r.diff.change;
                for (var i2 = 0, k, v, m = c.length; i2 < m; ++i2) {
                    [k, v] = c[i2];
                    k === "innerHTML" ? el[k] = v: el.setAttribute(k, v)
                }
                c = r.diff.remove;
                for (var i2 = 0, k, v, m = c.length; i2 < m; ++i2) {
                    [k, v] = c[i2];
                    k === "innerHTML" ? el[k] = undefined : el.removeAttribute(k);
                }
            } else {
                el.outerHTML = r.outerHTML;
            }
        }
    };
    fr.readAsText(e.data);
});
"""

EVENT_HEADERS = "".join(s.strip() for s in EVENT_HEADERS.split("\n")).strip()


def headers(host: str, port: int) -> str:
    """
    Returns the headers used by the event script in JavaScript.

    Parameters
    ----------
    host : str
        Host value
    port : int
        Port value

    Returns
    -------
    str
        Headers of event script used by JavaScript
    """
    return EVENT_HEADERS.replace("localhost", host).replace("5000", str(port))
