"""
Analisis Butir Soal - dengan UI Web
===================================
Program menghitung Validitas (point-biserial), Reliabilitas (KR-20),
Tingkat Kesukaran, dan Daya Pembeda dari data tes pilihan ganda.

Saat dijalankan, program akan:
  1. Mencetak rekapitulasi ke terminal (output asli, TIDAK diubah)
  2. Membuat file HTML berisi UI yang rapi lalu membukanya di browser

Data : 20 peserta x 20 butir (Kelompok 6)
Rumus & sumber :
  - Validitas      : r_pbis = ((Mp - Mt) / St) * sqrt(p/q)   [Arikunto 2018; Surapranata 2004]
                     valid jika r_pbis >= r_tabel (df=N-2=18, a=5% -> 0.444)
  - Reliabilitas   : KR-20 = (k/(k-1)) * (1 - Sum(p*q) / Var_total)  [Kuder & Richardson 1937]
  - Tingkat sukar  : P = B / JS   [Arikunto 2018; Depdiknas 2008]
  - Daya pembeda   : D = (BA/JA) - (BB/JB)  [Ebel & Frisbie 1991; Kelley 1939]
                     metode 9 atas / 9 bawah (2 peserta tengah dikeluarkan)

Cara menjalankan:
  python analisis_butir_soal_ui.py
"""

import math
import os
import json
import tempfile
import webbrowser

# ---------- DATA ----------
KEY = list("ABBACCACDEEDDCCBBAAE")
JAWABAN = {
    1:"BBABACCCBAEDDCCBBCBB", 2:"AABBACCACACDEECBBAAA", 3:"BBBACCCADEEDDCCBBCBB",
    4:"AABBADCADEEDDCCCBBAA", 5:"BABADCACDEEACCACDEEE", 6:"BBADCACDEEDDEDDBBCBB",
    7:"ABBADCACCACDEECBBAAC", 8:"CACDEEDDDEEDDCBBACBB", 9:"ABBCACDEEDDACCACDEEE",
    10:"ACCACDEEDEBBACCBBCBB", 11:"CCAADAAABBCABCDDEEAA", 12:"AACCAADAAABBCABCDDEE",
    13:"ACAAACAADBBCABCDDEEA", 14:"BBAAAABBACCACDEEDDCC", 15:"CACDEEDDCCBBAAAABBAC",
    16:"DCCBBAAAABBACCACDEED", 17:"EEDDEACCACDEEBBACACD", 18:"BBAACABCACDEEDDBBACC",
    19:"EBBAEABBACCCCACCACDE", 20:"ABAAEBACACDEEDDEDDBB",
}
R_TABEL = 0.444   # df = 18, alpha = 5%


def skor_matrix(key, jawaban):
    """Ubah jawaban menjadi matriks 1/0 (1 = sesuai kunci)."""
    siswa = sorted(jawaban)
    M = [[1 if jawaban[s][j] == key[j] else 0 for j in range(len(key))] for s in siswa]
    return M, siswa


def tingkat_kesukaran(M):
    n = len(M)
    P = [sum(M[i][j] for i in range(n)) / n for j in range(len(M[0]))]
    kat = ["Sukar" if p <= 0.30 else "Sedang" if p <= 0.70 else "Mudah" for p in P]
    return P, kat


def validitas(M):
    n, k = len(M), len(M[0])
    total = [sum(row) for row in M]
    mean = sum(total) / n
    St = math.sqrt(sum((x - mean) ** 2 for x in total) / n)   # SD populasi
    R, status = [], []
    for j in range(k):
        col = [M[i][j] for i in range(n)]
        nb = sum(col)
        p = nb / n
        q = 1 - p
        if 0 < p < 1:
            Mp = sum(total[i] for i in range(n) if col[i]) / nb
            r = ((Mp - mean) / St) * math.sqrt(p / q)
        else:
            r = 0.0
        R.append(r)
        status.append("Valid" if r >= R_TABEL else "Tidak Valid")
    return R, status


def reliabilitas_kr20(M):
    n, k = len(M), len(M[0])
    total = [sum(row) for row in M]
    mean = sum(total) / n
    Vt = sum((x - mean) ** 2 for x in total) / (n - 1)        # varians sampel
    spq = 0.0
    for j in range(k):
        p = sum(M[i][j] for i in range(n)) / n
        spq += p * (1 - p)
    kr = (k / (k - 1)) * (1 - spq / Vt) if Vt > 0 else 0.0
    kat = ("sangat rendah" if kr < 0.20 else "rendah" if kr < 0.40 else
           "sedang" if kr < 0.60 else "tinggi" if kr < 0.80 else "sangat tinggi")
    return kr, kat


def daya_pembeda(M, g=9):
    n, k = len(M), len(M[0])
    total = [sum(row) for row in M]
    urut = sorted(range(n), key=lambda i: total[i], reverse=True)
    atas, bawah = urut[:g], urut[n - g:]
    D, kat = [], []
    for j in range(k):
        BA = sum(M[i][j] for i in atas)
        BB = sum(M[i][j] for i in bawah)
        d = BA / g - BB / g
        D.append(d)
        kat.append("Sangat Baik" if d >= 0.40 else "Baik" if d >= 0.30 else
                   "Cukup" if d >= 0.20 else "Kurang")
    return D, kat


# ===================================================================
#  BAGIAN UI: membangun HTML dari hasil perhitungan
# ===================================================================
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Analisis Butir Soal &mdash; Khairatul Husna Tartila </title>
<style>
/* ============================================================
   RESET & BASE
   ============================================================ */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg:        #f0f2f5;
  --surface:   #ffffff;
  --surface2:  #f8f9fb;
  --border:    #e2e6ed;
  --ink:       #1a1d23;
  --ink2:      #4a5060;
  --ink3:      #8a90a0;

  --green:     #16a34a; --green-bg: #dcfce7; --green-dark: #14532d;
  --red:       #dc2626; --red-bg:   #fee2e2; --red-dark:   #7f1d1d;
  --amber:     #d97706; --amber-bg: #fef3c7; --amber-dark: #78350f;
  --blue:      #2563eb; --blue-bg:  #dbeafe; --blue-dark:  #1e3a8a;
  --gray:      #6b7280; --gray-bg:  #f3f4f6; --gray-dark:  #374151;
  --olive:     #4d7c0f; --olive-bg: #ecfccb;

  --shadow-sm: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  --shadow:    0 4px 12px rgba(0,0,0,.08), 0 2px 4px rgba(0,0,0,.05);
  --radius:    12px;
  --radius-sm: 8px;
}
body {
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  background: var(--bg);
  color: var(--ink);
  line-height: 1.6;
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}

/* ============================================================
   LAYOUT
   ============================================================ */
.page { max-width: 1080px; margin: 0 auto; padding: 32px 20px 60px; }

/* ============================================================
   HERO HEADER
   ============================================================ */
.hero {
  background: linear-gradient(135deg, #1e3a5f 0%, #1a6b45 100%);
  border-radius: 18px;
  padding: 36px 40px;
  margin-bottom: 28px;
  color: #fff;
  position: relative;
  overflow: hidden;
}
.hero::before {
  content: '';
  position: absolute; inset: 0;
  background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.04'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
}
.hero-badge {
  display: inline-flex; align-items: center; gap: 6px;
  background: rgba(255,255,255,.15);
  border: 1px solid rgba(255,255,255,.25);
  border-radius: 99px;
  padding: 4px 14px;
  font-size: 12px; font-weight: 600; letter-spacing: .06em;
  text-transform: uppercase; margin-bottom: 14px; color: rgba(255,255,255,.9);
}
.hero h1 { font-size: 28px; font-weight: 700; letter-spacing: -.025em; line-height: 1.2; }
.hero-sub { margin-top: 8px; font-size: 14px; color: rgba(255,255,255,.72); }
.hero-meta {
  display: flex; gap: 24px; flex-wrap: wrap;
  margin-top: 22px; padding-top: 20px;
  border-top: 1px solid rgba(255,255,255,.2);
  font-size: 13px; color: rgba(255,255,255,.8);
}
.hero-meta span b { color: #fff; font-weight: 600; }

/* ============================================================
   STAT CARDS ROW
   ============================================================ */
.stat-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 14px;
  margin-bottom: 24px;
}
.stat-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px 22px;
  box-shadow: var(--shadow-sm);
  display: flex; flex-direction: column; gap: 6px;
}
.stat-card .sc-label {
  font-size: 12px; font-weight: 600; letter-spacing: .05em;
  text-transform: uppercase; color: var(--ink3);
  display: flex; align-items: center; gap: 6px;
}
.stat-card .sc-label .icon {
  width: 28px; height: 28px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 15px;
}
.stat-card .sc-value {
  font-size: 32px; font-weight: 700; letter-spacing: -.04em;
  line-height: 1; color: var(--ink);
}
.stat-card .sc-value span { font-size: 16px; font-weight: 400; color: var(--ink3); }
.stat-card .sc-badge {
  display: inline-block;
  font-size: 11.5px; font-weight: 600;
  padding: 3px 10px; border-radius: 99px;
  text-transform: capitalize; width: fit-content;
}

/* ============================================================
   DISTRIBUTION BADGES (ringkasan kategori)
   ============================================================ */
.dist-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 14px;
  margin-bottom: 24px;
}
.dist-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px 20px;
  box-shadow: var(--shadow-sm);
}
.dist-card .dc-title {
  font-size: 11.5px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .06em; color: var(--ink3); margin-bottom: 10px;
}
.dist-list { display: flex; flex-direction: column; gap: 7px; }
.dist-item {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
}
.dist-item .di-label { font-size: 13px; color: var(--ink2); }
.dist-item .di-bar-wrap {
  flex: 1; height: 7px; background: var(--bg);
  border-radius: 99px; overflow: hidden;
}
.dist-item .di-bar { height: 100%; border-radius: 99px; }
.dist-item .di-count {
  font-size: 13px; font-weight: 600; min-width: 26px; text-align: right;
  color: var(--ink);
}

/* ============================================================
   PANEL / SECTION
   ============================================================ */
.section { margin-bottom: 24px; }
.section-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 12px; gap: 12px; flex-wrap: wrap;
}
.section-title {
  font-size: 16px; font-weight: 700; color: var(--ink);
  display: flex; align-items: center; gap: 8px;
}
.section-title .stag {
  font-size: 11px; font-weight: 600; letter-spacing: .05em;
  text-transform: uppercase; padding: 2px 9px; border-radius: 99px;
  background: var(--blue-bg); color: var(--blue-dark);
}

/* filter chips */
.filter-row { display: flex; gap: 7px; flex-wrap: wrap; align-items: center; }
.filter-chip {
  cursor: pointer;
  border: 1.5px solid var(--border);
  background: var(--surface);
  border-radius: 99px;
  padding: 4px 13px;
  font-size: 12px; font-weight: 600; color: var(--ink2);
  transition: all .15s;
  user-select: none;
}
.filter-chip:hover { border-color: var(--blue); color: var(--blue); }
.filter-chip.active {
  background: var(--blue); border-color: var(--blue); color: #fff;
}

/* ============================================================
   TABLE PANEL
   ============================================================ */
.table-panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}
.table-scroll { overflow-x: auto; }
table {
  width: 100%; border-collapse: collapse;
  font-size: 13.5px;
}
thead th {
  background: var(--surface2);
  border-bottom: 2px solid var(--border);
  padding: 12px 14px;
  text-align: left;
  font-size: 11.5px; font-weight: 700;
  text-transform: uppercase; letter-spacing: .06em;
  color: var(--ink3); white-space: nowrap;
  cursor: pointer; user-select: none;
  transition: color .15s;
}
thead th:hover { color: var(--blue); }
thead th.asc::after  { content: ' ▲'; }
thead th.desc::after { content: ' ▼'; }
thead th.no-sort { cursor: default; }
thead th.no-sort:hover { color: var(--ink3); }
th.r, td.r { text-align: right; font-variant-numeric: tabular-nums; }
th.c, td.c { text-align: center; }
tbody tr { transition: background .12s; }
tbody tr:hover { background: #f5f7fa; }
tbody tr.hidden { display: none; }
tbody td {
  padding: 11px 14px;
  border-bottom: 1px solid #f0f2f5;
  vertical-align: middle;
}
tbody tr:last-child td { border-bottom: none; }
td.no-cell {
  font-weight: 700; font-size: 15px; color: var(--ink2);
  width: 46px;
}

/* value with bar */
.val-bar { display: flex; align-items: center; gap: 8px; justify-content: flex-end; }
.val-bar .vb-num { font-variant-numeric: tabular-nums; font-weight: 500; min-width: 42px; text-align: right; }
.val-bar .vb-track {
  width: 56px; height: 6px; background: #e9ebef;
  border-radius: 99px; overflow: hidden; flex-shrink: 0;
}
.val-bar .vb-fill { height: 100%; border-radius: 99px; }
.neg-val { color: var(--red); font-weight: 600; }

/* pill badges */
.pill {
  display: inline-block; font-size: 12px; font-weight: 600;
  padding: 4px 12px; border-radius: 99px; white-space: nowrap;
  line-height: 1.4;
}

/* tooltip */
[data-tip] { position: relative; cursor: help; }
[data-tip]::after {
  content: attr(data-tip);
  position: absolute; bottom: calc(100% + 7px); left: 50%;
  transform: translateX(-50%);
  background: #1a1d23; color: #fff;
  font-size: 11.5px; font-weight: 400; line-height: 1.4;
  padding: 6px 11px; border-radius: 8px;
  white-space: nowrap; pointer-events: none;
  opacity: 0; transition: opacity .18s;
  z-index: 100;
}
[data-tip]:hover::after { opacity: 1; }

/* ============================================================
   HIGHLIGHT ROWS
   ============================================================ */
tr.row-valid   { }
tr.row-invalid { background: #fffafa; }
tr.row-invalid td { color: #6b3535; }
tr.row-invalid:hover { background: #fff0f0; }

/* ============================================================
   INFO BOX
   ============================================================ */
.info-box {
  background: var(--blue-bg); border: 1px solid #bfdbfe;
  border-radius: var(--radius-sm);
  padding: 14px 18px; font-size: 13.5px; color: var(--blue-dark);
  display: flex; gap: 12px; align-items: flex-start;
}
.info-box .ib-icon { font-size: 18px; flex-shrink: 0; margin-top: 1px; }
.info-box b { font-weight: 700; }

/* ============================================================
   ACCORDION (metodologi)
   ============================================================ */
.accordion {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  margin-bottom: 24px;
  box-shadow: var(--shadow-sm);
}
.accordion-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 22px; cursor: pointer; user-select: none;
  font-weight: 700; font-size: 14.5px; color: var(--ink);
  transition: background .15s;
}
.accordion-header:hover { background: var(--surface2); }
.accordion-header .ah-icon { font-size: 16px; transition: transform .25s; }
.accordion-header.open .ah-icon { transform: rotate(180deg); }
.accordion-body {
  display: none;
  padding: 0 22px 22px;
  border-top: 1px solid var(--border);
}
.accordion-body.open { display: block; }
.method-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px; margin-top: 16px;
}
.method-card {
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 16px 18px;
}
.method-card .mc-head {
  font-size: 12px; font-weight: 700; letter-spacing: .05em;
  text-transform: uppercase; color: var(--blue-dark); margin-bottom: 8px;
}
.method-card .mc-formula {
  font-family: 'Courier New', monospace;
  font-size: 12.5px; background: #fff;
  border: 1px solid var(--border); border-radius: 6px;
  padding: 7px 10px; margin-bottom: 8px; color: var(--ink);
  line-height: 1.5;
}
.method-card .mc-desc { font-size: 12.5px; color: var(--ink2); line-height: 1.6; }
.method-card .mc-criteria { margin-top: 8px; }
.crit-row { display: flex; gap: 6px; align-items: center; font-size: 12px; margin-top: 5px; }
.crit-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }

/* ============================================================
   FOOTER
   ============================================================ */
.footer {
  margin-top: 32px; font-size: 12px; color: var(--ink3);
  border-top: 1px solid var(--border); padding-top: 18px;
  line-height: 1.8;
}

/* ============================================================
   PRINT
   ============================================================ */
@media print {
  body { background: #fff; }
  .hero { background: #1e3a5f !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .filter-row, .accordion-header .ah-icon { display: none; }
  .accordion-body { display: block !important; }
  tbody tr.hidden { display: table-row !important; }
}

@media (max-width: 600px) {
  .hero { padding: 24px 20px; }
  .hero h1 { font-size: 22px; }
  .hero-meta { gap: 14px; }
  .stat-card .sc-value { font-size: 26px; }
}
</style>
</head>
<body>
<div class="page">

  <!-- ── HERO ─────────────────────────────────────────────── -->
  <div class="hero">
    <div class="hero-badge">&#128203; Khairatul Husna Tartila &middot; Evaluasi Pembelajaran</div>
    <h1>Analisis Butir Soal</h1>
    <div class="hero-sub">Validitas &middot; Reliabilitas (KR-20) &middot; Tingkat Kesukaran &middot; Daya Pembeda</div>
    <div class="hero-meta">
      <span><b>__N__ peserta</b></span>
      <span><b>__K__ butir soal</b></span>
      <span>r-tabel = <b>__RTABEL__</b> (df = __DF__, &alpha; = 5%)</span>
      <span>Metode kelompok: <b>9 atas / 9 bawah</b></span>
    </div>
  </div>

  <!-- ── STAT CARDS ───────────────────────────────────────── -->
  <div class="stat-row">
    <div class="stat-card">
      <div class="sc-label">
        <div class="icon" style="background:#dcfce7;">&#10003;</div>
        Butir Valid
      </div>
      <div class="sc-value">__NVALID__ <span>/ __K__</span></div>
      <div class="sc-badge" style="background:#dcfce7;color:#14532d;">__PCT_VALID__% lolos r-tabel</div>
    </div>
    <div class="stat-card">
      <div class="sc-label">
        <div class="icon" style="background:#dbeafe;">&#128200;</div>
        Reliabilitas KR-20
      </div>
      <div class="sc-value">__KR__</div>
      <div class="sc-badge" style="background:__KRBG__;color:__KRFG__;">__KRKAT__</div>
    </div>
    <div class="stat-card">
      <div class="sc-label">
        <div class="icon" style="background:#fef3c7;">&#127919;</div>
        Rata-rata Skor
      </div>
      <div class="sc-value">__RATA__ <span>/ __K__</span></div>
      <div class="sc-badge" style="background:#fef3c7;color:#78350f;">__PCT_SCORE__% dijawab benar</div>
    </div>
    <div class="stat-card">
      <div class="sc-label">
        <div class="icon" style="background:#ede9fe;">&#128290;</div>
        Butir Tidak Valid
      </div>
      <div class="sc-value">__NINVALID__ <span>/ __K__</span></div>
      <div class="sc-badge" style="background:#fee2e2;color:#7f1d1d;">perlu ditinjau ulang</div>
    </div>
  </div>

  <!-- ── DISTRIBUTION ─────────────────────────────────────── -->
  <div class="dist-row">
    <div class="dist-card">
      <div class="dc-title">&#128200; Tingkat Kesukaran</div>
      <div class="dist-list" id="dist-tk"></div>
    </div>
    <div class="dist-card">
      <div class="dc-title">&#9889; Daya Pembeda</div>
      <div class="dist-list" id="dist-dp"></div>
    </div>
    <div class="dist-card">
      <div class="dc-title">&#10003; Validitas</div>
      <div class="dist-list" id="dist-val"></div>
    </div>
  </div>

  <!-- ── INFO BOX ──────────────────────────────────────────── -->
  <div class="info-box" style="margin-bottom:20px;">
    <div class="ib-icon">&#128161;</div>
    <div>
      <b>Butir valid (__NVALID__ butir):</b> __VALIDLIST__<br>
      Butir dinyatakan valid apabila r-pbis &ge; r-tabel (<b>__RTABEL__</b>).
      Klik kepala kolom untuk mengurutkan tabel.
      Gunakan filter di bawah untuk menyaring kategori tertentu.
    </div>
  </div>

  <!-- ── TABEL UTAMA ───────────────────────────────────────── -->
  <div class="section">
    <div class="section-header">
      <div class="section-title">
        Tabel Rekapitulasi
        <span class="stag">__K__ butir</span>
      </div>
      <div class="filter-row">
        <span style="font-size:12px;color:var(--ink3);font-weight:600;">Filter:</span>
        <div class="filter-chip active" data-filter="all">Semua</div>
        <div class="filter-chip" data-filter="valid">Valid</div>
        <div class="filter-chip" data-filter="invalid">Tidak Valid</div>
        <div class="filter-chip" data-filter="sukar">Sukar</div>
        <div class="filter-chip" data-filter="sedang">Sedang</div>
        <div class="filter-chip" data-filter="mudah">Mudah</div>
      </div>
    </div>

    <div class="table-panel">
      <div class="table-scroll">
        <table id="main-table">
          <thead>
            <tr>
              <th class="no-sort c" style="width:46px;">No</th>
              <th class="r" data-col="p">
                <span data-tip="Tingkat kesukaran: proporsi peserta yang menjawab benar">P &#9432;</span>
              </th>
              <th data-col="tk">
                <span data-tip="Sukar: P &le; 0.30 | Sedang: 0.31–0.70 | Mudah: P &gt; 0.70">Tingkat Kesukaran &#9432;</span>
              </th>
              <th class="r" data-col="r">
                <span data-tip="r-pbis: korelasi point-biserial. Valid jika &ge; __RTABEL__">r-pbis &#9432;</span>
              </th>
              <th data-col="val">
                <span data-tip="Butir valid jika r-pbis &ge; r-tabel (__RTABEL__)">Validitas &#9432;</span>
              </th>
              <th class="r" data-col="d">
                <span data-tip="Daya pembeda: seberapa baik soal membedakan siswa pandai dan kurang pandai">D &#9432;</span>
              </th>
              <th data-col="dp">
                <span data-tip="Sangat Baik: D &ge; 0.40 | Baik: 0.30–0.39 | Cukup: 0.20–0.29 | Kurang: &lt; 0.20">Daya Pembeda &#9432;</span>
              </th>
            </tr>
          </thead>
          <tbody>
            __ROWS__
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- ── METODOLOGI (accordion) ────────────────────────────── -->
  <div class="accordion">
    <div class="accordion-header" onclick="toggleAccordion(this)">
      &#128218;&nbsp; Metodologi &amp; Kriteria Penilaian
      <span class="ah-icon">&#9660;</span>
    </div>
    <div class="accordion-body">
      <div class="method-grid">
        <div class="method-card">
          <div class="mc-head">&#128200; Tingkat Kesukaran</div>
          <div class="mc-formula">P = B / JS</div>
          <div class="mc-desc">B = jumlah peserta menjawab benar, JS = jumlah seluruh peserta.</div>
          <div class="mc-criteria">
            <div class="crit-row"><div class="crit-dot" style="background:#dc2626;"></div><span>Sukar: P &le; 0.30</span></div>
            <div class="crit-row"><div class="crit-dot" style="background:#d97706;"></div><span>Sedang: 0.31 &ndash; 0.70</span></div>
            <div class="crit-row"><div class="crit-dot" style="background:#16a34a;"></div><span>Mudah: P &gt; 0.70</span></div>
          </div>
          <div class="mc-desc" style="margin-top:8px;font-size:11.5px;color:#8a90a0;">Sumber: Arikunto (2018); Depdiknas (2008)</div>
        </div>
        <div class="method-card">
          <div class="mc-head">&#10003; Validitas (r-pbis)</div>
          <div class="mc-formula">r = ((Mp&minus;Mt)/St) &times; &radic;(p/q)</div>
          <div class="mc-desc">Mp = rata skor peserta benar, Mt = rata skor total, St = SD total.</div>
          <div class="mc-criteria">
            <div class="crit-row"><div class="crit-dot" style="background:#16a34a;"></div><span>Valid: r-pbis &ge; __RTABEL__ (df=__DF__, &alpha;=5%)</span></div>
            <div class="crit-row"><div class="crit-dot" style="background:#dc2626;"></div><span>Tidak Valid: r-pbis &lt; __RTABEL__</span></div>
          </div>
          <div class="mc-desc" style="margin-top:8px;font-size:11.5px;color:#8a90a0;">Sumber: Arikunto (2018); Surapranata (2004)</div>
        </div>
        <div class="method-card">
          <div class="mc-head">&#9889; Daya Pembeda</div>
          <div class="mc-formula">D = (BA/JA) &minus; (BB/JB)</div>
          <div class="mc-desc">BA/BB = benar kelompok atas/bawah, JA/JB = jumlah kelompok (9 peserta).</div>
          <div class="mc-criteria">
            <div class="crit-row"><div class="crit-dot" style="background:#16a34a;"></div><span>Sangat Baik: D &ge; 0.40</span></div>
            <div class="crit-row"><div class="crit-dot" style="background:#4d7c0f;"></div><span>Baik: 0.30 &ndash; 0.39</span></div>
            <div class="crit-row"><div class="crit-dot" style="background:#d97706;"></div><span>Cukup: 0.20 &ndash; 0.29</span></div>
            <div class="crit-row"><div class="crit-dot" style="background:#6b7280;"></div><span>Kurang: &lt; 0.20</span></div>
          </div>
          <div class="mc-desc" style="margin-top:8px;font-size:11.5px;color:#8a90a0;">Sumber: Ebel &amp; Frisbie (1991); Kelley (1939)</div>
        </div>
        <div class="method-card">
          <div class="mc-head">&#128200; Reliabilitas (KR-20)</div>
          <div class="mc-formula">KR-20 = (k/(k&minus;1)) &times; (1 &minus; &Sigma;pq / Vt)</div>
          <div class="mc-desc">k = jumlah butir, Vt = varians total skor.</div>
          <div class="mc-criteria">
            <div class="crit-row"><div class="crit-dot" style="background:#16a34a;"></div><span>Sangat Tinggi: 0.80 &ndash; 1.00</span></div>
            <div class="crit-row"><div class="crit-dot" style="background:#4d7c0f;"></div><span>Tinggi: 0.60 &ndash; 0.79</span></div>
            <div class="crit-row"><div class="crit-dot" style="background:#d97706;"></div><span>Sedang: 0.40 &ndash; 0.59</span></div>
            <div class="crit-row"><div class="crit-dot" style="background:#dc2626;"></div><span>Rendah: 0.00 &ndash; 0.39</span></div>
          </div>
          <div class="mc-desc" style="margin-top:8px;font-size:11.5px;color:#8a90a0;">Sumber: Kuder &amp; Richardson (1937)</div>
        </div>
      </div>
    </div>
  </div>

  <div class="footer">
    Rumus: r-pbis [Arikunto 2018; Surapranata 2004] &middot; KR-20 [Kuder &amp; Richardson 1937] &middot;
    P = B/JS [Arikunto 2018; Depdiknas 2008] &middot; D = (BA/JA)&minus;(BB/JB) [Ebel &amp; Frisbie 1991; Kelley 1939]
    &middot; Metode: 9 atas / 9 bawah (2 peserta tengah dikeluarkan).
  </div>
</div>

<!-- ══════════════════════════════════════════════════════════
     DATA & INTERAKTIVITAS
     ══════════════════════════════════════════════════════════ -->
<script>
// ── data baris disuntikkan dari Python ──────────────────────
const ROWS_DATA = __JSON_DATA__;

// ── distribusi ──────────────────────────────────────────────
function renderDist(id, items, colorMap) {
  const el = document.getElementById(id);
  const total = items.reduce((s,x) => s + x.count, 0);
  el.innerHTML = items.map(item => {
    const pct = total ? Math.round(item.count / total * 100) : 0;
    return `<div class="dist-item">
      <div class="di-label" style="min-width:80px;">${item.label}</div>
      <div class="di-bar-wrap">
        <div class="di-bar" style="width:${pct}%;background:${colorMap[item.label]||'#ccc'};"></div>
      </div>
      <div class="di-count">${item.count}</div>
    </div>`;
  }).join('');
}

const tkCounts = {};
const dpCounts = {};
const valCounts = {};
ROWS_DATA.forEach(r => {
  tkCounts[r.tk]  = (tkCounts[r.tk]  || 0) + 1;
  dpCounts[r.dp]  = (dpCounts[r.dp]  || 0) + 1;
  valCounts[r.val] = (valCounts[r.val]|| 0) + 1;
});

renderDist('dist-tk',
  [['Mudah','Sedang','Sukar'].map(k => ({label:k, count: tkCounts[k]||0}))].flat(),
  {Mudah:'#16a34a', Sedang:'#d97706', Sukar:'#dc2626'}
);
renderDist('dist-dp',
  [['Sangat Baik','Baik','Cukup','Kurang'].map(k => ({label:k, count: dpCounts[k]||0}))].flat(),
  {'Sangat Baik':'#16a34a', Baik:'#4d7c0f', Cukup:'#d97706', Kurang:'#6b7280'}
);
renderDist('dist-val',
  [['Valid','Tidak Valid'].map(k => ({label:k, count: valCounts[k]||0}))].flat(),
  {Valid:'#16a34a', 'Tidak Valid':'#dc2626'}
);

// ── filter chip ──────────────────────────────────────────────
document.querySelectorAll('.filter-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    const f = chip.dataset.filter;
    document.querySelectorAll('#main-table tbody tr').forEach(tr => {
      if (f === 'all') { tr.classList.remove('hidden'); return; }
      const d = tr.dataset;
      const show = (f === 'valid'   && d.val === 'Valid')
                || (f === 'invalid' && d.val === 'Tidak Valid')
                || (f === 'sukar'   && d.tk  === 'Sukar')
                || (f === 'sedang'  && d.tk  === 'Sedang')
                || (f === 'mudah'   && d.tk  === 'Mudah');
      tr.classList.toggle('hidden', !show);
    });
  });
});

// ── sortir kolom ──────────────────────────────────────────────
let sortCol = null, sortDir = 1;
document.querySelectorAll('thead th[data-col]').forEach(th => {
  th.addEventListener('click', () => {
    const col = th.dataset.col;
    if (sortCol === col) { sortDir *= -1; }
    else { sortCol = col; sortDir = 1; }
    document.querySelectorAll('thead th').forEach(t => t.classList.remove('asc','desc'));
    th.classList.add(sortDir === 1 ? 'asc' : 'desc');

    const tbody = document.querySelector('#main-table tbody');
    const rows = [...tbody.querySelectorAll('tr')];
    rows.sort((a, b) => {
      let va = a.dataset[col], vb = b.dataset[col];
      if (!isNaN(parseFloat(va))) { va = parseFloat(va); vb = parseFloat(vb); }
      return (va < vb ? -1 : va > vb ? 1 : 0) * sortDir;
    });
    rows.forEach(r => tbody.appendChild(r));
  });
});

// ── accordion ────────────────────────────────────────────────
function toggleAccordion(header) {
  header.classList.toggle('open');
  const body = header.nextElementSibling;
  body.classList.toggle('open');
}
</script>
</body>
</html>
"""

# ── warna pill ──────────────────────────────────────────────────────────────
_TK_COLOR  = {"Sukar":      ("#fee2e2", "#7f1d1d"),
               "Sedang":     ("#fef3c7", "#78350f"),
               "Mudah":      ("#dcfce7", "#14532d")}
_DP_COLOR  = {"Sangat Baik":("#dcfce7", "#14532d"),
               "Baik":       ("#ecfccb", "#3a5c09"),
               "Cukup":      ("#fef3c7", "#78350f"),
               "Kurang":     ("#f3f4f6", "#374151")}
_VAL_COLOR = {"Valid":       ("#dcfce7", "#14532d"),
               "Tidak Valid":("#fee2e2", "#7f1d1d")}

# warna KR-20 badge
_KR_COLOR = {
    "sangat rendah": ("#fee2e2", "#7f1d1d"),
    "rendah":        ("#fee2e2", "#991b1b"),
    "sedang":        ("#fef3c7", "#78350f"),
    "tinggi":        ("#dcfce7", "#14532d"),
    "sangat tinggi": ("#dcfce7", "#065f46"),
}


def _pill(text, palette):
    bg, fg = palette[text]
    return f'<span class="pill" style="background:{bg};color:{fg};">{text}</span>'


def _bar(value, lo, hi, color):
    """Hasilkan mini bar relatif terhadap rentang [lo, hi]."""
    clamped = max(lo, min(hi, value))
    pct = (clamped - lo) / (hi - lo) * 100 if hi != lo else 0
    return (f'<div class="val-bar">'
            f'<div class="vb-num">{value:.3f}</div>'
            f'<div class="vb-track"><div class="vb-fill" style="width:{pct:.0f}%;background:{color};"></div></div>'
            f'</div>')


def buat_html(P, tk, R, val, D, dp, kr, krkat, valid, rata, n, k):
    # data JSON untuk JS
    json_data = json.dumps([
        {"no": j + 1, "p": round(P[j], 4), "tk": tk[j],
         "r": round(R[j], 4), "val": val[j],
         "d": round(D[j], 4), "dp": dp[j]}
        for j in range(k)
    ])

    rows = []
    for j in range(k):
        row_cls = "row-valid" if val[j] == "Valid" else "row-invalid"
        r_neg   = ' neg-val' if R[j] < 0 else ''
        d_neg   = ' neg-val' if D[j] < 0 else ''
        r_str   = f'<span class="{r_neg.strip()}">{R[j]:.3f}</span>' if R[j] < 0 else f'{R[j]:.3f}'
        rows.append(
            f'<tr class="{row_cls}" '
            f'data-no="{j+1}" data-p="{P[j]:.4f}" data-tk="{tk[j]}" '
            f'data-r="{R[j]:.4f}" data-val="{val[j]}" '
            f'data-d="{D[j]:.4f}" data-dp="{dp[j]}">'
            f'<td class="no-cell c">{j + 1}</td>'
            f'<td class="r">{_bar(P[j], 0, 1, "#2563eb")}</td>'
            f'<td>{_pill(tk[j], _TK_COLOR)}</td>'
            f'<td class="r">{r_str}</td>'
            f'<td>{_pill(val[j], _VAL_COLOR)}</td>'
            f'<td class="r {d_neg.strip()}">{D[j]:.3f}</td>'
            f'<td>{_pill(dp[j], _DP_COLOR)}</td>'
            '</tr>'
        )

    kr_bg, kr_fg = _KR_COLOR.get(krkat, ("#f3f4f6", "#374151"))
    pct_valid = round(len(valid) / k * 100)
    pct_score = round(rata / k * 100)

    html = HTML_TEMPLATE
    html = html.replace("__ROWS__", "\n            ".join(rows))
    html = html.replace("__JSON_DATA__", json_data)
    html = html.replace("__N__", str(n))
    html = html.replace("__K__", str(k))
    html = html.replace("__NVALID__", str(len(valid)))
    html = html.replace("__NINVALID__", str(k - len(valid)))
    html = html.replace("__KR__", f"{kr:.4f}")
    html = html.replace("__KRKAT__", krkat)
    html = html.replace("__KRBG__", kr_bg)
    html = html.replace("__KRFG__", kr_fg)
    html = html.replace("__RATA__", f"{rata:.2f}")
    html = html.replace("__RTABEL__", f"{R_TABEL}")
    html = html.replace("__DF__", str(n - 2))
    html = html.replace("__VALIDLIST__", ", ".join(str(v) for v in valid))
    html = html.replace("__PCT_VALID__", str(pct_valid))
    html = html.replace("__PCT_SCORE__", str(pct_score))
    return html


def main():
    M, siswa = skor_matrix(KEY, JAWABAN)
    P, tk = tingkat_kesukaran(M)
    R, val = validitas(M)
    D, dp = daya_pembeda(M, g=9)
    kr, krkat = reliabilitas_kr20(M)

    # ---------- OUTPUT TERMINAL (TIDAK DIUBAH) ----------
    print("REKAPITULASI ANALISIS BUTIR SOAL\n" + "=" * 70)
    print(f"{'No':>3} {'P':>5} {'TK':<7} {'r_pbis':>7} {'Validitas':<12} {'D':>7} {'Daya Pembeda':<12}")
    print("-" * 70)
    for j in range(len(KEY)):
        print(f"{j+1:>3} {P[j]:>5.2f} {tk[j]:<7} {R[j]:>7.3f} {val[j]:<12} {D[j]:>7.3f} {dp[j]:<12}")
    print("-" * 70)
    valid = [j + 1 for j in range(len(KEY)) if val[j] == "Valid"]
    print(f"Butir valid ({len(valid)}): {valid}")
    print(f"KR-20 = {kr:.4f}  -> kategori {krkat}")
    skor = [sum(r) for r in M]
    rata = sum(skor) / len(skor)
    print(f"Rata-rata skor = {rata:.2f} dari {len(KEY)}")

    # ---------- OUTPUT UI WEB ----------
    html = buat_html(P, tk, R, val, D, dp, kr, krkat, valid, rata, len(siswa), len(KEY))
    out_path = os.path.join(tempfile.gettempdir(), "analisis_butir_soal.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("\n" + "=" * 70)
    print(f"UI tersimpan di : {out_path}")
    print("Membuka di browser...")
    webbrowser.open("file://" + os.path.abspath(out_path))


if __name__ == "__main__":
    main()
