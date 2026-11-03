"""PDF reports (reportlab), styled after the advancements.scouting.org Report Builder PDF."""
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from advancement import CHITS, RANKS, SECTIONS, is_needed, req_key

BLUE = colors.HexColor("#2196F3")
GREEN = colors.HexColor("#43A047")
GOLD = colors.HexColor("#F2B705")
INK = colors.HexColor("#222222")
MUTED = colors.HexColor("#666666")
GRID = colors.HexColor("#BDBDBD")
SECTION_BG = colors.HexColor("#EEF1F5")
RANKDONE_BG = colors.HexColor("#E6E6E6")

CAT = {
    "D": ("Discuss", colors.HexColor("#6A4C93")),
    "O": ("Outdoor", colors.HexColor("#2E7D32")),
    "S": ("On Own", colors.HexColor("#D97706")),
    "N": ("N/A", colors.HexColor("#78909C")),
}

ST = {
    "title": ParagraphStyle("title", fontName="Helvetica", fontSize=20, leading=24, alignment=1, textColor=INK),
    "subtitle": ParagraphStyle("subtitle", fontName="Helvetica", fontSize=12, leading=15, alignment=1, textColor=MUTED),
    "gen": ParagraphStyle("gen", fontName="Helvetica", fontSize=9.5, leading=12, textColor=INK),
    "h": ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=INK),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=9, leading=11, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=INK),
    "small": ParagraphStyle("small", fontName="Helvetica", fontSize=8, leading=10, textColor=INK),
    "smallc": ParagraphStyle("smallc", fontName="Helvetica", fontSize=8, leading=10, textColor=INK, alignment=1),
    "head": ParagraphStyle("head", fontName="Helvetica", fontSize=8.5, leading=10.5, textColor=INK, alignment=1),
}


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Icon(Flowable):
    """Status icon drawn centered in its cell (check / started triangle / award ribbon / grey check / ?)."""

    def __init__(self, kind, size=11):
        super().__init__()
        self.kind, self.size = kind, size

    def wrap(self, aw, ah):
        self._aw = aw
        return aw, self.size

    def draw(self):
        c, s = self.canv, self.size
        c.saveState()
        c.translate((self._aw - s) / 2.0, 0)
        if self.kind == "done":
            c.setFillColor(BLUE)
            c.roundRect(0, 0, s, s, 2, stroke=0, fill=1)
            c.setStrokeColor(colors.white)
            c.setLineWidth(1.5)
            c.setLineCap(1)
            p = c.beginPath()
            p.moveTo(s * .24, s * .52); p.lineTo(s * .43, s * .3); p.lineTo(s * .78, s * .72)
            c.drawPath(p, stroke=1, fill=0)
        elif self.kind == "partial":
            c.setFillColor(GREEN)
            p = c.beginPath()
            p.moveTo(0, 0); p.lineTo(s, 0); p.lineTo(s, s); p.close()
            c.drawPath(p, stroke=0, fill=1)
        elif self.kind == "award":
            import math
            pts = []
            for i in range(10):
                r = s * (.52 if i % 2 == 0 else .22)
                a = math.pi / 2 + i * math.pi / 5
                pts.append((s / 2 + r * math.cos(a), s * .47 + r * math.sin(a)))
            p = c.beginPath()
            p.moveTo(*pts[0])
            for x, y in pts[1:]:
                p.lineTo(x, y)
            p.close()
            c.setFillColor(GOLD)
            c.setStrokeColor(colors.HexColor("#C98A00"))
            c.setLineWidth(0.5)
            c.drawPath(p, stroke=1, fill=1)
        elif self.kind == "rankdone":
            c.setStrokeColor(colors.HexColor("#9E9E9E"))
            c.setLineWidth(1.3)
            p = c.beginPath()
            p.moveTo(s * .24, s * .52); p.lineTo(s * .43, s * .3); p.lineTo(s * .78, s * .72)
            c.drawPath(p, stroke=1, fill=0)
        elif self.kind == "unknown":
            c.setFillColor(MUTED)
            c.setFont("Helvetica", s * .9)
            c.drawCentredString(s / 2, s * .15, "?")
        c.restoreState()


class Pill(Flowable):
    """Colored category label, e.g. a purple 'Discuss' tag."""

    def __init__(self, cat, width=0.62 * inch, height=12):
        super().__init__()
        self.cat, self.w, self.h = cat, width, height

    def wrap(self, aw, ah):
        self._aw = aw
        return aw, self.h

    def draw(self):
        c = self.canv
        w = min(self.w, self._aw)
        c.saveState()
        c.translate((self._aw - w) / 2.0, 0)
        if self.cat in CAT:
            label, col = CAT[self.cat]
            c.setFillColor(col)
            c.roundRect(0, 0, w, self.h, 3, stroke=0, fill=1)
            c.setFillColor(colors.white)
        else:
            label = "?"
            c.setStrokeColor(GRID)
            c.setDash(2, 2)
            c.roundRect(0, 0, w, self.h, 3, stroke=1, fill=0)
            c.setFillColor(MUTED)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawCentredString(w / 2, self.h / 2 - 2.6, label)
        c.restoreState()


def _numbered_canvas(header):
    class NumberedCanvas(rl_canvas.Canvas):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self._pages = []

        def showPage(self):
            self._pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            n = len(self._pages)
            for st in self._pages:
                self.__dict__.update(st)
                w, h = self._pagesize
                self.setFont("Helvetica", 9)
                self.setFillColor(MUTED)
                self.drawString(0.5 * inch, h - 0.4 * inch, header)
                self.drawRightString(w - 0.5 * inch, h - 0.4 * inch, f"Page {self._pageNumber} of {n}")
                rl_canvas.Canvas.showPage(self)
            rl_canvas.Canvas.save(self)

    return NumberedCanvas


def _legend(legend, include_rankdone):
    """Two-part legend: what the colored type tags mean, and what the status marks mean."""
    rows = [[Paragraph("<b>Type</b>: how we'll work on each requirement", ST["small"]), ""]]
    for c in ("D", "O", "S", "N"):
        rows.append([Pill(c), Paragraph(_esc(legend.get(c, "")), ST["small"])])
    rows.append([Pill(""), Paragraph("Not categorized yet.", ST["small"])])
    type_tbl = Table(rows, colWidths=[0.75 * inch, 3.0 * inch])

    srows = [[Paragraph("<b>Status</b>", ST["small"]), ""],
             [Icon("done", 10), Paragraph("Signed off", ST["small"])],
             [Icon("partial", 10), Paragraph("Started / waiting for leader approval", ST["small"])],
             [Icon("award", 10), Paragraph("Rank awarded", ST["small"])],
             ["", Paragraph("Blank = still needed", ST["small"])]]
    if include_rankdone:
        srows.append(["", Paragraph("Grey cell = rank already finished", ST["small"])])
    status_tbl = Table(srows, colWidths=[0.35 * inch, 2.4 * inch])
    common = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("SPAN", (0, 0), (1, 0)),
              ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
              ("LEFTPADDING", (0, 0), (-1, -1), 2)]
    type_tbl.setStyle(TableStyle(common))
    st = list(common)
    if include_rankdone:
        st.append(("BACKGROUND", (0, len(srows) - 1), (0, len(srows) - 1), RANKDONE_BG))
    status_tbl.setStyle(TableStyle(st))
    outer = Table([[type_tbl, status_tbl]], colWidths=[3.95 * inch, 2.9 * inch])
    outer.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOX", (0, 0), (-1, -1), 0.5, GRID),
                               ("LINEBEFORE", (1, 0), (1, 0), 0.5, GRID),
                               ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return outer


def _rank_icon(rank):
    s = rank["status"].lower()
    if s.startswith("awarded"):
        return "award"
    if rank["done"]:
        return "done"
    if any(w in s for w in ("progress", "started", "completed")) and "not started" not in s:
        return "partial"
    return None


def _sections_from(start_index):
    """Rank sections from start_index (into RANKS) through First Class, followed by the chits."""
    return [s for s in SECTIONS if s["kind"] == "chit" or RANKS.index(s["code"]) >= start_index]


def _doc(path, title, pagesize=letter):
    return SimpleDocTemplate(str(path), pagesize=pagesize, title=title, author="Scout Advancement Tool",
                             leftMargin=0.6 * inch, rightMargin=0.6 * inch,
                             topMargin=0.7 * inch, bottomMargin=0.6 * inch)


def _gen_line(generated):
    return Paragraph("Generated: " + generated.strftime("%m/%d/%Y %H:%M:%S"), ST["gen"])


# ---------------------------------------------------------------- all scouts grid

def all_scouts_pdf(path, scouts, title, generated, categories, legend):
    n = len(scouts)
    pagesize = letter if n <= 6 else landscape(letter)
    doc = _doc(path, title, pagesize)
    avail = pagesize[0] - doc.leftMargin - doc.rightMargin
    fixed = [0.45 * inch, 1.95 * inch, 0.7 * inch, 0.42 * inch]
    scout_w = max(0.45 * inch, (avail - sum(fixed)) / max(n, 1))
    if scout_w * n + sum(fixed) > avail:  # many scouts: squeeze the description column
        fixed[1] = max(1.2 * inch, avail - scout_w * n - fixed[0] - fixed[2] - fixed[3])
    widths = fixed + [scout_w] * n

    header = [Paragraph("Req", ST["head"]), Paragraph("Requirement", ST["head"]),
              Paragraph("Type", ST["head"]), Paragraph("Need", ST["head"])]
    for s in scouts:
        first, _, last = s["name"].partition(" ")
        longest = max(stringWidth(w, "Helvetica", 1) for w in (first, last) if w)
        size = max(5.5, min(8.5, (scout_w - 7) / longest))
        style_n = ParagraphStyle("n", parent=ST["head"], fontSize=size, leading=size + 2)
        header.append(Paragraph(_esc(first) + ("<br/>" + _esc(last) if last else ""), style_n))
    rows, style = [header], [
        ("GRID", (0, 0), (-1, -1), 0.5, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, 0), 1.2, MUTED),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]

    start = min((s["start"] for s in scouts), default=len(RANKS))
    for sec in _sections_from(start):
        code = sec["code"]
        r_i = len(rows)
        if sec["kind"] == "rank":
            row = [Paragraph(_esc(sec["name"]), ST["cellb"]), "", "", ""]
            for s in scouts:
                ic = _rank_icon(s["ranks"][code])
                row.append(Icon(ic) if ic else "")
            rows.append(row)
            style += [("SPAN", (0, r_i), (3, r_i)), ("BACKGROUND", (0, r_i), (-1, r_i), SECTION_BG)]
        elif code == CHITS[0]:
            rows.append([Paragraph("Totin' Chip &amp; Firem'n Chit", ST["cellb"])] + [""] * (3 + n))
            style += [("SPAN", (0, r_i), (-1, r_i)), ("BACKGROUND", (0, r_i), (-1, r_i), SECTION_BG)]
        for r in sec["reqs"]:
            key = req_key(code, r["id"])
            need = sum(1 for s in scouts if is_needed(s["reqs"][key]))
            row = ["" if sec["kind"] == "chit" else Paragraph(_esc(r["id"]), ST["smallc"]),
                   Paragraph(_esc(r["short"]), ST["small"]),
                   Pill(categories.get(key, "")),
                   Paragraph(str(need) if need else "", ST["smallc"])]
            ri = len(rows)
            for j, s in enumerate(scouts):
                st = s["reqs"][key]
                if st == "rankdone":
                    row.append("")
                    style.append(("BACKGROUND", (4 + j, ri), (4 + j, ri), RANKDONE_BG))
                elif st in ("done", "partial", "unknown"):
                    row.append(Icon(st))
                else:
                    row.append("")
            rows.append(row)

    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle(style))
    story = [_gen_line(generated), Spacer(1, 4), Paragraph(_esc(title), ST["title"]),
             Paragraph("Trail to First Class: all scouts", ST["subtitle"]), Spacer(1, 8),
             _legend(legend, include_rankdone=True), Spacer(1, 10), table]
    doc.build(story, canvasmaker=_numbered_canvas(title))


# ---------------------------------------------------------------- one scout

def scout_pdf(path, scout, title, generated, categories, legend, hide_done=False):
    doc = _doc(path, f"{scout['name']} - Trail to First Class")
    avail = letter[0] - doc.leftMargin - doc.rightMargin

    # Rank summary strip
    labels = ["Scout", "Tenderfoot", "Second Class", "First Class", "Totin' Chip", "Firem'n Chit"]
    codes = RANKS + CHITS
    icons, texts = [], []
    for c in codes:
        rk = scout["ranks"][c]
        ic = _rank_icon(rk)
        icons.append(Icon(ic, 12) if ic else "")
        status = rk["status"]
        if c in RANKS and not rk["done"] and not rk["missing"]:
            sec = next(s for s in SECTIONS if s["code"] == c)
            done = sum(1 for r in sec["reqs"] if scout["reqs"][req_key(c, r["id"])] == "done")
            status += f"<br/>{done} of {len(sec['reqs'])} signed off"
        texts.append(Paragraph(status, ST["smallc"]))
    summary = Table([[Paragraph(f"<b>{l}</b>", ST["smallc"]) for l in labels], icons, texts],
                    colWidths=[avail / 6] * 6)
    summary.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, GRID), ("INNERGRID", (0, 0), (-1, 0), 0.5, GRID),
                                 ("LINEBEFORE", (1, 0), (-1, -1), 0.5, GRID),
                                 ("BACKGROUND", (0, 0), (-1, 0), SECTION_BG), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                 ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))

    sections = _sections_from(scout["start"])
    # Count what's still needed by type
    counts = {"D": 0, "O": 0, "S": 0, "N": 0, "": 0}
    for sec in sections:
        for r in sec["reqs"]:
            key = req_key(sec["code"], r["id"])
            if is_needed(scout["reqs"][key]):
                cat = categories.get(key, "")
                counts[cat if cat in counts else ""] += 1
    total = sum(counts.values())
    crow = [Paragraph(f"<b>Still needed: {total}</b>", ST["cell"])]
    for c in ("D", "O", "S", "N"):
        crow += [Pill(c), Paragraph(str(counts[c]), ST["cellb"])]
    cw = [1.35 * inch] + [0.7 * inch, 0.35 * inch] * 4
    if counts[""]:
        crow += [Pill(""), Paragraph(str(counts[""]), ST["cellb"])]
        cw += [0.7 * inch, 0.35 * inch]
    count_tbl = Table([crow], colWidths=cw, hAlign="LEFT")
    count_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 2)]))

    # Main requirement table
    widths = [0.55 * inch, avail - 0.55 * inch - 0.85 * inch - 0.75 * inch, 0.85 * inch, 0.75 * inch]
    rows = [[Paragraph("Req", ST["head"]), Paragraph("Requirement", ST["head"]),
             Paragraph("Type", ST["head"]), Paragraph("Status", ST["head"])]]
    style = [("GRID", (0, 0), (-1, -1), 0.5, GRID), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
             ("LINEBELOW", (0, 0), (-1, 0), 1.2, MUTED),
             ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5)]
    if scout["start"] >= len(RANKS):
        r_i = len(rows)
        rows.append([Paragraph("First Class rank is complete. Congratulations!", ST["cellb"]), "", "", ""])
        style += [("SPAN", (0, r_i), (-1, r_i)), ("BACKGROUND", (0, r_i), (-1, r_i), SECTION_BG)]
    for sec in sections:
        code = sec["code"]
        reqs = [r for r in sec["reqs"]
                if not (hide_done and not is_needed(scout["reqs"][req_key(code, r["id"])]))]
        if sec["kind"] == "rank":
            rk = scout["ranks"][code]
            done = sum(1 for r in sec["reqs"] if scout["reqs"][req_key(code, r["id"])] == "done")
            r_i = len(rows)
            rows.append([Paragraph(f"{_esc(sec['name'])}  <font color='#666666' size='8.5'>"
                                   f"{_esc(rk['status'])}, {done} of {len(sec['reqs'])} signed off</font>",
                                   ST["cellb"]), "", "", ""])
            style += [("SPAN", (0, r_i), (-1, r_i)), ("BACKGROUND", (0, r_i), (-1, r_i), SECTION_BG)]
        elif code == CHITS[0]:
            r_i = len(rows)
            rows.append([Paragraph("Totin' Chip &amp; Firem'n Chit", ST["cellb"]), "", "", ""])
            style += [("SPAN", (0, r_i), (-1, r_i)), ("BACKGROUND", (0, r_i), (-1, r_i), SECTION_BG)]
        for r in reqs:
            key = req_key(code, r["id"])
            st = scout["reqs"][key]
            rows.append(["" if sec["kind"] == "chit" else Paragraph(_esc(r["id"]), ST["smallc"]),
                         Paragraph(_esc(r["short"]), ST["cell"]),
                         Pill(categories.get(key, "")),
                         Icon(st) if st in ("done", "partial", "unknown") else ""])
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle(style))

    story = [_gen_line(generated), Spacer(1, 4),
             Paragraph(_esc(scout["name"]), ST["title"]),
             Paragraph(f"Trail to First Class · {_esc(title)}", ST["subtitle"]), Spacer(1, 10),
             summary, Spacer(1, 8), count_tbl, Spacer(1, 6),
             _legend(legend, include_rankdone=False), Spacer(1, 10), table]
    doc.build(story, canvasmaker=_numbered_canvas(f"{scout['name']} - Trail to First Class"))
