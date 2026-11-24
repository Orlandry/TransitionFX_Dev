"""
M_Transition_SpiralTiles を Named Reroute 注釈付きで構築する (in-place 再構築可)。

プラグインのコンテンツなので UE 5.5 のワークスペースで実行すること (CLAUDE.md "Plugin content is saved with UE 5.5")。
数式の原型は Saved/TransitionIdeas/transition_ideas.py (numpy プロトタイプ) の spiral_tiles、
2 本アームは Saved/TransitionIdeas/spiral_variants.py の order_two_arms。

画面を Columns x Rows のタイルに分け、矩形スパイラルの順にタイルが中心から膨らんで埋まる。
Arms = 2 (既定) では左上と右下の 2 本のアームが同じ渦を同時に時計回りに進み (180 度の回転対称)、
各周を両端から閉じて中央の 2 タイルで終わる。Arms = 1 は 1.7.0 の動き (外周の左上から 1 本で
中心へ。16 x 9 では最後に中央の 8 x 1 の列を左から右へ埋め、中心より右で終わる)。
画面 UV をそのまま使うので、タイルが正方形になるのは Columns : Rows が画面のアスペクト比と同じとき (既定 16 x 9)。

  cols, rows = max(round(Columns), 1), max(round(Rows), 1)
  cell  = uv * (cols, rows)                         タイル座標
  tile  = min(floor(cell), last)                    タイルの (列, 行)。last = (cols, rows) - 1
  ring  = min(tile, last - tile) の小さい方の成分    外周から数えた周回番号 (0 = 最外周)
  span  = last - 2 * ring                           その周の (幅 - 1, 高さ - 1) = (sw, sh)
  (a, b) = tile - ring                              周の左上を原点としたタイル位置
  off   = 周の中での順番 (左上から時計回り):
            上辺 (b = 0)   a
            右辺 (a = sw)  sw + b
            下辺 (b = sh)  2 * sw + sh - a
            左辺           2 * sw + 2 * sh - b
          上 > 右 > 下 > 左 の優先順で lerp で選ぶ (a, b は整数なので saturate が 0/1 の選択子になる)。
          幅か高さが 1 の最内周もこの式のままで正しい。
  offRot = 180 度回転した双子タイル (last - tile) の off。(a', b') = (sw - a, sh - b) を同じ式に入れたもの:
            上 (b = sh)    sw - a
            右 (a = 0)     sw + sh - b
            下 (b = 0)     sw + sh + a
            左             2 * sw + sh + b
          (優先順は off と同じ)。通常の周では offRot = (off + 周長 / 2) mod 周長、
          幅か高さが 1 の最内周では両端から数えた位置になる。
  arms  = clamp(round(Arms), 1, 2)
  lap   = arms = 2 なら min(off, offRot) (2 本のアームのうち先に着く方)、1 なら off
  order = (ring * (2 * (cols + rows) - 4 * ring) / arms + lap) / (cols * rows / arms)     0..1 未満
  local = saturate((Progress * (1 + Tail) - order) / Tail)    タイルの成長度。Tail = 同時に成長中の区間の長さ
                                                              (既定 0.03。1.7.0 は 0.07)
  size  = |frac(cell) - 0.5| * 2                    タイル中心からの距離 (軸ごと、1 = タイルの端)
  w     = |(ddx(cell.x), ddy(cell.y))| * 4          軸ごとの 2px (size 単位)
  edge  = local * (1 + w)                           タイルの現在の半幅。local = 1 で端を w だけ越える
  mask  = smoothstep(edge, edge - w, size) の x 成分 * y 成分
  出力  = lerp(SceneTexture.rgb, FadeColor, MF_ApplyInvert(mask, Invert)) -> EmissiveColor
  Progress = 0 で mask = 0、Progress = 1 で mask = 1。
ルール: GLSL ローカル変数 = Named Reroute Declaration / 再利用 = Usage。

実行例 (UE 5.5 ワークスペース):
  UnrealEditor-Cmd.exe T55W.uproject -run=pythonscript ^
    -script="<abs>/Plugins/DevMaterialTools/Tools/build_m_spiraltiles.py" -EnablePlugins=PythonScriptPlugin
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tfx_material_graph import Graph, E, C_CO, C_FX, C_SC, C_UV  # noqa: E402

ADD = E.MaterialExpressionAdd
SUB = E.MaterialExpressionSubtract
MUL = E.MaterialExpressionMultiply
DIV = E.MaterialExpressionDivide
MIN = E.MaterialExpressionMin
MAX = E.MaterialExpressionMax
SAT = E.MaterialExpressionSaturate
ABS = E.MaterialExpressionAbs


def build_spiral_tiles():
    g = Graph("M_Transition_SpiralTiles")

    # ---- grid = (cols, rows) / last = grid - 1 ----
    cols_p = g.sparam("Columns", 16.0, -4400, 0)
    rows_p = g.sparam("Rows", 9.0, -4400, 180)
    g.decl("cols", g.binop(MAX, -4050, 0, g.unary(E.MaterialExpressionRound, -4200, 0, cols_p), 1.0),
           -3900, 0, C_CO)
    g.decl("rows", g.binop(MAX, -4050, 180, g.unary(E.MaterialExpressionRound, -4200, 180, rows_p), 1.0),
           -3900, 180, C_CO)
    g.decl("grid", g.binop(E.MaterialExpressionAppendVector, -3500, 90,
                           g.use("cols", -3650, 40), g.use("rows", -3650, 140)), -3350, 90, C_CO)
    g.decl("last", g.binop(SUB, -2950, 90, g.use("grid", -3100, 90), 1.0), -2800, 90, C_CO)
    g.comment("grid = (cols, rows) = max(round(Columns / Rows), 1) / last = grid - 1 (index of the last column / row)",
              -4470, -100, 1900, 420, C_CO)

    # ---- arms = clamp(round(Arms), 1, 2) / twoArms = arms - 1 ----
    arms_p = g.sparam("Arms", 2.0, -2450, 0)
    arms_r = g.unary(E.MaterialExpressionRound, -2250, 0, arms_p)
    g.decl("arms", g.binop(MAX, -1950, 0, g.binop(MIN, -2100, 0, arms_r, 2.0), 1.0), -1800, 0, C_SC)
    g.decl("twoArms", g.binop(SUB, -1950, 180, g.use("arms", -2100, 180), 1.0), -1800, 180, C_SC)
    g.comment("arms = clamp(round(Arms), 1, 2): 2 = arms from the top-left and the bottom-right corner, "
              "1 = a single arm (1.7.0) / twoArms = arms - 1", -2500, -100, 950, 420, C_SC)

    # ---- cell = uv * grid / tile = min(floor(cell), last) ----
    tc = g.expr(E.MaterialExpressionTextureCoordinate, -4400, 500)
    g.decl("cell", g.binop(MUL, -4200, 500, tc, g.use("grid", -4400, 620)), -4050, 500, C_UV)
    fl = g.unary(E.MaterialExpressionFloor, -3700, 500, g.use("cell", -3850, 500))
    g.decl("tile", g.binop(MIN, -3550, 500, fl, g.use("last", -3700, 600)), -3400, 500, C_CO)
    g.comment("cell = uv * grid (tile coordinates) / tile = (column, row) of this pixel's tile",
              -4470, 400, 1300, 330, C_UV)

    # ---- ring = min component of min(tile, last - tile) ----
    far = g.binop(SUB, -2850, 560, g.use("last", -3000, 520), g.use("tile", -3000, 610))
    g.decl("edgeDist", g.binop(MIN, -2700, 500, g.use("tile", -2850, 460), far), -2550, 500, C_CO)
    ring = g.binop(MIN, -2050, 500, g.channel(-2200, 450, g.use("edgeDist", -2350, 450), "r"),
                   g.channel(-2200, 560, g.use("edgeDist", -2350, 560), "g"))
    g.decl("ring", ring, -1900, 500, C_CO)
    g.comment("ring = how many tiles this tile is away from the nearest screen edge (0 = outermost lap)",
              -3060, 400, 1400, 330, C_CO)

    # ---- span = last - 2 * ring = (sw, sh) / (a, b) = tile - ring ----
    ring2 = g.binop(MUL, -4200, 960, g.use("ring", -4400, 960), 2.0)
    g.decl("span", g.binop(SUB, -4050, 900, g.use("last", -4200, 860), ring2), -3900, 900, C_CO)
    g.decl("ab", g.binop(SUB, -4050, 1150, g.use("tile", -4200, 1110), g.use("ring", -4200, 1200)),
           -3900, 1150, C_CO)
    g.decl("sw", g.channel(-3500, 860, g.use("span", -3650, 860), "r"), -3350, 860, C_CO)
    g.decl("sh", g.channel(-3500, 960, g.use("span", -3650, 960), "g"), -3350, 960, C_CO)
    g.decl("a", g.channel(-3500, 1110, g.use("ab", -3650, 1110), "r"), -3350, 1110, C_CO)
    g.decl("b", g.channel(-3500, 1210, g.use("ab", -3650, 1210), "g"), -3350, 1210, C_CO)
    g.comment("this lap is a rectangle of (sw + 1) x (sh + 1) tiles; (a, b) = tile position inside it "
              "(0, 0 = the lap's top-left tile)", -4470, 770, 1300, 560, C_CO)

    # ---- onFar = saturate(ab - span + 1) = (right edge?, bottom edge?) / isTop = 1 - saturate(b) ----
    rel = g.binop(SUB, -2850, 900, g.use("ab", -3000, 860), g.use("span", -3000, 950))
    g.decl("onFar", g.unary(SAT, -2550, 900, g.binop(ADD, -2700, 900, rel, 1.0)), -2400, 900, C_SC)
    g.decl("isTop", g.unary(E.MaterialExpressionOneMinus, -2550, 1100, g.unary(SAT, -2700, 1100,
                                                                              g.use("b", -2850, 1100))),
           -2400, 1100, C_SC)
    g.comment("edge selectors (0 or 1, a / b are integers): onFar = (a == sw, b == sh) = on the right / bottom edge, "
              "isTop = (b == 0)", -3060, 770, 850, 480, C_SC)

    # ---- off = index of the tile along its lap (clockwise from the top-left tile) ----
    off_right = g.binop(ADD, -1650, 900, g.use("sw", -1800, 860), g.use("b", -1800, 950))
    sw2 = g.binop(MUL, -1650, 1080, g.use("sw", -1800, 1080), 2.0)
    g.decl("base", g.binop(ADD, -1500, 1120, sw2, g.use("sh", -1650, 1180)), -1350, 1120, C_SC)
    off_bottom = g.binop(SUB, -950, 1050, g.use("base", -1100, 1010), g.use("a", -1100, 1100))
    left_k = g.binop(ADD, -950, 1250, g.use("base", -1100, 1210), g.use("sh", -1100, 1300))
    off_left = g.binop(SUB, -800, 1290, left_k, g.use("b", -950, 1370))
    far_r = g.channel(-650, 860, g.use("onFar", -800, 860), "r")
    far_b = g.channel(-650, 1130, g.use("onFar", -800, 1130), "g")
    sel_bottom = g.lerp(-450, 1150, off_left, off_bottom, far_b)
    sel_right = g.lerp(-250, 950, sel_bottom, off_right, far_r)
    sel_top = g.lerp(-50, 800, sel_right, g.use("a", -250, 760), g.use("isTop", -250, 850))
    g.decl("off", sel_top, 100, 800, C_SC)
    g.comment("off = index along the lap, clockwise from its top-left tile: top a / right sw + b / "
              "bottom 2sw + sh - a / left 2sw + 2sh - b (priority top > right > bottom > left)",
              -1860, 670, 2150, 800, C_SC)

    # ---- offRot = off of the 180-degree twin tile (sw - a, sh - b) ----
    g.decl("onNear", g.unary(E.MaterialExpressionOneMinus, 600, 760, g.unary(SAT, 450, 760, g.use("ab", 350, 760))),
           750, 760, C_SC)
    below = g.binop(SUB, 450, 920, g.use("sh", 350, 880), g.use("b", 350, 970))
    g.decl("isBottom", g.unary(E.MaterialExpressionOneMinus, 600, 920, g.unary(SAT, 500, 920, below)),
           750, 920, C_SC)
    g.decl("half", g.binop(ADD, 600, 1120, g.use("sw", 450, 1080), g.use("sh", 450, 1170)), 750, 1120, C_SC)
    top_r = g.binop(SUB, 1150, 760, g.use("sw", 1000, 720), g.use("a", 1000, 810))
    right_r = g.binop(SUB, 1150, 920, g.use("half", 1000, 880), g.use("b", 1000, 970))
    bottom_r = g.binop(ADD, 1150, 1080, g.use("half", 1000, 1040), g.use("a", 1000, 1130))
    left_r = g.binop(ADD, 1150, 1240, g.use("base", 1000, 1200), g.use("b", 1000, 1290))
    near_a = g.channel(1450, 900, g.use("onNear", 1300, 900), "r")
    near_b = g.channel(1300, 1180, g.use("onNear", 1150, 1380), "g")
    rot_bottom = g.lerp(1450, 1150, left_r, bottom_r, near_b)
    rot_right = g.lerp(1650, 950, rot_bottom, right_r, near_a)
    rot_top = g.lerp(1850, 800, rot_right, top_r, g.use("isBottom", 1650, 800))
    g.decl("offRot", rot_top, 2000, 800, C_SC)
    g.comment("offRot = off of the 180-degree twin tile (sw - a, sh - b): top (b == sh) sw - a / right (a == 0) "
              "sw + sh - b / bottom (b == 0) sw + sh + a / left 2sw + sh + b (same priority as off)",
              300, 670, 1900, 800, C_SC)

    # ---- lap = arms == 2 ? min(off, offRot) : off ----
    g.decl("lap", g.lerp(2550, 950, g.use("off", 2350, 900),
                         g.binop(MIN, 2400, 1000, g.use("off", 2250, 980), g.use("offRot", 2250, 1070)),
                         g.use("twoArms", 2350, 1150)), 2700, 950, C_SC)
    g.comment("lap = index along the lap for the arm that reaches this tile first: two arms (top-left and "
              "bottom-right) take min(off, offRot), one arm takes off", 2230, 670, 650, 600, C_SC)

    # ---- order = (ring * (2 * (cols + rows) - 4 * ring) / arms + lap) / (cols * rows / arms) ----
    perim2 = g.binop(MUL, -4050, 1650, g.binop(ADD, -4200, 1650, g.use("cols", -4400, 1610),
                                              g.use("rows", -4400, 1700)), 2.0)
    ring4 = g.binop(MUL, -4050, 1800, g.use("ring", -4200, 1800), 4.0)
    before = g.binop(MUL, -3850, 1700, g.use("ring", -4050, 1580), g.binop(SUB, -3950, 1760, perim2, ring4))
    before_a = g.binop(DIV, -3700, 1700, before, g.use("arms", -3850, 1820))
    total = g.binop(MUL, -3850, 1950, g.use("cols", -4050, 1920), g.use("rows", -4050, 2010))
    total_a = g.binop(DIV, -3700, 1950, total, g.use("arms", -3850, 2060))
    index = g.binop(ADD, -3550, 1700, before_a, g.use("lap", -3700, 1600))
    g.decl("order", g.binop(DIV, -3400, 1750, index, total_a), -3250, 1750, C_SC)
    g.comment("order = (tiles in the laps outside this one / arms + lap) / (tile count / arms): 0 for the first "
              "tile, below 1 for the last", -4470, 1500, 1500, 620, C_SC)

    # ---- local = saturate((Progress * (1 + Tail) - order) / Tail) ----
    tail_p = g.sparam("Tail", 0.03, -2850, 1900)
    prog_p = g.sparam("Progress", 0.5, -2400, 1600)
    g.decl("tail", g.binop(MAX, -2650, 1900, tail_p, 0.0001), -2500, 1900, C_SC)
    stretch = g.binop(MUL, -2000, 1650, prog_p, g.binop(ADD, -2150, 1750, g.use("tail", -2300, 1750), 1.0))
    ahead = g.binop(SUB, -1850, 1700, stretch, g.use("order", -2000, 1800))
    grown = g.binop(DIV, -1700, 1750, ahead, g.use("tail", -1850, 1850))
    g.decl("local", g.unary(SAT, -1550, 1750, grown), -1400, 1750, C_SC)
    g.comment("local = saturate((Progress * (1 + Tail) - order) / Tail): growth of this tile; "
              "Tail = share of the spiral that is growing at the same time", -2910, 1500, 1750, 560, C_SC)

    # ---- size = |frac(cell) - 0.5| * 2 / w = |(ddx(cell.x), ddy(cell.y))| * 4 ----
    centred = g.binop(SUB, -4050, 2300, g.unary(E.MaterialExpressionFrac, -4200, 2300,
                                               g.use("cell", -4400, 2300)), 0.5)
    g.decl("size", g.binop(MUL, -3750, 2300, g.unary(ABS, -3900, 2300, centred), 2.0), -3600, 2300, C_CO)
    ddx = g.unary(E.MaterialExpressionDDX, -4050, 2500, g.channel(-4200, 2500, g.use("cell", -4400, 2500), "r"))
    ddy = g.unary(E.MaterialExpressionDDY, -4050, 2620, g.channel(-4200, 2620, g.use("cell", -4400, 2620), "g"))
    grad = g.unary(ABS, -3750, 2550, g.binop(E.MaterialExpressionAppendVector, -3900, 2550, ddx, ddy))
    g.decl("w", g.binop(MUL, -3600, 2550, grad, 4.0), -3450, 2550, C_SC)
    g.comment("size = distance from the tile centre per axis (1 = tile border) / w = 2 pixels per axis in size units",
              -4470, 2200, 1250, 560, C_CO)

    # ---- edge = local * (1 + w) / mask = smoothstep(edge, edge - w, size).x * .y ----
    reach = g.binop(ADD, -2850, 2400, g.use("w", -3000, 2400), 1.0)
    g.decl("edge", g.binop(MUL, -2700, 2350, g.use("local", -2850, 2300), reach), -2550, 2350, C_SC)
    inner = g.binop(SUB, -2050, 2420, g.use("edge", -2200, 2380), g.use("w", -2200, 2470))
    g.decl("axisMask", g.smoothstep(-1850, 2350, g.use("edge", -2050, 2300), inner, g.use("size", -2050, 2550)),
           -1650, 2350, C_FX)
    mask = g.binop(MUL, -1100, 2350, g.channel(-1250, 2300, g.use("axisMask", -1400, 2300), "r"),
                   g.channel(-1250, 2410, g.use("axisMask", -1400, 2410), "g"))
    g.comment("edge = local * (1 + w): the tile's half-size, a full tile passes its border by w / "
              "mask = smoothstep(edge, edge - w, size) in x times y (Min > Max: 1 inside the tile)",
              -3060, 2200, 2150, 500, C_FX)

    g.finish(mask, -700, 2350)
    return g.verify_and_save(["Progress", "Invert", "FadeColor", "Columns", "Rows", "Tail", "Arms"])


print("[TEST] RESULT: " + ("PASS" if build_spiral_tiles() else "FAIL"))
