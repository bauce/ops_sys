"""生成《信息化运维管理系统》图文版汇报 PPT：少文字、多截图。"""
from pathlib import Path

from PIL import Image
from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

BASE = Path(__file__).resolve().parent.parent
ASSETS = BASE / "build" / "ppt-assets"
OUT = BASE / "信息化运维管理系统-建设汇报（图文版）.pptx"

FONT = "PingFang SC"
NAVY = RGBColor(0x0F, 0x1E, 0x38)
NAVY_2 = RGBColor(0x17, 0x2E, 0x55)
BLUE = RGBColor(0x2F, 0x6F, 0xEB)
BLUE_SOFT = RGBColor(0x4F, 0x8C, 0xFF)
BLUE_LIGHT = RGBColor(0xEA, 0xF1, 0xFF)
INK = RGBColor(0x1F, 0x29, 0x37)
INK_2 = RGBColor(0x4B, 0x55, 0x63)
GRAY = RGBColor(0x8A, 0x94, 0xA6)
LINE = RGBColor(0xE4, 0xE9, 0xF2)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

W, H = 13.333, 7.5


def _set_font(run, size=None, color=None, bold=None, name=FONT):
    font = run.font
    if size is not None:
        font.size = Pt(size)
    if color is not None:
        font.color.rgb = color
    if bold is not None:
        font.bold = bold
    font.name = name
    rpr = run._r.get_or_add_rPr()
    ea = rpr.find(qn("a:ea"))
    if ea is None:
        ea = etree.SubElement(rpr, qn("a:ea"))
    ea.set("typeface", name)


def text(slide, x, y, w, h, content, size=14, color=INK, bold=False,
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, line=None):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    lines = content.split("\n") if isinstance(content, str) else content
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if line:
            p.line_spacing = line
        r = p.add_run()
        r.text = ln
        _set_font(r, size=size, color=color, bold=bold)
    return box


def rect(slide, x, y, w, h, fill=WHITE, border=None, radius=0.08, shadow=True):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.adjustments[0] = radius
    if fill is None:
        shape.fill.background()
    else:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
    if border is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = border
        shape.line.width = Pt(1)
    shape.shadow.inherit = False
    if shadow:
        sp_pr = shape._element.spPr
        effect_lst = etree.SubElement(sp_pr, qn("a:effectLst"))
        outer = etree.SubElement(effect_lst, qn("a:outerShdw"))
        outer.set("blurRad", "76200")
        outer.set("dist", "25400")
        outer.set("dir", "5400000")
        outer.set("algn", "ctr")
        outer.set("rotWithShape", "0")
        clr = etree.SubElement(outer, qn("a:srgbClr"))
        clr.set("val", "1F2D3D")
        alpha = etree.SubElement(clr, qn("a:alpha"))
        alpha.set("val", "11000")
    return shape


def circle(slide, x, y, d, fill, border=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    if border is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = border
    shape.shadow.inherit = False
    return shape


def line(slide, x, y, w, color=BLUE, h=0.045):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    shape.shadow.inherit = False
    return shape


def pic_fit(slide, path, x, y, w, h):
    iw, ih = Image.open(path).size
    scale = min(w / iw, h / ih)
    nw, nh = iw * scale, ih * scale
    slide.shapes.add_picture(str(path), Inches(x + (w - nw) / 2), Inches(y + (h - nh) / 2), Inches(nw), Inches(nh))


def shot(slide, path, x, y, w, h, border=True):
    if border:
        rect(slide, x - 0.06, y - 0.06, w + 0.12, h + 0.12, fill=WHITE, border=LINE, radius=0.03, shadow=True)
    pic_fit(slide, path, x, y, w, h)


def header(slide, kicker, title):
    text(slide, 0.78, 0.42, 11.8, 0.3, kicker, size=10.5, color=BLUE, bold=True)
    text(slide, 0.78, 0.68, 11.8, 0.6, title, size=25, color=INK, bold=True)
    line(slide, 0.8, 1.33, 0.55)


def footer(slide, page):
    line(slide, 0.78, 7.04, 11.78, color=LINE, h=0.01)
    text(slide, 0.78, 7.12, 7, 0.22, "信息化运维管理系统", size=9, color=GRAY)
    text(slide, 11.5, 7.12, 1.05, 0.22, f"{page:02d}", size=9, color=GRAY, align=PP_ALIGN.RIGHT)


def new_slide(prs, bg=WHITE):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg_shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg_shape.fill.solid()
    bg_shape.fill.fore_color.rgb = bg
    bg_shape.line.fill.background()
    bg_shape.shadow.inherit = False
    return slide


def label(slide, x, y, w, num, title, sub=""):
    circle(slide, x, y + 0.02, 0.42, BLUE_LIGHT)
    text(slide, x, y + 0.09, 0.42, 0.28, str(num), size=11, color=BLUE, bold=True, align=PP_ALIGN.CENTER)
    text(slide, x + 0.58, y - 0.03, w - 0.58, 0.34, title, size=16.5, color=INK, bold=True)
    if sub:
        text(slide, x + 0.58, y + 0.34, w - 0.58, 0.3, sub, size=10, color=GRAY)


def build():
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)

    # ---------- 1 封面 ----------
    s = new_slide(prs, NAVY)
    circle(s, 9.7, -1.5, 5.0, NAVY_2)
    circle(s, 11.3, 4.2, 3.2, RGBColor(0x14, 0x29, 0x4B))
    rect(s, 0.82, 0.72, 0.5, 0.5, fill=BLUE, radius=0.22)
    text(s, 0.82, 0.81, 0.5, 0.3, "运", size=15, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    text(s, 1.42, 0.82, 5.5, 0.3, "信息化运维管理系统", size=12.5, color=RGBColor(0xC7, 0xD8, 0xF5), bold=True)

    text(s, 0.9, 2.35, 8.6, 1.6, "运维全流程\n一码就搞定", size=40, color=WHITE, bold=True, line=1.3)
    text(s, 0.95, 4.15, 8.0, 0.4, "报障 · 派单 · 物资 · 设备", size=15, color=RGBColor(0x9D, 0xC0, 0xFF))
    line(s, 0.98, 4.75, 1.1, color=BLUE_SOFT, h=0.05)
    text(s, 0.98, 5.05, 7.5, 0.3, "建设情况汇报", size=13, color=RGBColor(0x8F, 0xA6, 0xC8))
    text(s, 0.98, 6.55, 7.5, 0.3, "信息中心  ·  2026年11月", size=11, color=RGBColor(0x7F, 0x92, 0xB4))

    # 封面右侧两张截图卡片
    shot(s, ASSETS / "dashboard.png", 8.25, 1.35, 4.35, 2.72, border=False)
    shot(s, ASSETS / "tickets.png", 9.35, 4.25, 3.55, 2.22, border=False)
    # 卡片加细边框，避免和深色背景糊在一起
    for (x, y, w, h) in [(8.25, 1.35, 4.35, 2.72), (9.35, 4.25, 3.55, 2.22)]:
        r = rect(s, x - 0.02, y - 0.02, w + 0.04, h + 0.04, fill=None, border=RGBColor(0x33, 0x4C, 0x72), radius=0.02, shadow=False)
        r.fill.background()

    # ---------- 2 系统一览 ----------
    s = new_slide(prs)
    header(s, "OVERVIEW", "一个系统，四块核心能力")
    items = [
        ("dashboard.png", "工作台"),
        ("tickets.png", "派单"),
        ("materials.png", "物资"),
        ("assets.png", "设备"),
    ]
    x = 0.7
    for name, cap in items:
        shot(s, ASSETS / name, x, 1.85, 2.95, 1.84)
        text(s, x, 3.82, 2.95, 0.3, cap, size=13.5, color=INK, bold=True, align=PP_ALIGN.CENTER)
        x += 3.07
    text(s, 0.8, 4.75, 11.7, 0.5, "扫码报障 → 受理派单 → 上门处理 → 签字确认", size=18, color=BLUE, bold=True, align=PP_ALIGN.CENTER)
    text(s, 0.8, 5.4, 11.7, 0.35, "全流程留痕，数据自动沉淀", size=12, color=GRAY, align=PP_ALIGN.CENTER)
    stats = [("27", "工单"), ("9", "故障类型"), ("8", "设备"), ("13", "物资")]
    for i, (value, name) in enumerate(stats):
        x = 0.8 + i * 3.02
        text(s, x, 6.12, 1.0, 0.4, value, size=20, color=BLUE, bold=True)
        text(s, x + 0.72, 6.22, 1.8, 0.26, name, size=10, color=GRAY)
    footer(s, 2)

    # ---------- 3 五步闭环 ----------
    s = new_slide(prs)
    header(s, "WORKFLOW", "五步闭环")
    steps = ["扫码报障", "受理派单", "上门处理", "物资领用", "签字确认"]
    for i, name in enumerate(steps):
        x = 0.8 + i * 2.38
        rect(s, x, 1.62, 2.2, 0.95, fill=BLUE if i % 2 == 0 else BLUE_SOFT, radius=0.12, shadow=False)
        text(s, x + 0.18, 1.7, 0.4, 0.24, f"0{i + 1}", size=9.5, color=RGBColor(0xC9, 0xDC, 0xFF), bold=True)
        text(s, x + 0.18, 1.98, 1.9, 0.36, name, size=13.5, color=WHITE, bold=True)
    shot(s, ASSETS / "labels-row.png", 1.55, 3.1, 10.2, 3.2)
    text(s, 0.8, 6.48, 11.7, 0.3, "一房一码，贴门即用", size=10.5, color=GRAY, align=PP_ALIGN.CENTER)
    footer(s, 3)

    # ---------- 4 报障 ----------
    s = new_slide(prs)
    header(s, "REPORT", "报障：扫码即填")
    shot(s, ASSETS / "report_phone.png", 0.75, 1.5, 2.75, 5.4)
    shot(s, ASSETS / "signature-pad.png", 3.78, 3.65, 2.45, 2.2)
    text(s, 3.78, 3.38, 2.45, 0.24, "手写签字", size=9.5, color=GRAY, align=PP_ALIGN.CENTER)
    labels = [
        ("地点自动带入", "扫哪个房间，默认就是哪个房间"),
        ("立即上门 / 自选时间", "日期默认当天，可直接改时间"),
        ("现场照片", "最多 3 张，自动压缩"),
        ("手机号后四位查单", "不用记单号，确认时手写签名"),
    ]
    y = 1.6
    for i, (title, sub) in enumerate(labels):
        label(s, 6.7, y, 6.0, i + 1, title, sub)
        y += 1.28
    footer(s, 4)

    # ---------- 5 派单 ----------
    s = new_slide(prs)
    header(s, "DISPATCH", "派单：受理、改派、转派")
    shot(s, ASSETS / "tickets.png", 0.75, 1.5, 8.0, 5.0)
    labels = [
        ("受理与指派", "选择处理人，自动发邮件"),
        ("改派", "受理员随时改，立即生效"),
        ("转派接收", "对方确认后才变更处理人"),
    ]
    y = 1.7
    for i, (title, sub) in enumerate(labels):
        label(s, 9.05, y, 3.7, i + 1, title, sub)
        y += 1.6
    footer(s, 5)

    # ---------- 6 记录 ----------
    s = new_slide(prs)
    header(s, "RECORDS", "记录：每一步都有据可查")
    shot(s, ASSETS / "ticket-record.png", 0.8, 1.45, 3.35, 5.4)
    cards = [
        ("时间线", "受理到确认，全程时间点"),
        ("故障原因", "处理说明逐单留存"),
        ("现场照片", "原图保存，可回看"),
        ("签字评价", "签名、评分、评价归档"),
    ]
    pos = [(4.6, 1.55), (8.6, 1.55), (4.6, 3.3), (8.6, 3.3)]
    for (title, sub), (x, y) in zip(cards, pos):
        rect(s, x, y, 3.75, 1.45, fill=RGBColor(0xF7, 0xF9, 0xFE), border=LINE, radius=0.1, shadow=False)
        text(s, x + 0.3, y + 0.22, 3.2, 0.36, title, size=16, color=INK, bold=True)
        text(s, x + 0.3, y + 0.72, 3.2, 0.3, sub, size=10, color=GRAY)
    text(s, 4.6, 5.0, 8.0, 0.35, "工单、照片、签名、流水相互印证", size=13, color=BLUE, bold=True)
    shot(s, ASSETS / "demo-photo.jpg", 10.45, 5.5, 2.3, 1.4)
    footer(s, 6)

    # ---------- 7 物资 ----------
    s = new_slide(prs)
    header(s, "MATERIALS", "物资：领用即扣减")
    shot(s, ASSETS / "materials.png", 0.75, 1.5, 7.9, 4.94)
    shot(s, ASSETS / "stock-drawer.png", 6.3, 4.45, 2.25, 1.7)
    text(s, 6.3, 6.2, 2.25, 0.22, "流水关联工单", size=8.5, color=GRAY, align=PP_ALIGN.CENTER)
    labels = [
        ("领用登记", "处理时选物资与数量"),
        ("自动扣减", "提交即扣库存"),
        ("流水追溯", "工单、处理人、时间"),
    ]
    y = 1.7
    for i, (title, sub) in enumerate(labels):
        label(s, 9.05, y, 3.7, i + 1, title, sub)
        y += 1.55
    footer(s, 7)

    # ---------- 8 设备 ----------
    s = new_slide(prs)
    header(s, "ASSETS", "设备：一表掌握")
    shot(s, ASSETS / "assets.png", 0.75, 1.5, 7.9, 4.94)
    shot(s, ASSETS / "asset-drawer.png", 6.3, 4.35, 2.25, 1.8)
    text(s, 6.3, 6.2, 2.25, 0.22, "密码加密，仅管理员可见", size=8.5, color=GRAY, align=PP_ALIGN.CENTER)
    labels = [
        ("位置与上架", "房间、机柜、上架时间"),
        ("网络与账号", "IP、管理地址、账号"),
        ("Excel 批量导入", "也支持 CSV，逐行校验"),
    ]
    y = 1.7
    for i, (title, sub) in enumerate(labels):
        label(s, 9.05, y, 3.7, i + 1, title, sub)
        y += 1.55
    footer(s, 8)

    # ---------- 9 大屏 ----------
    s = new_slide(prs, NAVY)
    text(s, 0.8, 0.5, 10, 0.5, "大屏：新报障，第一时间看见", size=24, color=WHITE, bold=True)
    chips = ["语音播报", "超时预警", "今日值班"]
    x = 0.82
    for c in chips:
        r = rect(s, x, 1.18, 1.45, 0.4, fill=RGBColor(0x1C, 0x35, 0x5C), border=RGBColor(0x33, 0x4C, 0x72), radius=0.3, shadow=False)
        text(s, x, 1.26, 1.45, 0.26, c, size=10.5, color=RGBColor(0xC7, 0xD8, 0xF5), align=PP_ALIGN.CENTER)
        x += 1.58
    pic_fit(s, ASSETS / "board.png", 1.85, 1.75, 9.6, 5.2)
    footer(s, 9)

    # ---------- 10 权限与值班 ----------
    s = new_slide(prs)
    header(s, "PERMISSIONS", "权限与值班")
    shot(s, ASSETS / "duty-engineer.png", 0.75, 1.5, 7.5, 4.69)
    labels = [
        ("多角色", "受理员 + 工程师"),
        ("值班受理", "值班期间临时授权"),
        ("排班", "整周固定 + 临时调班"),
    ]
    y = 1.7
    for i, (title, sub) in enumerate(labels):
        label(s, 8.95, y, 3.8, i + 1, title, sub)
        y += 1.55
    footer(s, 10)

    # ---------- 11 数据 ----------
    s = new_slide(prs)
    header(s, "STATUS", "数据：一屏掌握")
    nums = [
        ("27", "工单"), ("9", "故障类型"), ("6", "状态"),
        ("8", "设备"), ("13", "物资"), ("8", "房间"),
    ]
    for i, (value, name) in enumerate(nums):
        row, col = divmod(i, 3)
        x = 0.8 + col * 4.0
        y = 1.75 + row * 2.45
        rect(s, x, y, 3.7, 2.05, fill=WHITE, border=LINE, radius=0.1, shadow=True)
        text(s, x + 0.35, y + 0.28, 2.8, 0.9, value, size=42, color=BLUE, bold=True)
        text(s, x + 0.38, y + 1.25, 2.8, 0.35, name, size=13, color=GRAY)
    footer(s, 11)

    # ---------- 12 安全 ----------
    s = new_slide(prs)
    header(s, "SECURITY", "安全：内网、加密、留痕")
    secs = [
        ("非涉密", "页面固定提示"),
        ("匿名身份", "Cookie 只存哈希"),
        ("密码加密", "设备密码仅管理员可见"),
        ("全程留痕", "日志、签名、照片"),
    ]
    for i, (title, sub) in enumerate(secs):
        row, col = divmod(i, 2)
        x = 0.8 + col * 5.95
        y = 1.7 + row * 2.35
        rect(s, x, y, 5.7, 1.95, fill=WHITE, border=LINE, radius=0.1, shadow=True)
        text(s, x + 0.4, y + 0.35, 4.9, 0.45, title, size=22, color=INK, bold=True)
        text(s, x + 0.42, y + 1.05, 4.8, 0.35, sub, size=11, color=GRAY)
    text(s, 0.8, 6.35, 11.7, 0.35, "涉密不上网，上网不涉密", size=14, color=BLUE, bold=True, align=PP_ALIGN.CENTER)
    footer(s, 12)

    # ---------- 13 计划 ----------
    s = new_slide(prs)
    header(s, "ROADMAP", "下一步")
    phases = [
        ("试点", "1 个月", ["贴码", "建台账", "培训"]),
        ("推广", "3 个月", ["全覆盖", "邮件提醒", "值班大屏"]),
        ("深化", "6 个月+", ["报表", "盘点", "移动端"]),
    ]
    for i, (title, term, items) in enumerate(phases):
        x = 0.8 + i * 4.02
        rect(s, x, 1.75, 3.8, 3.85, fill=WHITE, border=LINE, radius=0.1, shadow=True)
        text(s, x + 0.35, 2.0, 3.0, 0.45, title, size=24, color=BLUE, bold=True)
        text(s, x + 0.35, 2.55, 3.0, 0.3, term, size=11, color=GRAY)
        yy = 3.25
        for item in items:
            circle(s, x + 0.4, yy + 0.06, 0.12, BLUE)
            text(s, x + 0.7, yy - 0.03, 2.6, 0.4, item, size=14, color=INK_2)
            yy += 0.75
    footer(s, 13)

    # ---------- 14 结束 ----------
    s = new_slide(prs, NAVY)
    circle(s, 10.3, -1.2, 4.2, NAVY_2)
    text(s, 0.95, 2.5, 9.0, 0.9, "谢谢", size=46, color=WHITE, bold=True)
    line(s, 0.98, 3.55, 1.0, color=BLUE_SOFT, h=0.05)
    text(s, 0.98, 3.9, 8.5, 0.35, "信息化运维管理系统", size=15, color=RGBColor(0x9D, 0xC0, 0xFF))
    text(s, 0.98, 4.35, 8.5, 0.3, "请批评指正", size=11, color=RGBColor(0x8F, 0xA6, 0xC8))

    speech = [
        "开场：一码报障、全流程留痕，是这套系统的核心。",
        "一屏四图：工作台、派单、物资、设备。",
        "五步闭环：扫码、派单、上门、领料、签字。",
        "报障端：扫码即填，立即或自选时间，照片与签字。",
        "派单：受理指派、改派、转派接收。",
        "记录：时间线、原因、照片、签名都可查。",
        "物资：登记即扣减，流水关联工单。",
        "设备：位置、上架、网络、账号一表掌握。",
        "大屏：语音播报、超时预警、今日值班。",
        "权限：多角色，值班临时受理。",
        "数据：演示环境六项指标。",
        "安全：非涉密、加密、留痕。",
        "计划：试点、推广、深化。",
        "结束：请批评指正。",
    ]
    for i, content in enumerate(speech):
        prs.slides[i].notes_slide.notes_text_frame.text = content

    prs.save(OUT)
    print("saved", OUT, "slides:", len(prs.slides))


if __name__ == "__main__":
    build()
