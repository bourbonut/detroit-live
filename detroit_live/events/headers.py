# Sorry for those who struggle to read this JavaScript code
# This code is minified and it is JavaScript ...
EVENT_HEADERS = """
const socket = new WebSocket("ws://localhost:5000/ws");

function f(o, t, u) {
    o.elementId = u;
    o.typename = t;
    socket.send(JSON.stringify(o, null, 0));
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
    return document.querySelector(u)
}

socket.addEventListener('message', (e) => {
    const fr = new FileReader();
    fr.onload = function(o) {
        const r = JSON.parse(o.target.result);
        const el = q(r.elementId);
        if (r.diff != undefined) {
            r.diff.change.forEach(([k, v]) => k === "innerHTML" ? el[k] = v: el.setAttribute(k, v));
            r.diff.remove.forEach(([k, _]) => k === "innerHTML" ? el[k] = undefined : el.removeAttribute(k));
        } else {
            el.outerHTML = r.outerHTML
        }
    };
    fr.readAsText(e.data);
});
"""

EVENT_HEADERS = "".join(
    s.strip() for s in EVENT_HEADERS.split("\n")
).strip()

def headers(host: str, port: int):
    return EVENT_HEADERS.replace("localhost", host).replace("5000", str(port))
