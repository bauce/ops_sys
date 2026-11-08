"""生成《信息化运维管理系统》汇报 PPT。"""
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt
from lxml import etree

BASE = Path(__file__).resolve().parent.parent
ASSETS = BASE / "build" / "ppt-assets"
OUT = BASE / "信息化运维管理系统-建设汇报.pptx"

FONT = "PingFang SC"
NAVY = RGBColor(0x0F, 0x1E, 0x38)
NAVY_2 = RGBColor(0x16, 0x2C, 0x50)
BLUE = RGBColor(0x2F, 0x6F, 0xEB)
BLUE_LIGHT = RGBColor(0xEA, 0xF1, 0xFF)
BLUE_SOFT = RGBColor(0x4F, 0x8C, 0xFF)
INK = RGBColor(0x1F, 0x29, 0x37)
INK_2 = RGBColor(0x4B, 0x55, 0x63)
GRAY = RGBColor(0x8A, 0x94, 0xA6)
LINE = RGBColor(0xE4, 0xE9, 0xF2)
BG = RGBColor(0xF6, 0xF8, 0xFC)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREEN = RGBColor(0x34, 0xA8, 0x53)
ORANGE = RGBColor(0xE6, 0xA2, 0x3C)
PURPLE = RGBColor(0x7A, 0x5C, 0xD1)
RED = RGBColor(0xD9, 0x53, 0x4F)

W, H = 13.333, 7.5


def _set_font(run, size=None, color=None, bold=None, name=FONT, italic=None):
    font = run.font
    if size is not None:
        font.size = Pt(size)
    if color is not None:
        font.color.rgb = color
    if bold is not None:
        font.bold = bold
    if italic is not None:
        font.italic = italic
    font.name = name
    rpr = run._r.get_or_add_rPr()
    ea = rpr.find(qn("a:ea"))
    if ea is None:
        ea = etree.SubElement(rpr, qn("a:ea"))
    ea.set("typeface", name)


def text(slide, x, y, w, h, content, size=14, color=INK, bold=False,
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, line=None, font=FONT,
         space_after=0, margins=(0, 0, 0, 0)):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left, tf.margin_right, tf.margin_top, tf.margin_bottom = [Inches(m) for m in margins]
    tf.vertical_anchor = anchor
    lines = content.split("\n") if isinstance(content, str) else content
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if line:
            p.line_spacing = line
        p.space_after = Pt(space_after)
        r = p.add_run()
        r.text = ln
        _set_font(r, size=size, color=color, bold=bold, name=font)
    return box


def rect(slide, x, y, w, h, fill=WHITE, border=None, radius=0.08, shadow=False):
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
        alpha.set("val", "12000")
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


def header(slide, kicker, title, sub=None):
    text(slide, 0.78, 0.42, 11.9, 0.32, kicker, size=11, color=BLUE, bold=True)
    text(slide, 0.78, 0.68, 11.9, 0.62, title, size=25, color=INK, bold=True)
    line(slide, 0.8, 1.38, 0.62)
    if sub:
        text(slide, 0.78, 1.5, 11.8, 0.32, sub, size=12.5, color=GRAY)


def footer(slide, page):
    line(slide, 0.78, 7.02, 11.78, color=LINE, h=0.012)
    text(slide, 0.78, 7.1, 7, 0.24, "信息化运维管理系统 · 建设汇报", size=9, color=GRAY)
    text(slide, 11.3, 7.1, 1.26, 0.24, f"{page:02d}", size=9, color=GRAY, align=PP_ALIGN.RIGHT)


def new_slide(prs, bg=WHITE):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg_shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg_shape.fill.solid()
    bg_shape.fill.fore_color.rgb = bg
    bg_shape.line.fill.background()
    bg_shape.shadow.inherit = False
    return slide


def chip(slide, x, y, w, h, label, fill=BLUE_LIGHT, color=BLUE, size=11):
    rect(slide, x, y, w, h, fill=fill, radius=0.5)
    text(slide, x, y + 0.03, w, h - 0.06, label, size=size, color=color,
         align=PP_ALIGN.CENTER, bold=True)


def build():
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)

    # ---------------- 1 封面 ----------------
    s = new_slide(prs, NAVY)
    circle(s, 9.9, -1.6, 4.9, RGBColor(0x17, 0x2E, 0x55))
    circle(s, 11.2, 4.1, 3.4, RGBColor(0x14, 0x29, 0x4B))
    rect(s, 0.82, 0.72, 0.52, 0.52, fill=BLUE, radius=0.22)
    text(s, 0.82, 0.82, 0.52, 0.32, "运", size=16, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    text(s, 1.46, 0.83, 6, 0.3, "信息化运维管理系统", size=13, color=RGBColor(0xC7, 0xD8, 0xF5), bold=True)

    text(s, 0.9, 2.0, 9.5, 0.9, "信息化运维管理系统", size=42, color=WHITE, bold=True)
    text(s, 0.95, 3.02, 8, 0.5, "建设情况汇报", size=24, color=RGBColor(0x9D, 0xC0, 0xFF))
    line(s, 0.98, 3.78, 1.15, color=BLUE_SOFT, h=0.05)
    text(s, 0.98, 4.15, 8, 0.3, "设备报障  ·  派单处置  ·  物资管理  ·  数据看板", size=13,
         color=RGBColor(0x8F, 0xA6, 0xC8))
    text(s, 0.98, 5.95, 8, 0.3, "汇报单位：信息中心      2026年11月", size=12,
         color=RGBColor(0x8F, 0xA6, 0xC8))
    text(s, 9.55, 6.55, 3.2, 0.3, "内部交流材料", size=11, color=RGBColor(0x5F, 0x77, 0x9E), align=PP_ALIGN.RIGHT)

    # ---------------- 2 提纲 ----------------
    s = new_slide(prs)
    header(s, "CONTENTS", "汇报提纲")
    items = [
        ("01", "背景与方案", "报障痛点、一房一码与全流程闭环"),
        ("02", "派单管理", "受理、指派、改派、转派与邮件通知"),
        ("03", "记录与物资", "处置过程留痕、物资领用与库存扣减"),
        ("04", "设备管理", "资产位置、上架时间、网络与账号"),
        ("05", "成效与计划", "数据覆盖、安全合规与推广安排"),
    ]
    y = 1.78
    for num, title, desc in items:
        text(s, 0.92, y - 0.04, 0.8, 0.5, num, size=24, color=BLUE, bold=True)
        text(s, 1.75, y - 0.06, 4.2, 0.4, title, size=17, color=INK, bold=True)
        text(s, 1.75, y + 0.34, 5.6, 0.3, desc, size=11.5, color=GRAY)
        line(s, 0.92, y + 0.72, 5.95, color=LINE, h=0.01)
        y += 0.98

    rect(s, 8.2, 1.78, 4.3, 4.55, fill=RGBColor(0xF2, 0xF7, 0xFF), border=RGBColor(0xD9, 0xE6, 0xFB), radius=0.06)
    text(s, 8.55, 2.0, 3.6, 0.3, "一套系统，四类角色", size=13, color=BLUE, bold=True)
    text(s, 8.55, 2.45, 3.6, 0.9, "从一线扫码报障\n到运维闭环归档", size=16, color=INK, bold=True, line=1.35)
    stats = [("4", "类使用角色"), ("9", "个功能模块"), ("27", "条演示工单")]
    yy = 3.6
    for value, label in stats:
        text(s, 8.55, yy, 1.3, 0.55, value, size=26, color=BLUE, bold=True)
        text(s, 9.65, yy + 0.15, 2.4, 0.3, label, size=11.5, color=GRAY)
        yy += 0.85
    footer(s, 2)

    # ---------------- 3 背景痛点 ----------------
    s = new_slide(prs)
    header(s, "BACKGROUND", "为什么要建这套系统", "运维报障长期依赖电话与口头传达，过程不可见、责任难追溯、数据难沉淀")
    pains = [
        ("报", "报障靠电话", "故障现象描述不清，地点只能靠口头说，容易跑错现场", ORANGE),
        ("址", "地点说不清", "同一人多个办公地点，报障时无法准确对应房间与设备", BLUE),
        ("踪", "进度靠追问", "处理到哪一步、谁在跟进，报障人只能反复打电话", PURPLE),
        ("料", "物资靠台账", "领用与工单对不上，库存账实不符，月底盘点费时", GREEN),
        ("数", "数据靠回忆", "报障量、响应时长、耗材成本没有沉淀，无法量化考核", RED),
    ]
    for i, (char, title, desc, color) in enumerate(pains):
        row, col = divmod(i, 3)
        if row == 0:
            x = 0.8 + col * 3.98
        else:
            x = 2.65 + (i - 3) * 4.0
        y = 1.92 + row * 1.75
        rect(s, x, y, 3.78, 1.5, fill=WHITE, border=LINE, radius=0.09, shadow=True)
        rect(s, x + 0.22, y + 0.22, 0.46, 0.46, fill=RGBColor(0xF2, 0xF7, 0xFF), radius=0.25)
        text(s, x + 0.22, y + 0.28, 0.46, 0.3, char, size=13, color=color, bold=True, align=PP_ALIGN.CENTER)
        text(s, x + 0.82, y + 0.2, 2.75, 0.32, title, size=14, color=INK, bold=True)
        text(s, x + 0.82, y + 0.58, 2.72, 0.78, desc, size=10.5, color=GRAY, line=1.25)

    text(s, 0.8, 5.95, 11.7, 0.45, "一线要快，管理要清，责任要明。", size=22, color=BLUE, bold=True, align=PP_ALIGN.CENTER)
    text(s, 0.8, 6.45, 11.7, 0.3, "用最小使用成本，换取全流程的数据与留痕。", size=12, color=GRAY, align=PP_ALIGN.CENTER)
    footer(s, 3)

    # ---------------- 4 目标思路 ----------------
    s = new_slide(prs)
    header(s, "OBJECTIVES", "建设思路：一房一码，扫码即报")
    text(s, 0.8, 1.68, 11.8, 0.6, "把报障入口装进二维码，把处置过程装进系统。", size=27, color=INK, bold=True)
    text(s, 0.82, 2.3, 11.6, 0.34, "不改变现有组织分工，用最轻的方式采集数据、驱动协同。", size=13, color=GRAY)
    pillars = [
        ("零门槛", "无需账号、无需安装，手机扫码即可报障，地点自动带入", BLUE),
        ("全闭环", "受理、派单、上门、物资、签字、评价，六种状态全程可见", GREEN),
        ("可追溯", "处理人、时间、物资领用、现场照片与签名逐单留痕", ORANGE),
        ("可分析", "报障量、故障类型、响应时长、耗材成本自动沉淀", PURPLE),
    ]
    for i, (title, desc, color) in enumerate(pillars):
        x = 0.8 + i * 3.02
        rect(s, x, 3.05, 2.8, 2.55, fill=WHITE, border=LINE, radius=0.08, shadow=True)
        line(s, x + 0.02, 3.05, 0.55, color=color, h=0.07)
        text(s, x + 0.3, 3.32, 2.2, 0.4, title, size=19, color=INK, bold=True)
        text(s, x + 0.3, 3.86, 2.25, 1.4, desc, size=11, color=GRAY, line=1.4)
        text(s, x + 1.85, 4.75, 0.85, 0.55, f"0{i + 1}", size=30, color=RGBColor(0xEE, 0xF4, 0xFE), bold=True,
             align=PP_ALIGN.RIGHT)
    text(s, 0.8, 5.95, 11.75, 0.4, "二维码即入口 · 手机号后四位即凭证 · 手写签名即验收", size=15,
         color=BLUE, bold=True, align=PP_ALIGN.CENTER)
    footer(s, 4)

    # ---------------- 5 流程 ----------------
    s = new_slide(prs)
    header(s, "WORKFLOW", "业务流程：从扫码到归档的完整闭环")
    steps = [
        ("01", "扫码报障", "地点自动带入\n可切换实际位置"),
        ("02", "受理派单", "选择上门人员\n邮件自动通知"),
        ("03", "上门处理", "填写故障原因\n处理过程说明"),
        ("04", "物资领用", "登记领用配件\n库存自动扣减"),
        ("05", "签字确认", "报障人评价\n手写签名归档"),
    ]
    x = 0.8
    for i, (num, title, desc) in enumerate(steps):
        rect(s, x, 1.95, 2.08, 1.0, fill=BLUE if i % 2 == 0 else RGBColor(0x3F, 0x7D, 0xF4), radius=0.12)
        text(s, x + 0.18, 2.05, 0.4, 0.28, num, size=11, color=RGBColor(0xC9, 0xDC, 0xFF), bold=True)
        text(s, x + 0.18, 2.32, 1.75, 0.4, title, size=15, color=WHITE, bold=True)
        text(s, x + 0.02, 3.1, 2.05, 0.85, desc, size=10.5, color=INK_2, align=PP_ALIGN.CENTER, line=1.35)
        if i < 4:
            arrow = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x + 2.14), Inches(2.33), Inches(0.22), Inches(0.22))
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = RGBColor(0xB7, 0xC7, 0xE2)
            arrow.line.fill.background()
        x += 2.38
    rect(s, 0.8, 4.25, 11.75, 0.92, fill=RGBColor(0xF7, 0xF9, 0xFE), border=LINE, radius=0.06)
    text(s, 1.05, 4.42, 11.2, 0.6, "分支处理：未使用物资可跳过登记  ·  工程师转派需对方接收  ·  电话报障由受理员代录  ·  超时工单自动预警",
         size=11.5, color=INK_2)
    text(s, 0.8, 5.55, 11.7, 0.35, "每一次流转自动记录：时间 · 处理人 · 物资 · 照片 · 签名", size=15,
         color=BLUE, bold=True, align=PP_ALIGN.CENTER)
    text(s, 0.8, 6.0, 11.7, 0.3, "状态：待受理 → 已受理 → 处理中 → 待确认 → 已完成（可撤销）", size=11, color=GRAY,
         align=PP_ALIGN.CENTER)
    footer(s, 5)

    # ---------------- 6 架构 ----------------
    s = new_slide(prs)
    header(s, "ARCHITECTURE", "总体架构与技术选型", "轻量单机部署，局域网内手机可直接扫码使用，数据全部留在本地")
    layers = [
        ("展示层", "手机扫码报障页   ·   运维管理后台   ·   受理中心语音大屏", BLUE),
        ("应用层", "工单流转  ·  物资管理  ·  二维码  ·  权限  ·  值班  ·  通知", RGBColor(0x3F, 0x7D, 0xF4)),
        ("数据层", "SQLite 单文件数据库  ·  现场照片  ·  配置与操作日志", RGBColor(0x5A, 0x90, 0xFF)),
        ("集成层", "SMTP 邮件提醒  ·  浏览器语音合成  ·  二维码生成", RGBColor(0x7F, 0xA8, 0xFF)),
    ]
    y = 1.9
    for label, body, color in layers:
        rect(s, 0.8, y, 1.25, 0.92, fill=color, radius=0.12)
        text(s, 0.8, y + 0.25, 1.25, 0.4, label, size=12, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
        rect(s, 2.15, y, 6.05, 0.92, fill=WHITE, border=LINE, radius=0.08)
        text(s, 2.4, y + 0.13, 5.7, 0.66, body, size=11.5, color=INK_2, anchor=MSO_ANCHOR.MIDDLE, line=1.3)
        y += 1.12
    rect(s, 8.55, 1.9, 3.95, 4.35, fill=RGBColor(0xF7, 0xF9, 0xFE), border=LINE, radius=0.07)
    text(s, 8.85, 2.1, 3.4, 0.3, "技术选型", size=13, color=BLUE, bold=True)
    stack = ["Vue 3 + Element Plus", "FastAPI + SQLite", "qrcode + Pillow", "SMTP / Web Speech"]
    yy = 2.55
    for item in stack:
        rect(s, 8.85, yy, 3.35, 0.5, fill=WHITE, border=RGBColor(0xD9, 0xE6, 0xFB), radius=0.18)
        text(s, 9.05, yy + 0.1, 3.0, 0.3, item, size=10.5, color=INK_2, bold=True)
        yy += 0.62
    line(s, 8.85, 5.18, 3.35, color=LINE, h=0.012)
    text(s, 8.85, 5.32, 3.3, 0.75, "部署：一台内网电脑即可\n访问：局域网 IP / 手机扫码\n备份：拷贝 data 目录",
         size=10, color=GRAY, line=1.45)
    footer(s, 6)

    # ---------------- 7 报障端 ----------------
    s = new_slide(prs)
    header(s, "REPORT", "报障端：把复杂留给系统，把简单留给一线")
    rect(s, 0.78, 1.7, 3.1, 5.12, fill=RGBColor(0xF2, 0xF6, 0xFD), radius=0.06)
    pic_fit(s, ASSETS / "report_phone.png", 0.92, 1.78, 2.82, 4.96)

    points = [
        ("地点自动带入，也可切换", "扫哪个房间的码，默认就是哪个房间；多处办公可改选实际位置"),
        ("期待上门时间可选", "立即上门，或自选日期与时间点（默认当天），调度一目了然"),
        ("现场照片 + 保密提醒", "最多 3 张现场照片自动压缩；页面固定提示严禁上传涉密信息"),
        ("手机号后四位查单", "无需记单号，换手机也能找回工单；确认时手写签名并评价"),
    ]
    y = 1.78
    for i, (title, desc) in enumerate(points):
        circle(s, 4.25, y + 0.02, 0.34, BLUE_LIGHT)
        text(s, 4.25, y + 0.06, 0.34, 0.24, str(i + 1), size=10, color=BLUE, bold=True, align=PP_ALIGN.CENTER)
        text(s, 4.78, y - 0.02, 7.6, 0.34, title, size=14.5, color=INK, bold=True)
        text(s, 4.78, y + 0.34, 7.7, 0.55, desc, size=10.5, color=GRAY, line=1.35)
        y += 1.06
    rect(s, 4.25, 6.15, 8.2, 0.58, fill=BLUE_LIGHT, radius=0.12)
    text(s, 4.45, 6.26, 7.9, 0.34, "普通用户无需账号、无需安装，扫码即报，提交即有单号。", size=12,
         color=BLUE, bold=True)
    footer(s, 7)

    # ---------------- 8 派单管理 ----------------
    s = new_slide(prs)
    header(s, "DISPATCH", "派单管理：受理、指派、改派、转派一条链")
    rect(s, 0.78, 1.7, 7.05, 4.55, fill=WHITE, border=LINE, radius=0.05, shadow=True)
    pic_fit(s, ASSETS / "tickets.png", 0.86, 1.78, 6.89, 4.39)
    items = [
        ("受理与指派", "待受理清单一键受理，选择处理人；新处理人自动收到邮件"),
        ("改派", "受理员随时改派，立即生效，并重新通知处理人"),
        ("转派接收", "工程师转派需对方确认，确认前原处理人继续负责"),
        ("状态与预警", "六种状态、期望上门时间实时可见，超时自动标红"),
    ]
    y = 1.8
    for i, (title, desc) in enumerate(items):
        line(s, 8.1, y + 0.02, 0.05, color=BLUE if i % 2 == 0 else BLUE_SOFT, h=0.42)
        text(s, 8.32, y - 0.04, 4.3, 0.32, title, size=14.5, color=INK, bold=True)
        text(s, 8.32, y + 0.32, 4.2, 0.78, desc, size=10.5, color=GRAY, line=1.35)
        y += 1.2
    text(s, 8.12, 6.45, 4.4, 0.3, "谁受理、派给谁、何时改派，全部写入工单日志", size=10.5, color=BLUE, bold=True)
    footer(s, 8)

    # ---------------- 9 记录与留痕 ----------------
    s = new_slide(prs)
    header(s, "RECORDS", "全过程记录：每一次处理都有据可查", "工单详情一屏还原从报障、派单、处理到确认的完整过程")
    rect(s, 0.78, 1.7, 3.62, 5.08, fill=WHITE, border=LINE, radius=0.05, shadow=True)
    pic_fit(s, ASSETS / "ticket-record.png", 0.9, 1.8, 3.38, 4.88)
    records = [
        ("时间线", "提交、受理、指派、开始、完成、确认，每一步都有时间与操作人"),
        ("故障与处理", "故障原因、处理说明逐单保存，形成可复用经验"),
        ("现场照片", "报障人上传的设备现场照片原图留存"),
        ("物资记录", "领用物资、数量与出库流水自动关联工单"),
        ("签字与评价", "手写签名、满意度与确认时间一并归档"),
    ]
    yy = 1.78
    for i, (title, desc) in enumerate(records):
        circle(s, 4.85, yy + 0.02, 0.34, BLUE_LIGHT)
        text(s, 4.85, yy + 0.06, 0.34, 0.24, str(i + 1), size=10, color=BLUE, bold=True, align=PP_ALIGN.CENTER)
        text(s, 5.38, yy - 0.02, 7.0, 0.3, title, size=14, color=INK, bold=True)
        text(s, 5.38, yy + 0.32, 7.2, 0.5, desc, size=10.5, color=GRAY, line=1.3)
        yy += 0.9
    rect(s, 4.85, 6.35, 7.7, 0.55, fill=BLUE_LIGHT, radius=0.12)
    text(s, 5.08, 6.46, 7.3, 0.32, "工单、日志、照片、签名、流水相互印证，责任到人、过程可查。",
         size=10.5, color=BLUE, bold=True)
    footer(s, 9)

    # ---------------- 10 物资领用 ----------------
    s = new_slide(prs)
    header(s, "MATERIALS", "物资领用：登记即扣减，领用可追溯")
    rect(s, 0.78, 1.7, 6.55, 4.4, fill=WHITE, border=LINE, radius=0.05, shadow=True)
    pic_fit(s, ASSETS / "materials.png", 0.86, 1.78, 6.39, 4.24)
    items = [
        ("领用登记", "处理工单时选择物资与数量，一键登记"),
        ("自动扣减", "提交即扣库存，并生成出库流水"),
        ("关联工单", "每条流水可回溯到工单、处理人与时间"),
        ("未用跳过", "本次未使用物资可勾选跳过，不产生出库"),
    ]
    y = 1.8
    for i, (title, desc) in enumerate(items):
        circle(s, 7.75, y + 0.03, 0.3, BLUE_LIGHT)
        text(s, 7.75, y + 0.07, 0.3, 0.22, str(i + 1), size=9.5, color=BLUE, bold=True, align=PP_ALIGN.CENTER)
        text(s, 8.2, y - 0.04, 4.3, 0.32, title, size=14, color=INK, bold=True)
        text(s, 8.2, y + 0.31, 4.2, 0.6, desc, size=10.5, color=GRAY, line=1.35)
        y += 1.1
    chips = [("13", "种物资台账"), ("2", "条演示领用"), ("实时", "库存预警")]
    for i, (value, label) in enumerate(chips):
        x = 7.75 + i * 1.62
        text(s, x, 6.2, 1.0, 0.32, value, size=16, color=BLUE, bold=True)
        text(s, x, 6.5, 1.5, 0.24, label, size=9, color=GRAY)
    footer(s, 10)

    # ---------------- 11 设备管理 ----------------
    s = new_slide(prs)
    header(s, "ASSETS", "设备管理：资产、位置、网络、账号一表掌握")
    rect(s, 0.78, 1.7, 6.6, 4.45, fill=WHITE, border=LINE, radius=0.05, shadow=True)
    pic_fit(s, ASSETS / "assets.png", 0.86, 1.78, 6.44, 4.29)
    items = [
        ("资产台账", "编号、型号、序列号、房间、机柜、上架时间、保修与责任人"),
        ("网络与账号", "网络/VLAN、管理地址、端口、账号密码集中记录"),
        ("批量导入", "Excel / CSV 模板导入，逐行校验并提示错误行"),
        ("安全查看", "密码加密存储，仅管理员可查看明文"),
    ]
    y = 1.8
    for i, (title, desc) in enumerate(items):
        line(s, 7.78, y + 0.02, 0.05, color=BLUE if i % 2 == 0 else BLUE_SOFT, h=0.4)
        text(s, 8.0, y - 0.04, 4.4, 0.3, title, size=13.5, color=INK, bold=True)
        text(s, 8.0, y + 0.3, 4.3, 0.75, desc, size=10.5, color=GRAY, line=1.35)
        y += 1.15
    text(s, 7.8, 6.35, 4.6, 0.3, "8 台演示设备 · 按类型 / 状态 / 房间筛选", size=10.5, color=BLUE, bold=True)
    footer(s, 11)

    # ---------------- 10 大屏 ----------------
    s = new_slide(prs, NAVY)
    text(s, 0.8, 0.5, 6, 0.3, "MONITORING", size=11, color=BLUE_SOFT, bold=True)
    text(s, 0.8, 0.78, 6.2, 1.2, "让每一张新报障\n第一时间被看见", size=27, color=WHITE, bold=True, line=1.25)
    line(s, 0.82, 2.28, 0.62, color=BLUE_SOFT)
    points = [
        ("邮件派单", "派单、改派、转派自动发信，带工单直达链接"),
        ("语音播报", "大屏 8 秒轮询，新单自动响铃并播报地点设备"),
        ("超时预警", "待受理/上门/处理分级预警，红色卡片置顶"),
    ]
    y = 2.95
    for i, (title, desc) in enumerate(points):
        circle(s, 0.84, y, 0.32, RGBColor(0x1C, 0x35, 0x5C))
        text(s, 0.84, y + 0.05, 0.32, 0.22, str(i + 1), size=9.5, color=BLUE_SOFT, bold=True, align=PP_ALIGN.CENTER)
        text(s, 1.35, y - 0.05, 4.0, 0.3, title, size=14, color=WHITE, bold=True)
        text(s, 1.35, y + 0.3, 3.9, 0.55, desc, size=10, color=RGBColor(0x9F, 0xB2, 0xD0), line=1.35)
        y += 1.28
    rect(s, 5.38, 1.1, 7.4, 5.45, fill=RGBColor(0x0B, 0x14, 0x24), border=RGBColor(0x2A, 0x3D, 0x5C), radius=0.03)
    pic_fit(s, ASSETS / "board.png", 5.45, 1.17, 7.25, 5.3)
    text(s, 0.82, 6.7, 4.2, 0.3, "今日值班与超时数量，在大屏顶部一屏可见", size=10, color=RGBColor(0x7F, 0x92, 0xB4))
    text(s, 11.0, 6.85, 1.5, 0.24, "12", size=9, color=RGBColor(0x5F, 0x77, 0x9E), align=PP_ALIGN.RIGHT)

    # ---------------- 11 权限与值班 ----------------
    s = new_slide(prs)
    header(s, "PERMISSIONS", "权限与值班：一套账号，多种角色")
    rect(s, 0.78, 1.7, 6.5, 4.45, fill=WHITE, border=LINE, radius=0.05, shadow=True)
    pic_fit(s, ASSETS / "duty-engineer.png", 0.86, 1.78, 6.34, 4.29)
    items = [
        ("多角色取并集", "同一账号可同时是受理员与工程师，权限自动合并"),
        ("值班临时受理", "工程师值班期间自动获得受理派单权限，值班结束收回"),
        ("整周 + 临时调班", "一周固定 2 人以上，某天某时段可临时换人"),
        ("分级管理账号", "管理员管全部；受理员只维护工程师账号"),
    ]
    y = 1.8
    for i, (title, desc) in enumerate(items):
        line(s, 7.72, y + 0.02, 0.05, color=BLUE if i % 2 == 0 else BLUE_SOFT, h=0.4)
        text(s, 7.95, y - 0.04, 4.5, 0.3, title, size=13.5, color=INK, bold=True)
        text(s, 7.95, y + 0.3, 4.4, 0.65, desc, size=10.5, color=GRAY, line=1.35)
        y += 1.17
    footer(s, 13)

    # ---------------- 12 运行成效 ----------------
    s = new_slide(prs)
    header(s, "STATUS", "运行情况：数据已覆盖全流程", "以下为演示环境数据，用于验证功能与展示效果")
    kpis = [("27", "演示工单", BLUE), ("9", "故障类型", PURPLE), ("6", "工单状态", GREEN),
            ("8", "设备台账", ORANGE), ("13", "物资种类", RGBColor(0x3F, 0x7D, 0xF4)),
            ("8", "报障房间", RGBColor(0x6B, 0x7A, 0x90))]
    for i, (value, label, color) in enumerate(kpis):
        x = 0.8 + i * 1.99
        rect(s, x, 1.88, 1.82, 1.12, fill=WHITE, border=LINE, radius=0.08, shadow=True)
        text(s, x + 0.18, 1.98, 1.1, 0.5, value, size=24, color=color, bold=True)
        text(s, x + 0.18, 2.55, 1.55, 0.28, label, size=10, color=GRAY)

    text(s, 0.8, 3.32, 7.5, 0.3, "工单状态分布", size=13, color=INK, bold=True)
    statuses = [("待受理", 5, ORANGE), ("已受理", 5, BLUE), ("处理中", 5, RGBColor(0x3F, 0x7D, 0xF4)),
                ("待确认", 4, RGBColor(0xB8, 0x82, 0x30)), ("已完成", 4, GREEN), ("已取消", 4, GRAY)]
    total = sum(v for _, v, _ in statuses)
    x = 0.8
    bar_w = 7.5
    for name, value, color in statuses:
        w = bar_w * value / total
        rect(s, x, 3.72, w - 0.03, 0.52, fill=color, radius=0.12)
        text(s, x, 3.85, w, 0.26, str(value), size=10, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
        text(s, x, 4.35, w, 0.26, name, size=9.5, color=GRAY, align=PP_ALIGN.CENTER)
        x += w
    text(s, 0.8, 4.85, 7.5, 0.3, "演示数据含：4 条签字确认、3 条现场照片、2 条物资领用、1 条待接收转派",
         size=10, color=GRAY)

    rect(s, 0.8, 6.02, 11.75, 0.72, fill=RGBColor(0xF2, 0xF7, 0xFF), border=RGBColor(0xD9, 0xE6, 0xFB), radius=0.12)
    text(s, 1.05, 6.2, 11.3, 0.32,
         "报障有入口：一房一码，扫码即报      |      处置有闭环：受理、上门、物资、签字      |      管理有数据：状态、时长、耗材可统计",
         size=10.5, color=RGBColor(0x2C, 0x5A, 0xA8), bold=True)

    rect(s, 8.7, 3.3, 3.85, 2.5, fill=RGBColor(0xF7, 0xF9, 0xFE), border=LINE, radius=0.07)
    text(s, 8.95, 3.48, 3.4, 0.3, "角色已全部覆盖", size=12.5, color=BLUE, bold=True)
    roles = [("系统管理员", "全局配置与账号"), ("报障受理员", "受理、派单、物资"),
             ("运维工程师", "处理、转派"), ("值班受理", "值班期间临时授权")]
    yy = 3.9
    for name, desc in roles:
        text(s, 8.95, yy, 1.4, 0.26, name, size=10, color=INK, bold=True)
        text(s, 10.25, yy, 2.2, 0.26, desc, size=9.5, color=GRAY)
        yy += 0.46
    footer(s, 14)

    # ---------------- 13 安全合规 ----------------
    s = new_slide(prs)
    header(s, "SECURITY", "安全与合规：内网使用，全程留痕")
    notes = [
        "已内置：报障页与照片处双重提示",
        "已内置：Cookie 仅存哈希",
        "已内置：首次登录请改默认密码",
        "已内置：逐单可回溯、可导出",
    ]
    cards = [
        ("非涉密定位", "报障页与照片上传处固定提示：非涉密系统，严禁上传涉密信息", RED),
        ("匿名身份安全", "报障人 Cookie 随机 128 位，数据库仅存 SHA-256 哈希，180 天有效", BLUE),
        ("账号与会话", "PBKDF2-SHA256 加盐存储密码，会话 7 天过期，支持启停与重置", PURPLE),
        ("操作全程留痕", "工单日志、签字图片、物资流水、照片原图逐单可查，SQLite 单文件备份", GREEN),
    ]
    for i, (title, desc, color) in enumerate(cards):
        row, col = divmod(i, 2)
        x = 0.8 + col * 6.0
        y = 1.88 + row * 2.05
        rect(s, x, y, 5.7, 1.75, fill=WHITE, border=LINE, radius=0.08, shadow=True)
        rect(s, x + 0.25, y + 0.28, 0.5, 0.5, fill=RGBColor(0xF4, 0xF7, 0xFC), radius=0.2)
        text(s, x + 0.25, y + 0.36, 0.5, 0.3, str(i + 1), size=13, color=color, bold=True, align=PP_ALIGN.CENTER)
        text(s, x + 0.95, y + 0.25, 4.5, 0.32, title, size=15, color=INK, bold=True)
        text(s, x + 0.95, y + 0.68, 4.45, 0.9, desc, size=10.5, color=GRAY, line=1.4)
        text(s, x + 0.95, y + 1.32, 4.4, 0.26, notes[i], size=9.5, color=BLUE)
    rect(s, 0.8, 6.02, 11.75, 0.55, fill=RGBColor(0xF4, 0xF8, 0xFF), border=RGBColor(0xD9, 0xE6, 0xFB), radius=0.1)
    text(s, 1.02, 6.14, 11.3, 0.3, "底线要求：涉密不上网、上网不涉密；上线前修改默认密码，并按内网要求配置 HTTPS。",
         size=10.5, color=RGBColor(0x2C, 0x5A, 0xA8), bold=True)
    footer(s, 15)

    # ---------------- 14 下一步 ----------------
    s = new_slide(prs)
    header(s, "ROADMAP", "下一步计划：试点先行，逐步铺开")
    phases = [
        ("近期 · 1 个月", "打基础", ["选定试点楼层，打印并张贴房间二维码", "导入在用物资台账，配置故障类型与设备", "完成受理员、工程师培训与账号发放"], BLUE),
        ("中期 · 3 个月", "全覆盖", ["推广至全部办公区域，替换纸质报障", "配置 SMTP，启用邮件派单与超时提醒", "建立值班表，启用大屏与超时考核"], RGBColor(0x3F, 0x7D, 0xF4)),
        ("远期 · 6 个月+", "深运营", ["工单量、响应时长、耗材成本报表", "物资盘点、报废与领料单管理", "短信/企业微信通知、知识库与移动端深化"], RGBColor(0x7F, 0xA8, 0xFF)),
    ]
    for i, (phase, tag, items, color) in enumerate(phases):
        x = 0.8 + i * 4.02
        rect(s, x, 1.85, 3.8, 4.55, fill=WHITE, border=LINE, radius=0.08, shadow=True)
        rect(s, x, 1.85, 3.8, 0.62, fill=color, radius=0.08)
        text(s, x + 0.25, 1.98, 3.2, 0.3, phase, size=12.5, color=WHITE, bold=True)
        text(s, x + 0.25, 2.75, 3.2, 0.4, tag, size=20, color=INK, bold=True)
        yy = 3.42
        for item in items:
            circle(s, x + 0.27, yy + 0.08, 0.14, color)
            text(s, x + 0.55, yy, 3.0, 0.75, item, size=10.5, color=INK_2, line=1.35)
            yy += 0.92
    footer(s, 16)

    # ---------------- 15 结束 ----------------
    s = new_slide(prs, NAVY)
    circle(s, 10.4, -1.2, 4.2, RGBColor(0x17, 0x2E, 0x55))
    rect(s, 0.9, 0.78, 0.52, 0.52, fill=BLUE, radius=0.22)
    text(s, 0.9, 0.88, 0.52, 0.3, "运", size=16, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    text(s, 0.92, 2.5, 9.0, 0.9, "谢谢，请指正", size=44, color=WHITE, bold=True)
    line(s, 0.95, 3.55, 1.15, color=BLUE_SOFT, h=0.05)
    text(s, 0.95, 3.85, 9.5, 0.35, "信息化运维管理系统  ·  信息中心", size=14, color=RGBColor(0x9D, 0xC0, 0xFF))
    text(s, 0.95, 4.3, 9.5, 0.3, "后续将持续优化功能、沉淀数据，让运维保障更高效、更透明。", size=11,
         color=RGBColor(0x8F, 0xA6, 0xC8))

    # 讲师备注
    speech = [
        "开场：本次汇报介绍信息化运维管理系统的建设背景、方案、核心功能与下一步计划。演示环境地址 http://127.0.0.1:8008。",
        "提纲：重点讲清四件事——派单管理、全过程记录、物资领用和设备管理；最后看成效与计划。",
        "痛点：报障、地点、进度、物资、数据五个环节，核心是过程不可见、责任难追溯。",
        "思路：不改变组织分工，把入口做成二维码，把过程装进系统，用最轻的方式沉淀数据。",
        "流程：扫码报障、受理派单、上门处理、物资领用、签字确认五步闭环，分支场景都已实现。",
        "架构：前端 Vue、后端 FastAPI + SQLite，单机部署即可，手机连内网扫码使用，数据留在本地。",
        "报障端：地点自动带入、立即上门或自选时间点、现场照片、保密提醒、手机号后四位查单、手写签名。",
        "派单管理：受理时可指派，受理员可改派，工程师转派需对方接收，所有变更自动写日志并发邮件。",
        "记录与留痕：工单详情一屏看到时间线、故障原因、处理说明、照片、领用物资、签名与评价。",
        "物资领用：处理时登记物资即扣库存，流水关联工单与处理人；未使用物资可跳过，不产生出库。",
        "设备管理：资产位置、机柜、上架时间、网络、管理地址与账号密码统一台账，支持 Excel/CSV 导入，密码加密仅管理员可看。",
        "大屏与提醒：邮件、语音播报、超时预警三件套，让新报障第一时间被看见。",
        "权限与值班：多角色取并集，工程师值班期间临时获得受理权限，整周排班加临时调班。",
        "运行情况：演示数据覆盖 9 类故障、6 种状态、8 台设备、13 种物资，数据均可从页面验证。",
        "安全合规：非涉密定位、匿名身份只存哈希、密码加盐、设备密码加密、操作全程留痕。",
        "计划：先试点再推广，逐步启用邮件、值班、大屏与报表，持续沉淀运维数据。",
        "结束：请领导和同事批评指正。",
    ]
    for i, content in enumerate(speech):
        if i < len(prs.slides):
            prs.slides[i].notes_slide.notes_text_frame.text = content

    prs.save(OUT)
    print("saved", OUT, "slides:", len(prs.slides))


if __name__ == "__main__":
    build()
