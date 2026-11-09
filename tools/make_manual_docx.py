"""生成《信息化运维管理系统 使用手册》DOCX（分角色操作指南）。"""
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image

BASE = Path(__file__).resolve().parent.parent
SHOTS = BASE / "docs" / "screenshots"
ASSETS = BASE / "build" / "ppt-assets"
OUT = BASE / "信息化运维管理系统-使用手册.docx"

FONT = "PingFang SC"
BLUE = RGBColor(0x2F, 0x6F, 0xEB)
NAVY = RGBColor(0x17, 0x32, 0x5C)
INK = RGBColor(0x1F, 0x29, 0x37)
INK_2 = RGBColor(0x4B, 0x55, 0x63)
GRAY = RGBColor(0x6B, 0x7A, 0x90)
LINE = "D9E0EC"

CONTENT_W = 16.6  # cm


def set_run(run, size=10.5, color=INK, bold=False, name=FONT):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), name)
    rfonts.set(qn("w:hAnsi"), name)
    rfonts.set(qn("w:eastAsia"), name)


def body(text, size=10.5, color=INK, bold=False, after=4, before=0, indent=0, line=1.6,
         align=WD_ALIGN_PARAGRAPH.JUSTIFY):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.line_spacing = line
    p.paragraph_format.left_indent = Cm(indent)
    p.alignment = align
    r = p.add_run(text)
    set_run(r, size=size, color=color, bold=bold)
    return p


def bullet(text, size=10.5, color=INK_2):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.75)
    p.paragraph_format.first_line_indent = Cm(-0.35)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.55
    r = p.add_run("·  ")
    set_run(r, size=size, color=BLUE, bold=True)
    r2 = p.add_run(text)
    set_run(r2, size=size, color=color)
    return p


def chapter(num, title):
    p = doc.add_paragraph(style="Heading 1")
    p.paragraph_format.page_break_before = True
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(12)
    r = p.add_run(f"第 {num} 章   {title}")
    set_run(r, size=18, color=NAVY, bold=True)
    return p


def section_title(text):
    p = doc.add_paragraph(style="Heading 2")
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    set_run(r, size=14, color=BLUE, bold=True)
    return p


def sub_title(text):
    p = doc.add_paragraph(style="Heading 3")
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    set_run(r, size=11.5, color=INK, bold=True)
    return p


def shade(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def cell_margins(table, top=60, bottom=60, left=100, right=100):
    tblPr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for side, val in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tblPr.append(mar)


def table_borders(table, color=LINE, size=4):
    tblPr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(size))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    tblPr.append(borders)


def no_borders(table):
    tblPr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "nil")
        borders.append(el)
    tblPr.append(borders)


def header_row(table):
    tr = table.rows[0]._tr
    trPr = tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def no_split(table):
    for row in table.rows:
        trPr = row._tr.get_or_add_trPr()
        el = OxmlElement("w:cantSplit")
        el.set(qn("w:val"), "true")
        trPr.append(el)


def set_col_width(table, widths_cm):
    table.autofit = False
    for row in table.rows:
        for idx, width in enumerate(widths_cm):
            row.cells[idx].width = Cm(width)


def table(doc, headers, rows, widths, font_size=9.5, header_fill="2F6FEB",
          first_col_bold=False, align_center=False):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_borders(t)
    cell_margins(t)
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        cell = hdr[i]
        shade(cell, header_fill)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(h)
        set_run(r, size=font_size + 0.5, color=RGBColor(0xFF, 0xFF, 0xFF), bold=True)
    for row_data in rows:
        cells = t.add_row().cells
        for i, value in enumerate(row_data):
            cell = cells[i]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.35
            if align_center or i == 0 and first_col_bold:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i == 0 else WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(str(value))
            set_run(r, size=font_size, color=INK, bold=(first_col_bold and i == 0))
    set_col_width(t, widths)
    header_row(t)
    no_split(t)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def steps_table(rows):
    table(doc, ["步骤", "操作", "说明"], rows, [1.5, 6.3, 8.6], font_size=9.5)


def note(text, color_fill="F2F7FF", color_text=RGBColor(0x2C, 0x5A, 0xA8)):
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    no_borders(t)
    cell = t.rows[0].cells[0]
    shade(cell, color_fill)
    cell.width = Cm(CONTENT_W)
    cell_margins(t, 100, 100, 160, 160)
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.5
    r = p.add_run(text)
    set_run(r, size=9.5, color=color_text, bold=False)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def figure(path, caption, width_cm=15.5, max_h=16.5):
    iw, ih = Image.open(path).size
    ratio = ih / iw
    width = min(width_cm, max_h / ratio)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Cm(width))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(10)
    r = cap.add_run(caption)
    set_run(r, size=9, color=GRAY)


def add_field(paragraph, instr, size=9):
    run = paragraph.add_run()
    set_run(run, size=size, color=GRAY)
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr_el = OxmlElement("w:instrText")
    instr_el.set(qn("xml:space"), "preserve")
    instr_el.text = instr
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    text_el = OxmlElement("w:t")
    text_el.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr_el)
    run._r.append(sep)
    run._r.append(text_el)
    run._r.append(end)


def header_footer():
    section = doc.sections[0]
    section.different_first_page_header_footer = True
    hp = section.header.paragraphs[0]
    hp.style = doc.styles["Normal"]
    hp.paragraph_format.tab_stops.clear_all()
    hp.paragraph_format.tab_stops.add_tab_stop(Cm(CONTENT_W), WD_TAB_ALIGNMENT.RIGHT)
    r = hp.add_run("信息化运维管理系统  ·  使用手册")
    set_run(r, size=9, color=GRAY)
    r2 = hp.add_run("\tV1.0")
    set_run(r2, size=9, color=GRAY)
    pPr = hp._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "4")
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), LINE)
    pBdr.append(bottom)
    pPr.append(pBdr)

    fp = section.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = fp.add_run("第 ")
    set_run(r, size=9, color=GRAY)
    add_field(fp, "PAGE")
    r = fp.add_run(" 页  /  共 ")
    set_run(r, size=9, color=GRAY)
    add_field(fp, "NUMPAGES")
    r = fp.add_run(" 页")
    set_run(r, size=9, color=GRAY)


def cover():
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    no_borders(t)
    cell = t.rows[0].cells[0]
    cell.width = Cm(CONTENT_W)
    shade(cell, "17325C")
    cell_margins(t, 500, 500, 500, 500)
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(18)
    r = p.add_run("信息中心  ·  内部资料")
    set_run(r, size=10, color=RGBColor(0x9D, 0xC0, 0xFF))

    p2 = cell.add_paragraph()
    p2.paragraph_format.space_after = Pt(8)
    r = p2.add_run("信息化运维管理系统")
    set_run(r, size=30, color=RGBColor(0xFF, 0xFF, 0xFF), bold=True)

    p3 = cell.add_paragraph()
    p3.paragraph_format.space_after = Pt(0)
    r = p3.add_run("使 用 手 册")
    set_run(r, size=22, color=RGBColor(0xFF, 0xFF, 0xFF), bold=True)

    body("", after=30)
    body("分角色操作指南", size=16, color=BLUE, bold=True, after=6, line=1.3)
    body("报障人  ·  受理员  ·  运维工程师  ·  系统管理员", size=11, color=GRAY, after=60, line=1.5)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(40)
    r = p.add_run("版本 V1.0      ·      编制日期 2026 年 11 月      ·      适用系统 v1.0")
    set_run(r, size=10, color=GRAY)


def info_page():
    p = doc.add_paragraph(style="Heading 1")
    p.paragraph_format.page_break_before = True
    r = p.add_run("文档说明")
    set_run(r, size=18, color=NAVY, bold=True)

    body("本手册面向系统的四类使用者：普通报障人、报障受理员、运维工程师、系统管理员。"
         "每章按角色说明登录方式、典型任务和操作步骤，并配以系统实际界面截图。"
         "建议首次使用前通读第 1 章，再按角色查阅对应章节。", after=10)

    body("一、阅读对象", size=11, color=INK, bold=True, after=4)
    table(doc, ["角色", "建议阅读章节"], [
        ("普通用户（报障人）", "第 1 章、第 2 章"),
        ("报障受理员", "第 1 章、第 3 章、第 6 章"),
        ("运维工程师", "第 1 章、第 4 章、第 6 章"),
        ("系统管理员", "第 1 章、第 5 章、第 6 章、第 7 章"),
    ], [6.5, 10.1], font_size=9.5)

    body("二、修订记录", size=11, color=INK, bold=True, after=4)
    table(doc, ["版本", "日期", "修订内容", "编制"], [
        ("V1.0", "2026-11", "首次发布：报障、派单、记录、物资、设备、权限与值班", "信息中心"),
    ], [2.2, 3.0, 8.4, 3.0], font_size=9.5)

    body("三、约定", size=11, color=INK, bold=True, after=4)
    bullet("界面按钮、菜单以「」标注，如「工单管理」；页面字段以加粗或引号说明。")
    bullet("系统地址示例为 http://服务器地址:8008，实际以单位部署地址为准。")
    bullet("截图中的姓名、电话、IP、账号均为演示数据，不代表真实信息。")

    toc_page()


def toc_page():
    p = doc.add_paragraph(style="Heading 1")
    p.paragraph_format.page_break_before = True
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(10)
    r = p.add_run("目录")
    set_run(r, size=18, color=NAVY, bold=True)
    table(doc, ["章节", "主要内容"], [
        ("第 1 章  系统概览", "系统能力、角色权限、访问方式、工单状态"),
        ("第 2 章  普通用户（报障人）", "扫码报障、查询进度、确认与手写签字"),
        ("第 3 章  报障受理员", "受理派单、电话代录、改派、大屏、值班、物资与账号"),
        ("第 4 章  运维工程师", "接单处理、提交结果、物资领用、转派、值班受理"),
        ("第 5 章  系统管理员", "房间二维码、账号权限、邮件、设备台账、备份"),
        ("第 6 章  值班与交接", "排班规则、今日值班、交接清单"),
        ("第 7 章  常见问题", "扫码、登录、邮件、库存、签字等常见问题"),
        ("附录", "工单字段说明、角色任务索引"),
    ], [6.2, 10.4], font_size=9.5)


def build():
    global doc
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.2)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)
    section.header_distance = Cm(1.2)
    section.footer_distance = Cm(1.2)

    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = INK
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    normal.paragraph_format.line_spacing = 1.6

    for style_name in ("Heading 1", "Heading 2", "Heading 3"):
        st = doc.styles[style_name]
        st.font.name = FONT
        st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)

    header_footer()
    cover()
    info_page()

    # ================= 第 1 章 =================
    chapter(1, "系统概览")
    body("信息化运维管理系统用于单位内部非涉密设备的报障、派单、上门处理、物资领用和设备台账管理。"
         "每个房间张贴一张二维码，扫码即可报障，地点自动带入；运维人员在后台完成受理、指派、处理与确认，"
         "全过程自动记录时间、处理人、物资、照片与签名。")

    section_title("1.1 功能模块")
    table(doc, ["模块", "主要用途"], [
        ("扫码报障", "手机扫码填写故障设备、类型、地点、期望上门时间，可传现场照片"),
        ("派单管理", "受理、指派、改派、转派，处理人自动收到邮件提醒"),
        ("过程记录", "时间线、故障原因、处理说明、照片、领用物资、签字评价"),
        ("物资管理", "分类自动编号、入库出库、库存预警、工单领用自动扣减、CSV 导入"),
        ("设备台账", "资产位置、机柜、上架时间、网络、管理地址与账号密码，支持 Excel/CSV 导入"),
        ("报障大屏", "待受理实时列表、语音播报、超时预警、今日值班"),
        ("值班排班", "整周固定多人值班，支持某天某时段临时调班"),
        ("系统设置", "故障类型与设备字典、物资分类、邮件通知、账号与二维码地址"),
    ], [4.2, 12.4], font_size=9.5)

    section_title("1.2 角色与权限")
    table(doc, ["角色", "登录方式", "主要权限"], [
        ("普通用户（报障人）", "无需账号，扫房间二维码", "提交报障、查看本人工单、确认并手写签字"),
        ("报障受理员", "账号登录", "受理派单、电话代录、改派、大屏、值班、物资与分类、字典、工程师账号"),
        ("运维工程师", "账号登录", "处理指派给自己的工单、登记领用物资、发起转派"),
        ("值班受理", "工程师值班期间自动获得", "值班时段内可受理、派单、电话代录、改派"),
        ("系统管理员", "账号登录", "全部功能，含邮件配置、全部账号、房间二维码、设备台账、备份"),
    ], [4.0, 4.8, 7.8], font_size=9.5)

    note("账号由系统管理员创建和分配。登录页不再展示默认账号；初始账号与密码见项目 README 文档，首次登录后请立即修改。")

    section_title("1.3 访问方式")
    bullet("电脑端：浏览器访问 http://服务器地址:8008，建议使用 Chrome、Edge 或 Safari 最新版本。")
    bullet("手机端：扫描房间门旁的二维码，直接进入该房间的报障页，无需安装 App。")
    bullet("运维人员：访问 /login 登录后台；普通报障人不需要登录。")
    bullet("大屏：访问 /board，用于受理中心电视或显示器展示。")

    section_title("1.4 工单状态说明")
    table(doc, ["状态", "含义", "下一步操作"], [
        ("待受理", "报障已提交，尚未受理", "受理员受理并指派处理人"),
        ("已受理", "已受理，等待上门", "处理人开始处理"),
        ("处理中", "已上门，正在处理", "处理人提交处理结果"),
        ("待确认", "处理完成，等待报障人确认", "报障人评分、手写签字"),
        ("已完成", "确认归档", "无需操作，可在工单列表查询"),
        ("已取消", "重复报障、用户撤销或无法联系", "无需操作"),
    ], [2.6, 7.2, 6.8], font_size=9.5)

    # ================= 第 2 章 =================
    chapter(2, "普通用户（报障人）")
    body("普通用户不需要注册账号。用手机扫描房间门旁的二维码即可报障；提交后凭同一手机可查看进度，"
         "维修完成后需要在线确认并手写签名。")

    section_title("2.1 扫码报障")
    steps_table([
        ("1", "扫描房间二维码", "打开报障页，页面顶部自动显示该房间位置（楼栋、楼层、房间号）"),
        ("2", "确认报障地点", "默认是扫码所在房间；如果您在其他地点办公，可在下拉框切换"),
        ("3", "填写故障设备", "可手动输入，也可点下方常用设备快捷标签"),
        ("4", "选择故障类型", "从管理员配置的类型中选择，如网络、打印、投影等"),
        ("5", "选择期待上门时间", "默认「立即上门」；选「指定时间」后日期默认当天，可直接选时间，也可改日期"),
        ("6", "填写故障描述", "简单描述故障现象，便于运维人员提前判断"),
        ("7", "上传现场照片（选填）", "最多 3 张，手机可直接拍照；请勿拍摄涉密内容"),
        ("8", "填写联系人与电话", "请填写真实姓名和可接通的电话"),
        ("9", "提交报障", "提交成功后显示报障单号，请留意来电"),
    ])
    figure(ASSETS / "report_phone.png", "图 2-1  手机扫码报障页面", width_cm=7.2)
    note("页面顶部固定提示「非涉密系统，严禁上传涉密信息」。请勿填写或上传国家秘密、工作秘密及内部敏感信息。")

    section_title("2.2 查看报障进度")
    body("同一部手机提交的报障会自动关联。打开报障页右上角「我的报障」，或直接访问 /mine，即可查看历史工单。"
         "若更换手机或清理了浏览器缓存，输入报障时填写的手机号后四位即可查回该号码的全部工单。")
    figure(ASSETS / "mine-crop.png", "图 2-2  「我的报障」列表", width_cm=7.0)
    steps_table([
        ("1", "进入「我的报障」", "可通过报障页右上角或系统首页入口进入"),
        ("2", "输入手机号后四位", "首次查询需要输入；查询成功后本机会记住"),
        ("3", "查看工单列表", "显示状态、地点、设备、期望上门时间与提交时间"),
        ("4", "打开工单详情", "查看处理人、处理进度、领用物资与签字记录"),
    ])

    section_title("2.3 确认维修完成与签字")
    body("当工单状态变为「待确认」，说明运维人员已提交处理结果。请核对处理说明与领用物资，"
         "确认无误后完成评分并手写签名。")
    figure(ASSETS / "signature-pad.png", "图 2-3  确认与手写签名", width_cm=6.5)
    steps_table([
        ("1", "打开「我的报障」", "找到状态为「待确认」的工单"),
        ("2", "点击「确认完成」", "弹出确认窗口，显示满意度评分与签名框"),
        ("3", "选择满意度", "1—5 星，可填写补充说明"),
        ("4", "手写签名", "在签名框内用手指书写姓名；可点「清除重签」"),
        ("5", "提交", "确认后工单归档为「已完成」，签名随工单保存"),
    ])

    section_title("2.4 注意事项")
    bullet("本系统仅用于非涉密设备报障，严禁上传涉密文件、涉密屏幕或涉密场所照片。")
    bullet("联系电话务必填写准确，运维人员上门前会电话联系。")
    bullet("报障地点默认是扫码房间；若设备不在该房间，请在提交前切换地点。")
    bullet("「待受理」状态下可撤销报障；已受理后如需取消，请联系运维人员。")
    bullet("维修完成后请及时确认，未确认的工单会一直停留在「待确认」。")

    # ================= 第 3 章 =================
    chapter(3, "报障受理员")
    body("受理员负责接收报障、指派处理人、电话代录、改派、关闭工单，并可使用大屏、维护值班、物资与工程师账号。")

    section_title("3.1 登录与工作台")
    body("访问 /login，输入管理员分配的账号密码。登录后进入「工作台」，可查看待受理、处理中、待确认数量，"
         "以及今日新增、近 7 天完成、平均处理时长与服务评分。")
    figure(SHOTS / "dashboard.png", "图 3-1  受理员工作台")
    bullet("右上角「电话报障」用于代录电话报障；「生成二维码」跳转房间管理。")
    bullet("左侧菜单：工单管理、物资管理、设备台账、房间与二维码、报障大屏、值班排班、系统设置。")
    bullet("工程师值班期间会自动出现「值班受理中」标签，具备受理权限。")

    section_title("3.2 受理与派单")
    steps_table([
        ("1", "进入「工单管理」", "默认显示全部工单，点「待受理」标签筛选"),
        ("2", "选择工单", "核对地点、设备、故障类型、期望上门时间"),
        ("3", "点击「受理」或「详情 → 受理并派单」", "受理弹窗中选择上门/处理人员，也可暂不指派"),
        ("4", "确认受理", "工单变为「已受理」，处理人收到邮件提醒（需配置 SMTP）"),
        ("5", "如需调整", "在工单详情点「改派」，选择新的处理人，立即生效并重新通知"),
    ])
    figure(SHOTS / "tickets.png", "图 3-2  工单管理与受理派单")

    section_title("3.3 电话报障代录")
    body("用户未扫码、直接打电话报障时，由受理员代录。")
    steps_table([
        ("1", "工作台右上角点击「电话报障」", "打开代录表单"),
        ("2", "填写报障地点", "可从房间列表选择，也可直接输入地点"),
        ("3", "填写设备、故障类型、描述", "记录来电人描述的现象"),
        ("4", "填写联系人与电话", "来电人姓名与可回拨号码"),
        ("5", "选择期待上门时间", "立即上门或指定时间点"),
        ("6", "指派处理人（可选）", "选择后提交即完成受理并派单，同时发邮件"),
        ("7", "提交", "生成工单，来源标记为「电话代录」"),
    ])
    figure(SHOTS / "manual-ticket.png", "图 3-3  电话报障代录")

    section_title("3.4 改派、转派与关闭")
    sub_title("改派")
    body("工单详情 →「改派」→ 选择新的处理人 → 确定。改派立即生效，系统记录改派日志并邮件通知新处理人。", after=3)
    sub_title("转派")
    body("工程师可在工单详情发起「转派他人」，选择同事并填写原因。工单进入「待接收」状态，"
         "由接收人在工作台「待接收转派」中确认；确认前原处理人继续负责。受理员也可通过「改派」直接调整，无需对方确认。", after=3)
    sub_title("关闭工单")
    body("对于重复报障、用户撤销、无法联系等情况，可在工单详情点「关闭工单」并填写原因，工单状态变为「已取消」。", after=3)

    section_title("3.5 报障大屏与语音提醒")
    body("访问 /board，或从左侧菜单进入「报障大屏」。大屏每 8 秒刷新待受理工单，新报障自动弹出横幅、"
         "播放提示音并语音播报地点、设备与故障类型。")
    steps_table([
        ("1", "打开大屏并全屏", "建议使用受理中心电视或副屏"),
        ("2", "点击「开启语音提醒」", "浏览器限制自动播放，首次需手动开启，设置会记住"),
        ("3", "查看超时预警", "待受理超 15 分钟、上门超 60 分钟、处理超 4 小时会标红"),
        ("4", "查看今日值班", "顶部显示本周固定值班人员与临时替班时段"),
    ])
    figure(SHOTS / "board.png", "图 3-4  报障实时大屏")

    section_title("3.6 值班排班")
    body("值班按「整周固定 + 临时调班」管理，不再区分白班夜班。整周值班至少选择 2 人；"
         "临时调班用于某天某个时间段换人，例如「11-06 14:00-17:00 王五替班」。")
    steps_table([
        ("1", "进入「值班排班」", "默认显示本周"),
        ("2", "选择值班人员", "多选 2 人及以上，填写备注后保存"),
        ("3", "新增临时调班", "选择日期、起止时间、替班人员与原因"),
        ("4", "查看今日值班", "页面顶部与大屏同步显示当天的固定人员与临时人员"),
    ])
    figure(SHOTS / "duty.png", "图 3-5  值班排班（整周 + 临时调班）")

    section_title("3.7 物资、分类与设备台账")
    body("受理员可维护物资台账、分类与设备台账；设备管理密码仅管理员可查看明文，受理员只能看到「已设置」。")
    bullet("物资管理：新增物资、入库、出库、查看流水；新增时按分类前缀自动生成编号。")
    bullet("批量导入：下载 CSV 模板，填写后导入；分类必须是系统已有分类。")
    bullet("设备台账：新增/编辑设备，记录位置、上架时间、网络与管理地址；导入支持 Excel/CSV。")
    figure(SHOTS / "materials.png", "图 3-6  物资管理与领用流水")

    section_title("3.8 工程师账号管理")
    body("进入「系统设置 → 运维账号」，可新增工程师、编辑姓名/电话/邮箱、启停账号、重置密码。"
         "受理员只能维护「纯工程师」账号，不能新增或修改管理员、受理员账号。")
    figure(SHOTS / "dispatcher-accounts.png", "图 3-7  受理员维护工程师账号")

    # ================= 第 4 章 =================
    chapter(4, "运维工程师")
    body("工程师负责处理指派给自己的工单：开始处理、记录故障原因与处理过程、登记领用物资、提交结果；"
         "必要时可转派给其他同事。")

    section_title("4.1 查看我的工单")
    steps_table([
        ("1", "登录后台", "账号由管理员或受理员分配"),
        ("2", "进入「工单管理」", "勾选「只看我的」或按状态筛选"),
        ("3", "打开工单详情", "查看地点、联系人电话、期望上门时间、故障描述与照片"),
        ("4", "查看首页提醒", "工作台顶部会显示指派给你的工单与待接收转派"),
    ])
    figure(SHOTS / "duty-engineer.png", "图 4-1  工程师工作台（值班中示例）")

    section_title("4.2 开始处理")
    body("到达现场后，在工单详情点击「开始处理」，工单由「已受理」变为「处理中」，系统记录开始时间。")

    section_title("4.3 提交处理结果")
    steps_table([
        ("1", "点击「提交处理结果」", "打开处理结果弹窗"),
        ("2", "填写故障原因", "如「电源适配器损坏」「网线水晶头松动」"),
        ("3", "填写处理说明（必填）", "说明处理过程与结果，提交后由报障人确认"),
        ("4", "登记领用物资", "点「添加物资」，选择物资与数量；提交后自动扣库存并生成出库流水"),
        ("5", "未使用物资", "勾选「本次维修未使用物资」，不产生出库记录"),
        ("6", "提交", "工单变为「待确认」，等待报障人签字确认"),
    ])
    figure(ASSETS / "ticket-record.png", "图 4-2  处理结果与签字记录示例", width_cm=9.0)

    section_title("4.4 转派给其他同事")
    body("现场情况需要其他专业同事处理时，可在工单详情点「转派他人」，选择接收人并填写转派说明。"
         "转派需对方在工作台「待接收转派」中确认；确认前仍由你继续负责，对方拒绝则保持原处理人不变。")

    section_title("4.5 值班期间临时受理")
    body("当您在本周值班名单内，或处于当天临时调班时间段内，系统会自动授予「值班受理」权限："
         "可受理、派单、改派、电话代录，工作台出现「电话报障」按钮，顶部显示「值班受理中」。"
         "值班结束后权限自动收回。该权限不包含账号管理、物资分类与系统设置。")

    section_title("4.6 注意事项")
    bullet("到场后及时点「开始处理」，完成后及时提交结果，避免工单超时。")
    bullet("领用物资数量要准确；未使用物资请勾选跳过，避免库存误扣。")
    bullet("处理说明尽量写清原因与结果，便于报障人确认与后续统计。")
    bullet("现场照片请勿拍摄涉密内容。")

    # ================= 第 5 章 =================
    chapter(5, "系统管理员")
    body("管理员负责系统基础配置：房间二维码、账号权限、邮件通知、设备台账、物资分类与数据备份。")

    section_title("5.1 房间与二维码")
    figure(SHOTS / "rooms.png", "图 5-1  房间与二维码管理")
    steps_table([
        ("1", "进入「房间与二维码」", "查看全部房间及报障数量"),
        ("2", "新增房间", "填写楼栋、楼层、房间号、名称与备注"),
        ("3", "打印标签", "勾选房间后点「打印选中标签」，或「打印全部标签」"),
        ("4", "打印或另存 PDF", "A4 纸 3 列排版，剪开后贴到对应房间门旁"),
        ("5", "重新生成二维码", "旧码立即作废，需要重新打印；仅在二维码泄露时使用"),
    ])

    section_title("5.2 二维码访问地址")
    body("二维码中编码的是访问地址。默认自动使用本机局域网 IP；部署到服务器或使用域名后，"
         "请到「系统设置 → 二维码地址」填写手机可访问的正式地址，例如 https://ops.example.com，"
         "保存后重新打印二维码。若通过环境变量 OPS_PUBLIC_BASE_URL 配置，页面留空时自动使用该地址。")
    figure(SHOTS / "print-labels.png", "图 5-2  A4 二维码标签打印效果")

    section_title("5.3 账号与多角色权限")
    body("「系统设置 → 运维账号」可新增账号、编辑邮箱、启停、重置密码。角色支持多选，"
         "例如同一账号同时勾选「受理员 + 运维工程师」，权限自动合并。管理员不能移除自己的管理员角色，也不能停用自己。")
    figure(SHOTS / "multi-role-accounts.png", "图 5-3  多角色账号管理")

    section_title("5.4 邮件通知配置")
    body("派单、改派、转派时系统会给处理人发送邮件。配置路径：「系统设置 → 邮件通知」。")
    steps_table([
        ("1", "填写 SMTP 服务器与端口", "如 smtp.qq.com / 587；企业邮箱以信息中心提供为准"),
        ("2", "选择加密方式", "STARTTLS（587）、SSL（465）或不加密（内网 25）"),
        ("3", "填写账号与授权码", "授权码不是登录密码，请在邮箱后台单独生成"),
        ("4", "设置发件人", "发件人邮箱与名称，留空则使用 SMTP 账号"),
        ("5", "启用并保存", "打开「启用派单邮件提醒」"),
        ("6", "发送测试邮件", "填写接收邮箱，确认收到后即配置成功"),
    ])
    figure(SHOTS / "mail-config.png", "图 5-4  SMTP 邮件配置")

    section_title("5.5 设备台账")
    body("设备台账记录资产位置、上架时间、网络信息、管理地址与账号密码，支持按类型、状态、房间筛选。")
    bullet("字段：资产编号、设备名称、类型、品牌型号、序列号、房间、机柜位置、上架时间、状态、网络信息、管理地址、管理账号/密码、端口、责任人、供应商、保修到期、备注。")
    bullet("资产编号留空自动生成 ZC-0001 形式；管理密码加密存储，列表与详情默认脱敏，仅管理员可点「显示密码」查看。")
    bullet("「导入」支持 .xlsx 与 .csv，模板可在导入弹窗中下载；导入逐行校验并提示错误行号。")
    figure(SHOTS / "assets.png", "图 5-5  设备台账")

    section_title("5.6 物资分类与批量导入")
    body("「系统设置 → 物资分类」维护分类名称与编号前缀（如线材 XC、设备 SB、其它 QT）。"
         "新增物资时按前缀自动生成编号。分类下已有物资时不能删除。"
         "「物资管理 → 批量导入」可下载 CSV 模板，填写名称、分类、规格、单位、库存等信息后导入。")

    section_title("5.7 数据备份与恢复")
    body("系统数据保存在 backend/data 目录：ops.db 为 SQLite 数据库，uploads 为报障照片。"
         "Docker/Dokploy 部署时该目录挂载为数据卷，备份数据卷即可。")
    steps_table([
        ("1", "停止服务", "保证 SQLite WAL 文件一致"),
        ("2", "复制数据目录或卷", "本地部署复制 backend/data；容器部署备份 /app/backend/data 卷"),
        ("3", "保存到备份介质", "按日期命名，保留多份"),
        ("4", "恢复", "停止服务后覆盖回原目录/卷，再启动，数据自动完成兼容迁移"),
    ])
    note("设备台账密码使用 Fernet 加密，密钥存放在同一个数据库中；丢失数据库将无法解密设备密码，请务必定期备份。")

    section_title("5.8 安全建议")
    bullet("首次上线立即修改默认密码，停用不需要的账号。")
    bullet("对外访问使用 HTTPS，不要把 8008 端口直接暴露到公网。")
    bullet("非涉密系统，严禁录入涉密信息与涉密照片。")
    bullet("定期检查超时工单、库存预警与设备保修到期。")

    # ================= 第 6 章 =================
    chapter(6, "值班与交接")
    section_title("6.1 排班规则")
    bullet("整周固定值班：每周至少 2 人，可多人；保存后本周生效。")
    bullet("临时调班：针对某一天某个时间段临时换人，需填写日期、起止时间、替班人员与原因。")
    bullet("值班中的工程师自动获得受理权限，值班结束后自动收回。")
    bullet("大屏与工作台会显示今日值班人员（含临时替班时间段）。")

    section_title("6.2 每日交接清单")
    table(doc, ["检查项", "操作"], [
        ("待受理工单", "是否有超时未受理，及时指派"),
        ("处理中/已受理", "是否有超时未上门，联系处理人"),
        ("待确认工单", "提醒报障人确认签字"),
        ("待接收转派", "提醒接收人尽快确认或拒绝"),
        ("库存预警", "低于预警线的物资及时补货"),
        ("设备异常", "核对设备台账与现场是否一致"),
    ], [5.0, 11.6], font_size=9.5)

    section_title("6.3 交接注意事项")
    bullet("交接时说明未结工单、待确认工单与超时工单。")
    bullet("临时调班请在系统中登记，避免大屏显示与实际值班人员不一致。")
    bullet("值班期间发生的电话报障，请用「电话报障」代录，不要只在聊天工具里转达。")

    # ================= 第 7 章 =================
    chapter(7, "常见问题")
    table(doc, ["问题", "处理方法"], [
        ("手机扫码打不开页面", "确认手机与服务器在同一网络；二维码地址是否为手机可访问的域名/IP；服务器防火墙是否放行"),
        ("忘记登录密码", "联系系统管理员在「系统设置 → 运维账号」中重置密码"),
        ("收不到派单邮件", "检查处理人是否填写邮箱；在邮件配置中发送测试邮件；确认服务器可访问 SMTP 端口"),
        ("二维码扫出来是旧地址", "到「系统设置 → 二维码地址」修改后重新打印二维码"),
        ("提交报障提示频繁", "同一身份 10 分钟内最多提交 5 单，稍后再试"),
        ("物资领用提示库存不足", "先入库或调整数量；库存以物资管理页面为准"),
        ("工单无法撤销", "仅「待受理」可撤销；已受理请联系运维人员关闭"),
        ("签字无法提交", "需先在签名框内手写；图片过大可点「清除重签」后重新签名"),
        ("转派对方没收到", "对方在工作台「待接收转派」查看；确认是否登录了正确账号"),
        ("时间显示不对", "容器部署需设置 TZ=Asia/Shanghai；本地部署检查系统时区"),
        ("如何迁移/备份", "备份 backend/data 目录或 Docker 数据卷，恢复后启动会自动迁移表结构"),
    ], [5.2, 11.4], font_size=9.5)

    # ================= 附录 =================
    p = doc.add_paragraph(style="Heading 1")
    p.paragraph_format.page_break_before = True
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(12)
    r = p.add_run("附录")
    set_run(r, size=18, color=NAVY, bold=True)

    section_title("附录 A  工单字段说明")
    table(doc, ["字段", "说明"], [
        ("单号", "系统自动生成，格式 WO+日期+序号"),
        ("报障地点", "房间位置，扫码自动带入，可手动切换"),
        ("故障设备/类型", "报障人选填或从配置字典选择"),
        ("期望上门时间", "立即上门或指定日期时间点"),
        ("故障描述/照片", "报障人填写与上传，最多 3 张照片"),
        ("处理人", "受理时指派，可改派或转派"),
        ("故障原因/处理说明", "处理人提交结果时填写"),
        ("领用物资", "处理人登记的物资与数量，自动扣库存"),
        ("签字与评价", "报障人确认时的手写签名、评分与评价"),
    ], [4.6, 12.0], font_size=9.5)

    section_title("附录 B  角色任务索引")
    table(doc, ["我想……", "去哪里操作", "角色"], [
        ("报障", "扫房间二维码", "普通用户"),
        ("查看报障进度", "我的报障 / 手机号后四位查询", "普通用户"),
        ("确认维修并签字", "我的报障 → 待确认 → 确认完成", "普通用户"),
        ("受理并派单", "工单管理 → 待受理 → 受理", "受理员"),
        ("代录电话报障", "工作台 → 电话报障", "受理员/值班受理"),
        ("改派处理人", "工单详情 → 改派", "受理员"),
        ("处理工单", "工单详情 → 开始处理 → 提交处理结果", "工程师"),
        ("转派给同事", "工单详情 → 转派他人", "工程师"),
        ("打印房间二维码", "房间与二维码 → 打印标签", "管理员"),
        ("配置邮件", "系统设置 → 邮件通知", "管理员"),
        ("维护设备台账", "设备台账 → 新增/导入", "管理员/受理员"),
        ("查看大屏", "报障大屏 /board", "受理员/值班受理"),
        ("排班", "值班排班", "管理员/受理员"),
    ], [5.4, 7.6, 3.6], font_size=9.5)

    body("", after=20)
    note("本手册随系统版本更新。如界面与手册不一致，以系统实际页面为准；"
         "功能建议或问题请联系信息中心。")

    # 打开时自动更新页码字段
    settings = doc.settings.element
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    settings.append(update)

    doc.core_properties.title = "信息化运维管理系统 使用手册"
    doc.core_properties.author = "信息中心"
    doc.core_properties.subject = "分角色操作指南"
    doc.save(OUT)
    print("saved", OUT, "paragraphs", len(doc.paragraphs), "images", len(doc.inline_shapes))


if __name__ == "__main__":
    build()
