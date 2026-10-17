#!/usr/bin/env python3
"""(From another project of the user's, tools/deck/steam_shortcut.py, 2026-10-14; used as is. Mulle Meck's
launcher sends it to the Deck after a copy, launcher/deck.py.)

Adds a game to the Steam library on a Steam Deck, or updates the entry it already has (found by name). Runs on the
Deck (the sender runs it over SSH). It goes through the Steam client's own SteamClient API in its
SharedJSContext page, over the client's debugging port, which Decky Loader turns on
(~/.steam/steam/.cef-enable-remote-debugging). Steam keeps running and shows the game at once, also in Game Mode.

    python3 steam_shortcut.py --name NAME --exe PATH --dir DIR [--tool proton_experimental] [--options ...] [--art DIR]

--tool is the compatibility tool Steam runs it with (Proton for a Windows exe); empty for a native program. --art: a
folder with the entry's artwork, named by Steam's sizes: library_600x900.png the portrait tile,
header_920x430.png the wide one, main_1232x706.png the banner over the game's page (Steam fits it); what's missing
stays as it is.
"""
import argparse
import base64
import json
import os
import socket
import struct
import urllib.request

DEBUG_PORT = "127.0.0.1:8080"


class WebSocket:
    """Just enough of RFC 6455 for a few text messages to the debugging port."""

    def __init__(self, url):
        hostport, path = url[len("ws://"):].split("/", 1)
        host, port = hostport.rsplit(":", 1)
        self.sock = socket.create_connection((host, int(port)), timeout=20)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall(("GET /%s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                           "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n" % (path, hostport, key)).encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("Steam closed the connection during the handshake")
            head += chunk
        head, self.buf = head.split(b"\r\n\r\n", 1)
        status = head.split(b"\r\n", 1)[0]
        if b" 101 " not in status:
            raise ConnectionError(status.decode(errors="replace"))

    def send(self, text):
        data = text.encode()
        head = bytearray([0x81])  # one frame, text
        if len(data) < 126:
            head.append(0x80 | len(data))
        elif len(data) < 1 << 16:
            head += bytes([0x80 | 126]) + struct.pack(">H", len(data))
        else:
            head += bytes([0x80 | 127]) + struct.pack(">Q", len(data))
        mask = os.urandom(4)  # a client masks what it sends
        self.sock.sendall(bytes(head) + mask + bytes(b ^ mask[i & 3] for i, b in enumerate(data)))

    def _read(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("Steam closed the connection")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def recv(self):
        message = b""
        while True:
            b0, b1 = self._read(2)
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            mask = self._read(4) if b1 & 0x80 else None
            payload = self._read(n)
            if mask:
                payload = bytes(b ^ mask[i & 3] for i, b in enumerate(payload))
            opcode = b0 & 0x0F
            if opcode == 8:
                raise ConnectionError("Steam closed the connection")
            if opcode in (9, 10):  # ping, pong
                continue
            message += payload
            if b0 & 0x80:
                return message.decode()


def evaluate(expression):
    """Runs JavaScript in Steam's SharedJSContext page (where SteamClient lives) and returns its value."""
    targets = json.load(urllib.request.urlopen("http://%s/json" % DEBUG_PORT, timeout=5))
    page = next((t for t in targets if t.get("title") == "SharedJSContext"), None)
    if not page:
        raise RuntimeError("no SharedJSContext page on the debugging port (is Steam running?)")
    ws = WebSocket(page["webSocketDebuggerUrl"])
    ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate",
                        "params": {"expression": expression, "awaitPromise": True, "returnByValue": True}}))
    while True:
        reply = json.loads(ws.recv())
        if reply.get("id") == 1:
            break
    result = reply.get("result", {})
    if "exceptionDetails" in result:
        details = result["exceptionDetails"]
        raise RuntimeError(details.get("exception", {}).get("description") or details.get("text"))
    return result.get("result", {}).get("value")


# Shortcuts (non-Steam games) are app type 0x40000000. Steam keeps a shortcut's exe and start folder in quotes.
ADD_OR_UPDATE = """(async () => {
    const a = %s;
    const apps = (window.appStore && appStore.allApps) || [];
    const found = apps.find(x => x.app_type === 0x40000000 && x.display_name === a.name);
    const exe = '"' + a.exe + '"', dir = '"' + a.dir + '"';
    const appId = found ? found.appid : await SteamClient.Apps.AddShortcut(a.name, exe, dir, a.options);
    SteamClient.Apps.SetShortcutName(appId, a.name);
    SteamClient.Apps.SetShortcutExe(appId, exe);
    SteamClient.Apps.SetShortcutStartDir(appId, dir);
    SteamClient.Apps.SetAppLaunchOptions(appId, a.options);
    SteamClient.Apps.SpecifyCompatTool(appId, a.tool);
    return JSON.stringify({ appId: appId, added: !found });
})()"""


# The artwork, by SteamClient.Apps.SetCustomArtworkForApp's asset type (0 the portrait tile, 1 the banner, 3 the wide
# tile; 2 would be a logo over the banner, and the pictures have their own).
ART = [("library_600x900.png", 0), ("main_1232x706.png", 1), ("header_920x430.png", 3)]
SET_ART = "SteamClient.Apps.SetCustomArtworkForApp(%d, %s, 'png', %d).then(() => 'ok')"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--name", required=True)
    ap.add_argument("--exe", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--tool", default="")
    ap.add_argument("--options", default="")
    ap.add_argument("--art", default="")
    args = ap.parse_args()
    entry = {k: v for k, v in vars(args).items() if k != "art"}
    result = json.loads(evaluate(ADD_OR_UPDATE % json.dumps(entry)))
    print("%s Steam's library: \"%s\" (app id %d)%s" % ("Added to" if result["added"] else "Updated in", args.name,
                                                         result["appId"], ", runs with " + args.tool if args.tool else ""))
    done = []
    for name, kind in ART if args.art else []:
        path = os.path.join(args.art, name)
        if os.path.exists(path):
            with open(path, "rb") as f:
                evaluate(SET_ART % (result["appId"], json.dumps(base64.b64encode(f.read()).decode()), kind))
            done.append(name)
    if done:
        print("Its artwork: " + ", ".join(done))


if __name__ == "__main__":
    main()
