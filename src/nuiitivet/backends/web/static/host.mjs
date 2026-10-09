// What the CanvasKit adapter reaches through `js.NV_HOST`.
//
// The helpers take plain numbers, so one draw is one crossing from Python with
// no array built on the Python side.
//
// A canvas keeps the identity matrix between runs of draws. `m` applies the
// adapter's matrix inside a save level of its own, and every save, restore and
// clip pops that level first.

export function installHost(CK, canvas, input, fonts) {
  const styles = [CK.PaintStyle.Fill, CK.PaintStyle.Stroke];
  const caps = [CK.StrokeCap.Butt, CK.StrokeCap.Round, CK.StrokeCap.Square];
  const ltrb = (l, t, r, b) => CK.LTRBRect(l, t, r, b);
  const rrect = (l, t, r, b, radii) => Float32Array.of(l, t, r, b, ...radii);

  function drop(c) {
    if (c._nvMatrix) {
      c.restore();
      c._nvMatrix = false;
    }
  }

  const context = CK.GetWebGLContext(canvas);
  const gr = context ? CK.MakeWebGLContext(context) : null;
  let surface = null;
  let sized = "";

  const host = {
    CK,
    fonts,
    width: 0,
    height: 0,
    pixelWidth: 0,
    pixelHeight: 0,
    dpr: 1,
    onResize: null,
    onPointer: null,
    onWheel: null,
    onKey: null,
    onText: null,
    onCompose: null,
    onPaste: null,

    // Move the unseen input field to the caret. Without a focused text field
    // it asks for no on-screen keyboard.
    placeInput(x, y, height, editing) {
      input.style.left = `${x}px`;
      input.style.top = `${y}px`;
      input.style.height = `${Math.max(1, height)}px`;
      input.inputMode = editing ? "text" : "none";
    },
    writeClipboard(text) {
      navigator.clipboard?.writeText(text).catch((error) => console.warn("copy failed:", error));
    },

    // A page opens a picker only while a click or a key press is being handled.
    canShowPicker() {
      return !navigator.userActivation || navigator.userActivation.isActive;
    },
    // The file picker: the files chosen, none when the user cancelled.
    pickFiles(accept, multiple, directory) {
      return new Promise((resolve) => {
        const picker = document.createElement("input");
        picker.type = "file";
        picker.accept = accept;
        picker.multiple = multiple;
        picker.webkitdirectory = directory;
        picker.style.display = "none";
        const done = (files) => { picker.remove(); resolve(files); };
        picker.addEventListener("change", () => done(Array.from(picker.files)));
        picker.addEventListener("cancel", () => done([]));
        document.body.append(picker);
        picker.click();
      });
    },
    download(name, bytes) {
      const url = URL.createObjectURL(new Blob([bytes]));
      const link = document.createElement("a");
      link.href = url;
      link.download = name;
      link.click();
      // The browser reads the URL after the click returns; revoking at once can lose the download.
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
    },

    // The surface for this frame. It is made again when the canvas or the
    // device pixel ratio changed, and the caller repaints everything then.
    frame() {
      const dpr = window.devicePixelRatio || 1;
      const width = Math.max(1, canvas.clientWidth);
      const height = Math.max(1, canvas.clientHeight);
      const key = `${width}x${height}@${dpr}`;
      if (key !== sized) {
        sized = key;
        canvas.width = Math.max(1, Math.round(width * dpr));
        canvas.height = Math.max(1, Math.round(height * dpr));
        if (surface) surface.delete();
        surface = gr
          ? CK.MakeOnScreenGLSurface(gr, canvas.width, canvas.height, CK.ColorSpace.SRGB)
          : CK.MakeSWCanvasSurface(canvas);
        Object.assign(host, { width, height, dpr, pixelWidth: canvas.width, pixelHeight: canvas.height });
      }
      return surface;
    },

    release(o) { o.delete(); },

    paint(p, color, aa, style, strokeWidth, cap, maskFilter, pathEffect) {
      if (!p) p = new CK.Paint();
      p.setColorInt(color);
      p.setAntiAlias(aa);
      p.setStyle(styles[style]);
      p.setStrokeWidth(strokeWidth);
      p.setStrokeCap(caps[cap]);
      p.setMaskFilter(maskFilter ?? null);
      p.setPathEffect(pathEffect ?? null);
      return p;
    },
    blur(sigma, respectCTM) { return CK.MaskFilter.MakeBlur(CK.BlurStyle.Normal, sigma, respectCTM); },
    dash(intervals, phase) { return CK.PathEffect.MakeDash(Array.from(intervals), phase); },

    m(c, sx, kx, tx, ky, sy, ty) {
      drop(c);
      if (sx === 1 && kx === 0 && tx === 0 && ky === 0 && sy === 1 && ty === 0) return;
      c.save();
      c.concat([sx, kx, tx, ky, sy, ty, 0, 0, 1]);
      c._nvMatrix = true;
    },
    save(c) { drop(c); c.save(); },
    restore(c) { drop(c); c.restore(); },
    saveLayer(c, p, bounded, l, t, r, b) {
      drop(c);
      c.saveLayer(p ?? undefined, bounded ? ltrb(l, t, r, b) : null);
    },

    // Clips take device coordinates: the canvas is at the identity matrix here.
    clipRect(c, l, t, r, b, aa) { drop(c); c.clipRect(ltrb(l, t, r, b), CK.ClipOp.Intersect, aa); },
    clipRRect(c, l, t, r, b, aa, ...radii) {
      drop(c);
      c.clipRRect(rrect(l, t, r, b, radii), CK.ClipOp.Intersect, aa);
    },
    // A clip under a rotation or a skew is not a rect in device coordinates.
    clipTransformed(c, sx, kx, tx, ky, sy, ty, l, t, r, b, aa, ...radii) {
      drop(c);
      const builder = new CK.PathBuilder();
      builder.addRRect(rrect(l, t, r, b, radii));
      builder.transform([sx, kx, tx, ky, sy, ty, 0, 0, 1]);
      const path = builder.detachAndDelete();
      c.clipPath(path, CK.ClipOp.Intersect, aa);
      path.delete();
    },

    clear(c, a, r, g, b) { c.clear(CK.Color4f(r, g, b, a)); },
    rrect(c, l, t, r, b, rx, ry, p) { c.drawRRect(CK.RRectXY(ltrb(l, t, r, b), rx, ry), p); },
    rrect8(c, l, t, r, b, p, ...radii) { c.drawRRect(rrect(l, t, r, b, radii), p); },
    drrect(c, p, ...v) { c.drawDRRect(Float32Array.from(v.slice(0, 12)), Float32Array.from(v.slice(12)), p); },
    oval(c, l, t, r, b, p) { c.drawOval(ltrb(l, t, r, b), p); },
    arc(c, l, t, r, b, start, sweep, useCenter, p) { c.drawArc(ltrb(l, t, r, b), start, sweep, useCenter, p); },
    path(c, builder, p) {
      const path = builder.snapshot();
      c.drawPath(path, p);
      path.delete();
    },
    image(c, image, x, y, linear, p) {
      const filter = linear ? CK.FilterMode.Linear : CK.FilterMode.Nearest;
      c.drawImageOptions(image, x, y, filter, CK.MipmapMode.None, p ?? null);
    },
    imageRect(c, image, sl, st, sr, sb, dl, dt, dr, db, linear, p) {
      const filter = linear ? CK.FilterMode.Linear : CK.FilterMode.Nearest;
      c.drawImageRectOptions(image, ltrb(sl, st, sr, sb), ltrb(dl, dt, dr, db), filter, CK.MipmapMode.None, p ?? null);
    },

    arcTo(builder, l, t, r, b, start, sweep, forceMoveTo) {
      builder.arcToOval(ltrb(l, t, r, b), start, sweep, forceMoveTo);
    },
    addRect(builder, l, t, r, b) { builder.addRect(ltrb(l, t, r, b)); },
    addRRect(builder, l, t, r, b, ...radii) { builder.addRRect(rrect(l, t, r, b, radii)); },
    addOval(builder, l, t, r, b) { builder.addOval(ltrb(l, t, r, b)); },

    typeface(bytes) {
      const copy = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
      return CK.Typeface.MakeTypefaceFromData(copy);
    },
    metrics(f) {
      const metrics = f.getMetrics();
      return [metrics.ascent, metrics.descent, metrics.leading];
    },
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

    decode(bytes) { return CK.MakeImageFromEncoded(bytes); },
    encode(image) { return image.encodeToBytes(); },
  };

  new ResizeObserver(() => host.onResize?.()).observe(canvas);
  // A window dragged to a display of another density changes the ratio with no resize.
  const watchRatio = () => {
    matchMedia(`(resolution: ${window.devicePixelRatio}dppx)`).addEventListener(
      "change",
      () => { host.onResize?.(); watchRatio(); },
      { once: true },
    );
  };
  watchRatio();

  // The bits follow MOD_SHIFT, MOD_CTRL, MOD_ALT and MOD_META of nuiitivet.input.codes.
  const mods = (e) => (e.shiftKey ? 1 : 0) | (e.ctrlKey ? 2 : 0) | (e.altKey ? 4 : 0) | (e.metaKey ? 8 : 0);
  const pointer = (kind) => (e) => host.onPointer?.(kind, e.offsetX, e.offsetY, e.button, e.buttons, mods(e));
  // The input field holds the keyboard focus, so text, IME and paste events
  // arrive there. A press on the canvas must not take the focus away.
  canvas.addEventListener("mousedown", (e) => e.preventDefault());
  canvas.addEventListener("pointerdown", (e) => {
    input.focus({ preventScroll: true });
    // A drag keeps reaching the canvas after the pointer leaves it.
    canvas.setPointerCapture(e.pointerId);
    pointer("down")(e);
  });
  canvas.addEventListener("pointerup", pointer("up"));
  canvas.addEventListener("pointermove", pointer("move"));
  canvas.addEventListener("contextmenu", (e) => e.preventDefault());
  canvas.addEventListener(
    "wheel",
    (e) => {
      // Ctrl with the wheel is the browser's zoom.
      if (e.ctrlKey) return;
      e.preventDefault();
      host.onWheel?.(e.offsetX, e.offsetY, e.deltaX, e.deltaY, e.deltaMode);
    },
    { passive: false },
  );

  let composing = false;
  // A key pressed during a composition belongs to the IME; 229 is how older browsers mark one.
  const imeKey = (e) => composing || e.isComposing || e.keyCode === 229;
  input.addEventListener("keydown", (e) => {
    if (imeKey(e)) return;
    const accel = e.ctrlKey || e.metaKey;
    // The paste event carries the text; the key alone cannot read the clipboard.
    if (accel && e.key.toLowerCase() === "v") return;
    const handled = host.onKey?.(true, e.key, e.code, mods(e), e.repeat);
    // A character key stays with the browser, which turns it into an input event.
    if ((handled && (e.key.length > 1 || accel)) || e.key === "Enter") e.preventDefault();
  });
  input.addEventListener("keyup", (e) => {
    if (!imeKey(e)) host.onKey?.(false, e.key, e.code, mods(e), false);
  });
  input.addEventListener("input", () => {
    if (composing) return;
    const text = input.value;
    input.value = "";
    if (text) host.onText?.(text);
  });
  input.addEventListener("compositionstart", () => { composing = true; });
  input.addEventListener("compositionupdate", (e) => host.onCompose?.(e.data));
  input.addEventListener("compositionend", (e) => {
    composing = false;
    input.value = "";
    if (e.data) host.onText?.(e.data);
    else host.onCompose?.("");
  });
  input.addEventListener("paste", (e) => {
    e.preventDefault();
    host.onPaste?.(e.clipboardData.getData("text/plain"));
  });
  input.focus({ preventScroll: true });

  globalThis.NV_HOST = host;
  return host;
}
