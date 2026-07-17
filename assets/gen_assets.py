#!/usr/bin/env python3
"""Generate the three Fusion Prime brand diagrams as sober, vision-aligned SVGs.

Design system (deliberately restrained):
  bg      #0C1322   panel #141E32   panel2 #18233B
  stroke  #263149   text  #E6ECF5   muted  #93A1B8   faint #5C6B84
  accent  #5EEAD4 (teal — the CCIP / cross-chain thread)
  accent2 #8B93F8 (indigo — the borrow / off-chain side, used sparingly)
Font: DejaVu Sans (present on this box), Helvetica/Arial fallback.
"""
from pathlib import Path
from html import escape

BG, BG2 = "#0C1322", "#0A0F1C"
PANEL, PANEL2 = "#141E32", "#18233B"
STROKE = "#263149"
TEXT, MUTED, FAINT = "#E6ECF5", "#93A1B8", "#5C6B84"
ACCENT, ACCENT2 = "#5EEAD4", "#8B93F8"
FONT = "DejaVu Sans, Helvetica, Arial, sans-serif"
MONO = "DejaVu Sans Mono, monospace"

OUT = Path(__file__).parent


def T(x, y, s, size=15, fill=TEXT, weight="normal", anchor="start", ls="0", font=FONT, op=1):
    return (f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" '
            f'letter-spacing="{ls}" opacity="{op}">{escape(s)}</text>')


def card(x, y, w, h, fill=PANEL, stroke=STROKE, rx=14, sw=1.2):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def pill(x, y, w, s, accent=MUTED, h=30, fill="none", text_fill=None):
    tf = text_fill or accent
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h/2}" fill="{fill}" '
            f'stroke="{accent}" stroke-width="1.2"/>'
            + T(x + w / 2, y + h / 2 + 4.5, s, 13, tf, "500", "middle"))


def line(x1, y1, x2, y2, stroke=STROKE, sw=1.6, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}"{d}/>'


def dot(x, y, r=4, fill=ACCENT):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"/>'


def header(defs_extra=""):
    return (f'<defs>'
            f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{BG}"/><stop offset="1" stop-color="{BG2}"/>'
            f'</linearGradient>'
            f'<marker id="arw" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" '
            f'markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0 0 L10 5 L0 10 z" fill="{FAINT}"/></marker>'
            f'<marker id="arwA" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" '
            f'markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0 0 L10 5 L0 10 z" fill="{ACCENT}"/></marker>'
            f'{defs_extra}</defs>')


def wrap(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}">{header()}'
            f'<rect width="{w}" height="{h}" fill="url(#bg)"/>{body}</svg>')


def title_block(x, y, title, subtitle):
    s = T(x, y, title, 30, TEXT, "700")
    s += T(x, y + 26, subtitle, 15, MUTED)
    s += line(x, y + 42, x + 54, y + 42, ACCENT, 3)
    return s


def wordmark(x, y):
    # small square mark + name, for footer/corner
    return (f'<rect x="{x}" y="{y-13}" width="18" height="18" rx="4" fill="none" '
            f'stroke="{ACCENT}" stroke-width="1.6"/>'
            f'<rect x="{x+5}" y="{y-8}" width="8" height="8" rx="2" fill="{ACCENT}"/>'
            + T(x + 27, y + 2, "Fusion Prime", 14, TEXT, "600"))


def footer(w, h, note):
    return line(64, h - 52, w - 64, h - 52, STROKE, 1) + T(64, h - 30, note, 12.5, FAINT, "400", "start", "0.3")


# ---------------------------------------------------------------- 1. PLATFORM OVERVIEW
def platform_overview():
    W, H = 1200, 680
    b = title_block(64, 74, "Fusion Prime", "Omnichain collateral & settlement protocol")
    b += wordmark(W - 190, 60)

    # On-chain band
    vy, vh = 150, 150
    # Vault A
    b += card(64, vy, 300, vh)
    b += T(84, vy + 30, "ETHEREUM · Sepolia", 12, MUTED, "600", "start", "1.2")
    b += pill(84, vy + 52, 200, "CrossChainVault", ACCENT, 34, PANEL2, TEXT)
    b += T(84, vy + 116, "collateral · liquidations", 12.5, FAINT)
    # Vault B
    b += card(836, vy, 300, vh)
    b += T(856, vy + 30, "BASE · Sepolia", 12, MUTED, "600", "start", "1.2")
    b += pill(856, vy + 52, 200, "CrossChainVault", ACCENT, 34, PANEL2, TEXT)
    b += T(856, vy + 116, "unified position", 12.5, FAINT)
    # BridgeManager (center)
    cx = 468
    b += card(cx, vy, 264, vh, PANEL2)
    b += T(cx + 132, vy + 30, "BridgeManager", 15, TEXT, "600", "middle")
    b += pill(cx + 24, vy + 50, 100, "CCIP", ACCENT, 30, "none", ACCENT)
    b += pill(cx + 140, vy + 50, 100, "Axelar", FAINT, 30)
    b += T(cx + 132, vy + 118, "bridge-agnostic · trusted-remote", 11.5, FAINT, "400", "middle")

    # connectors A -> BM -> B (accent = the CCIP thread)
    midy = vy + vh / 2
    b += line(364, midy, cx, midy, ACCENT, 2.2)
    b += line(cx + 264, midy, 836, midy, ACCENT, 2.2)
    b += dot(364, midy) + dot(836, midy)
    b += T(414, midy - 12, "cross-chain message", 11.5, ACCENT, "400", "middle")

    # Oracle above center
    oy = 118
    b += f'<circle cx="{cx+132}" cy="{oy}" r="6" fill="none" stroke="{MUTED}" stroke-width="1.4"/>'
    b += line(cx + 132, oy + 6, cx + 132, vy, MUTED, 1.2, "3 4")
    b += T(cx + 132, oy - 12, "Price oracle · staleness-checked", 11.5, MUTED, "400", "middle")

    # events down to off-chain
    b += line(214, vy + vh, 214, 372, FAINT, 1.4, "3 4")
    b += f'<line x1="214" y1="372" x2="214" y2="392" stroke="{FAINT}" stroke-width="1.4" marker-end="url(#arw)"/>'
    b += T(230, 366, "events", 11.5, FAINT)

    # Off-chain band
    oy2 = 402
    b += card(64, oy2, 1072, 150, PANEL)
    b += T(88, oy2 + 32, "EVENT-DRIVEN SETTLEMENT LAYER", 12, MUTED, "600", "start", "1.4")
    labels = ["Relayer", "Settlement", "Risk Engine", "Compliance", "Indexer"]
    pw, gap = 176, 24
    total = len(labels) * pw + (len(labels) - 1) * gap
    sx = 64 + (1072 - total) / 2
    ly = oy2 + 92  # pill vertical centre
    for i, lb in enumerate(labels):
        px = sx + i * (pw + gap)
        acc = ACCENT2 if lb in ("Settlement", "Risk Engine") else MUTED
        b += pill(px, oy2 + 74, pw, lb, acc, 36, PANEL2, TEXT)
        if i < len(labels) - 1:  # connector segment in the gap, not through the pill
            b += f'<line x1="{px+pw+2}" y1="{ly}" x2="{px+pw+gap-2}" y2="{ly}" stroke="{STROKE}" stroke-width="1.6" marker-end="url(#arw)"/>'
    b += T(88, oy2 + 130, "Pub/Sub event bus", 11.5, FAINT)

    b += footer(W, H, "Deposit collateral on one chain · borrow against it on another · CCIP-first, bridge-agnostic")
    return wrap(W, H, b)


# ---------------------------------------------------------------- 2. OMNICHAIN COLLATERAL
def omnichain():
    W, H = 1200, 680
    b = title_block(64, 74, "Omnichain Collateral", "Deposit anywhere · borrow anywhere · one position")
    b += wordmark(W - 190, 60)

    # Left: source chains with collateral
    chains = [("Ethereum", "ETH · stables"), ("Base", "ETH · stables"), ("Arbitrum", "wstETH · wBTC")]
    cy0, chh, cg = 150, 108, 26
    for i, (c, assets) in enumerate(chains):
        y = cy0 + i * (chh + cg)
        b += card(64, y, 300, chh)
        b += T(88, y + 38, c, 17, TEXT, "600")
        b += T(88, y + 66, assets, 12.5, MUTED)
        b += T(88, y + 90, "collateral", 11, FAINT, "400", "start", "1")
        # connector to hub
        b += line(364, y + chh / 2, 470, 340, ACCENT if i == 0 else STROKE, 2 if i == 0 else 1.6)
    b += dot(364, cy0 + chh / 2, 4, ACCENT)

    # Center hub
    hx, hy, hw, hh = 470, 250, 260, 180
    b += card(hx, hy, hw, hh, PANEL2)
    b += T(hx + hw / 2, hy + 40, "Fusion Prime", 17, TEXT, "700", "middle")
    b += T(hx + hw / 2, hy + 62, "collateral hub", 12.5, MUTED, "400", "middle")
    b += pill(hx + 30, hy + 84, 200, "BridgeManager", MUTED, 32, PANEL, TEXT)
    b += pill(hx + 30, hy + 126, 95, "CCIP", ACCENT, 30, "none", ACCENT)
    b += pill(hx + 135, hy + 126, 95, "Axelar", FAINT, 30)

    # Right: unified credit line output
    ox = 836
    b += card(ox, hy, 300, hh, PANEL)
    b += T(ox + 24, hy + 40, "UNIFIED POSITION", 12, MUTED, "600", "start", "1.4")
    b += T(ox + 24, hy + 76, "One credit line", 20, TEXT, "700")
    b += T(ox + 24, hy + 104, "across every chain's", 13, MUTED)
    b += T(ox + 24, hy + 124, "collateral", 13, MUTED)
    b += pill(ox + 24, hy + 138, 130, "borrow →", ACCENT2, 32, "none", ACCENT2)
    # hub -> output (accent thread)
    b += line(hx + hw, hy + hh / 2, ox, hy + hh / 2, ACCENT, 2.4)
    b += f'<line x1="{ox-40}" y1="{hy+hh/2}" x2="{ox}" y2="{hy+hh/2}" stroke="{ACCENT}" stroke-width="2.4" marker-end="url(#arwA)"/>'

    b += footer(W, H, "Cross-chain collateral state moved through a bridge-agnostic adapter layer — CCIP-first")
    return wrap(W, H, b)


# ---------------------------------------------------------------- 3. ESCROW & SETTLEMENT
def escrow():
    W, H = 1200, 560
    b = title_block(64, 74, "Programmable Escrow & Settlement", "On-chain triggers · identity-gated release · event-driven settlement")
    b += wordmark(W - 190, 60)

    # Horizontal stage flow
    stages = [
        ("createEscrow", "funds locked on-chain", ACCENT),
        ("conditions", "approvals · on-chain triggers", MUTED),
        ("release", "delivery-vs-payment", ACCENT),
    ]
    sw_, sh_, sy = 300, 116, 168
    gap = (W - 128 - 3 * sw_) / 2
    for i, (t, sub, acc) in enumerate(stages):
        x = 64 + i * (sw_ + gap)
        b += card(x, sy, sw_, sh_)
        b += T(x + 24, sy + 30, f"{i+1}", 13, FAINT, "700")
        b += T(x + 24, sy + 58, t, 19, TEXT, "600", "start", "0", MONO)
        b += T(x + 24, sy + 86, sub, 12.5, MUTED)
        b += f'<rect x="{x}" y="{sy}" width="4" height="{sh_}" rx="2" fill="{acc}"/>'
        if i < 2:
            ax = x + sw_
            b += f'<line x1="{ax+10}" y1="{sy+sh_/2}" x2="{ax+gap-10}" y2="{sy+sh_/2}" stroke="{FAINT}" stroke-width="1.8" marker-end="url(#arw)"/>'

    # Off-chain settlement pipeline underneath
    py = 356
    b += card(64, py, W - 128, 120, PANEL)
    b += T(88, py + 32, "SETTLEMENT PIPELINE", 12, MUTED, "600", "start", "1.4")
    steps = ["on-chain event", "relayer", "Pub/Sub", "settlement", "indexer → REST"]
    pw, gp = 190, 22
    total = len(steps) * pw + (len(steps) - 1) * gp
    sx = 64 + (W - 128 - total) / 2
    ly = py + 78
    for i, st in enumerate(steps):
        px = sx + i * (pw + gp)
        acc = ACCENT2 if st == "settlement" else MUTED
        b += pill(px, py + 60, pw, st, acc, 34, PANEL2, TEXT)
        if i < len(steps) - 1:
            b += f'<line x1="{px+pw+2}" y1="{ly}" x2="{px+pw+gp-2}" y2="{ly}" stroke="{STROKE}" stroke-width="1.6" marker-end="url(#arw)"/>'
    # link stage1 down to pipeline
    b += line(214, sy + sh_, 214, py, FAINT, 1.3, "3 4")

    b += footer(W, H, "CI-certified end-to-end: createEscrow → relayer → Pub/Sub → settlement → indexer")
    return wrap(W, H, b)


for name, fn in [
    ("fusion_prime_platform_overview", platform_overview),
    ("omnichain_liquidity_architecture", omnichain),
    ("secure_escrow_settlement", escrow),
]:
    (OUT / f"{name}.svg").write_text(fn())
    print("wrote", name + ".svg")
