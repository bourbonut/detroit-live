# Sorry for those who struggle to read this JavaScript code
# This code is minified and it is JavaScript ...
EVENT_HEADERS = """
const s = new WebSocket("ws://localhost:5000/ws");
const w = window;
const d = document;

function f(o, t, u) {
    o.elementId = u;
    o.typename = t;
    s.send(JSON.stringify(o, null, 0));
}

function p(e) {
    if (!e) return;
    if (e === d.body) return 'body';
    let t = e.parentNode;
    if (null == t) return '';
    let r = Array.from(t.children).filter((t => t.tagName === e.tagName)),
        n = r.indexOf(e) + 1,
        a = e.tagName.toLowerCase(),
        o = p(t) + '/' + a;
    return r.length > 1 && (o += `[${n}]`), o
}

function q(u) {
    return d.querySelector(u)
}

s.addEventListener('message', (e) => {
    const r = new FileReader();
    r.onload = function(o) {
        const v = JSON.parse(o.target.result);
        const el = q(v.elementId);
        if (v.diff != undefined) {
            v.diff.change.forEach(([k, v_]) => el[k] = v_);
            v.diff.remove.forEach(([k, _]) => el[k] = undefined);
        } else {
            el.outerHTML = v.outerHTML
        }
    };
    r.readAsText(e.data);
});
"""

EVENT_HEADERS = "".join(
    s.strip() for s in EVENT_HEADERS.split("\n")
).strip()

def headers(host: str, port: int):
    return EVENT_HEADERS.replace("localhost", host).replace("5000", str(port))
