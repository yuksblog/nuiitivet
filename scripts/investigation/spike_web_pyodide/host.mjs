// What the shim reaches through `js`, shared by the Node runner and the browser page.
//
// The helpers take plain numbers so one draw is one crossing from Python, with
// no array built on the Python side.

export function installHost(CK, fontData, spike) {
  const styles = [CK.PaintStyle.Fill, CK.PaintStyle.Stroke];
  const caps = [CK.StrokeCap.Butt, CK.StrokeCap.Round, CK.StrokeCap.Square];

  globalThis.CK = CK;
  globalThis.FONT_DATA = fontData;
  globalThis.SPIKE = spike;
  globalThis.H = {
    paint(p, color, aa, style, strokeWidth, cap) {
      if (!p) p = new CK.Paint();
      p.setColorInt(color);
      p.setAntiAlias(aa);
      p.setStyle(styles[style]);
      p.setStrokeWidth(strokeWidth);
      p.setStrokeCap(caps[cap]);
      return p;
    },
    release(o) { o.delete(); },
    measure(f, text) {
      const widths = f.getGlyphWidths(f.getGlyphIDs(text));
      let sum = 0;
      for (let i = 0; i < widths.length; i++) sum += widths[i];
      return sum;
    },
    posBlob(text, xs, y, f) {
      const glyphs = f.getGlyphIDs(text);
      const rs = new Float32Array(glyphs.length * 4);
      for (let i = 0; i < glyphs.length; i++) {
        rs[i * 4] = 1;
        rs[i * 4 + 2] = xs[i] ?? 0;
        rs[i * 4 + 3] = y;
      }
      return CK.TextBlob.MakeFromRSXformGlyphs(glyphs, rs, f);
    },
    clear(c, a, r, g, b) { c.clear(CK.Color4f(r, g, b, a)); },
    clipRect(c, l, t, r, b) { c.clipRect(CK.LTRBRect(l, t, r, b), CK.ClipOp.Intersect, true); },
    drawRRect(c, l, t, r, b, rx, ry, p) { c.drawRRect(CK.RRectXY(CK.LTRBRect(l, t, r, b), rx, ry), p); },
    drawOval(c, l, t, r, b, p) { c.drawOval(CK.LTRBRect(l, t, r, b), p); },
  };
}

// The Python that starts the benchmark once the sources are importable from `paths`.
export function startScript(paths, entry) {
  return `
import runpy
import sys

sys.path[:0] = ${JSON.stringify(paths)}
runpy.run_path(${JSON.stringify(entry)}, run_name="__main__")
`;
}
