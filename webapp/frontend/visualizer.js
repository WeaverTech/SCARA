/* Wizualizacja 2D SCARA (widok z gory) na <canvas>.
   Geometria zgodna z firmware: L1=139.928, L2=140.0, kolumna w (-165, 0),
   strefa wykluczenia R=45, zasieg 0.072..279.928 mm. */

const VIZ = (() => {
  const L1 = 139.928, L2 = 140.0, COL_X = -165.0, EXCL_R = 45.0;
  const R_MAX = 279.928;

  const canvas = document.getElementById("canvas");
  const ctx = canvas.getContext("2d");
  let scale = 1, cx = 0, cy = 0;
  let trail = [];

  function worldToScreen(x, y) {
    // Uklad robota: X w prawo, Y w gore -> ekran: Y odwrocone.
    return [cx + x * scale, cy - y * scale];
  }

  function computeTransform() {
    const margin = 30;
    const worldW = (R_MAX + 20) - (COL_X - EXCL_R - 20);
    const worldH = 2 * (R_MAX + 20);
    scale = Math.min((canvas.width - 2 * margin) / worldW,
                     (canvas.height - 2 * margin) / worldH);
    cx = margin + (-(COL_X - EXCL_R - 20)) * scale;
    cy = canvas.height / 2;
  }

  function circle(x, y, r, stroke, fill, lw = 1.5) {
    const [sx, sy] = worldToScreen(x, y);
    ctx.beginPath();
    ctx.arc(sx, sy, r * scale, 0, 2 * Math.PI);
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw; ctx.stroke(); }
  }

  function dot(x, y, rpx, color) {
    const [sx, sy] = worldToScreen(x, y);
    ctx.beginPath();
    ctx.arc(sx, sy, rpx, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();
  }

  function line(x0, y0, x1, y1, color, lwpx) {
    const [a, b] = worldToScreen(x0, y0);
    const [c, d] = worldToScreen(x1, y1);
    ctx.beginPath();
    ctx.moveTo(a, b);
    ctx.lineTo(c, d);
    ctx.strokeStyle = color;
    ctx.lineWidth = lwpx;
    ctx.lineCap = "round";
    ctx.stroke();
  }

  function draw(status, points) {
    computeTransform();
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Siatka co 50 mm.
    ctx.strokeStyle = "#141c24";
    ctx.lineWidth = 1;
    for (let gx = -250; gx <= 300; gx += 50) {
      const [sx] = worldToScreen(gx, 0);
      ctx.beginPath(); ctx.moveTo(sx, 0); ctx.lineTo(sx, canvas.height); ctx.stroke();
    }
    for (let gy = -300; gy <= 300; gy += 50) {
      const [, sy] = worldToScreen(0, gy);
      ctx.beginPath(); ctx.moveTo(0, sy); ctx.lineTo(canvas.width, sy); ctx.stroke();
    }

    // Obszar roboczy (pierscien) + strefa wykluczenia kolumny.
    circle(0, 0, R_MAX, "#2a3644", "rgba(56,182,255,0.05)");
    circle(COL_X, 0, EXCL_R, "#ff5b5b", "rgba(255,91,91,0.12)");
    // Kolumna Z.
    const [colx, coly] = worldToScreen(COL_X, 0);
    ctx.fillStyle = "#394856";
    ctx.fillRect(colx - 10, coly - 10, 20, 20);

    // Zapisane punkty.
    (points || []).forEach(p => {
      dot(p.x, p.y, 4, "#ffb347");
      const [sx, sy] = worldToScreen(p.x, p.y);
      ctx.fillStyle = "#8296ab";
      ctx.font = "11px sans-serif";
      ctx.fillText(p.name, sx + 7, sy - 5);
    });

    if (!status || status.j1 === undefined) return;

    // FK dla lokcia i TCP.
    const t1 = status.j1 * Math.PI / 180;
    const t12 = (status.j1 + status.j2) * Math.PI / 180;
    const ex = L1 * Math.cos(t1), ey = L1 * Math.sin(t1);
    const tx = ex + L2 * Math.cos(t12), ty = ey + L2 * Math.sin(t12);

    // Slad TCP.
    trail.push([tx, ty]);
    if (trail.length > 400) trail.shift();
    ctx.beginPath();
    trail.forEach(([px, py], i) => {
      const [sx, sy] = worldToScreen(px, py);
      if (i === 0) ctx.moveTo(sx, sy); else ctx.lineTo(sx, sy);
    });
    ctx.strokeStyle = "rgba(56,182,255,0.35)";
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Ramie.
    line(0, 0, ex, ey, "#dbe4ee", 7);
    line(ex, ey, tx, ty, "#aab9c9", 5);
    dot(0, 0, 8, "#38b6ff");         // bark
    dot(ex, ey, 6, "#dbe4ee");       // lokiec
    dot(tx, ty, 6, status.grip ? "#ff5b5b" : "#34d17b");  // TCP / gripper

    // Wskaznik kata narzedzia.
    const phi = t12 + (status.tool * Math.PI / 180);
    line(tx, ty, tx + 18 * Math.cos(phi), ty + 18 * Math.sin(phi), "#ffb347", 2);
  }

  function clearTrail() { trail = []; }

  return { draw, clearTrail };
})();
