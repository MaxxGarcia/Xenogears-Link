// RetroArch network-command reader for Windows: the same protocol and answers as Link.java in the Android app.
// Reads 256-byte pages. mode: m80 = READ_CORE_MEMORY at 0x80000000+offset, m00 = READ_CORE_MEMORY at offset,
// ram = READ_CORE_RAM at offset. All requests go out first and replies are collected after (up to 400 ms),
// so one poll costs about one emulator frame. Answer: {seq, sent, got, err, ok:{pageHex: dataHex}} for onMem().
const dgram = require('dgram');

class Link {
  constructor() { this.sock = null; this.chain = Promise.resolve(); this.handler = null; }
  socket() {
    if (this.sock) return this.sock;
    const s = dgram.createSocket('udp4');
    s.on('message', m => { if (this.handler) this.handler(m.toString('ascii').trim()); });
    s.on('error', () => this.close());
    s.bind(0); this.sock = s; return s;
  }
  close() { if (this.sock) { try { this.sock.close(); } catch (e) {} } this.sock = null; }
  queue(fn) { const r = this.chain.then(fn, fn); this.chain = r.catch(() => {}); return r; }

  send(host, port, cmd) { try { this.socket().send(Buffer.from(cmd, 'ascii'), port, host); } catch (e) {} }

  poll(host, port, mode, pagesCsv, seq) {
    return this.queue(() => new Promise(resolve => {
      let s; try { s = this.socket(); } catch (e) { resolve({ seq, sent: 0, got: 0, err: e.code || 'SocketError', ok: {} }); return; }
      const cmd = mode === 'ram' ? 'READ_CORE_RAM' : 'READ_CORE_MEMORY';
      const base = mode === 'm80' ? 0x80000000 : 0;
      const pages = pagesCsv ? pagesCsv.split(',') : [];
      const ok = {}; let sent = 0, got = 0, err = '', done = false;
      const finish = () => { if (done) return; done = true; this.handler = null; clearTimeout(t); if (got === 0 && sent > 0 && !err) err = 'timeout'; resolve({ seq, sent, got, err, ok }); };
      this.handler = t2 => {                       // replies from an earlier poll are filtered by command name and address
        const f = t2.split(/\s+/); if (f.length < 3 || f[0] !== cmd) return;
        if (f[2] === '-1') { err = 'refused'; got++; if (got >= sent) finish(); return; }
        const addr = parseInt(f[1], 16); if (isNaN(addr)) return;
        const page = (((addr - base) >>> 0) & 0x1FFFFF) >>> 8;
        let hex = ''; for (let i = 2; i < f.length; i++) hex += f[i].length === 1 ? '0' + f[i] : f[i];
        if (hex.length !== 512) { err = 'short'; got++; } else { ok[page.toString(16)] = hex; got++; }
        if (got >= sent) finish();
      };
      const t = setTimeout(finish, 400);
      for (const p of pages) {
        const addr = (base + parseInt(p, 16) * 256) >>> 0;
        s.send(Buffer.from(cmd + ' ' + addr.toString(16) + ' 256\n', 'ascii'), port, host, e => { if (e) err = e.code || 'send'; });
        sent++;
      }
      if (!sent) finish();
    }));
  }
}
module.exports = Link;
