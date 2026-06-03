"""生成简化版项目信息填写表，供项目经理填写，由 AI 解析为 YAML 配置。"""
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT = "/Users/spellbook/Desktop/Langlobal/AI Lab/Game-Terms-Extraction-Langlobal/docs/项目配置填写表.xlsx"

HEADER_FILL  = PatternFill("solid", fgColor="1F4E79")
SECTION_FILL = PatternFill("solid", fgColor="2E75B6")
INPUT_FILL   = PatternFill("solid", fgColor="FFFDE7")
HINT_FILL    = PatternFill("solid", fgColor="F5F5F5")
WHITE_FILL   = PatternFill("solid", fgColor="FFFFFF")

HEADER_FONT  = Font(bold=True, color="FFFFFF", size=12)
SECTION_FONT = Font(bold=True, color="FFFFFF", size=10)
LABEL_FONT   = Font(bold=True, size=10)
HINT_FONT    = Font(italic=True, color="888888", size=9)
BODY_FONT    = Font(size=10)

BORDER = Border(
    left=Side(style="thin", color="CCCCCC"),
    right=Side(style="thin", color="CCCCCC"),
    top=Side(style="thin", color="CCCCCC"),
    bottom=Side(style="thin", color="CCCCCC"),
)
WRAP   = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)


def apply(cell, fill=None, font=None, align=WRAP, border=BORDER):
    if fill:   cell.fill   = fill
    if font:   cell.font   = font
    if align:  cell.alignment = align
    if border: cell.border = border


def section_header(ws, row, text):
    c = ws.cell(row=row, column=1, value=text)
    apply(c, fill=SECTION_FILL, font=SECTION_FONT, align=CENTER)
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
    ws.row_dimensions[row].height = 24


def question_row(ws, row, label, hint, input_height=40):
    # col1: 题号+问题
    lc = ws.cell(row=row, column=1, value=label)
    apply(lc, fill=WHITE_FILL, font=LABEL_FONT)

    # col2: 提示（灰色小字）
    hc = ws.cell(row=row, column=2, value=hint)
    apply(hc, fill=HINT_FILL, font=HINT_FONT)

    # col3: 填写区（淡黄）
    ic = ws.cell(row=row, column=3, value="")
    apply(ic, fill=INPUT_FILL, font=BODY_FONT)

    ws.row_dimensions[row].height = input_height
    return ic


def main():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "项目信息填写表"

    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 36
    ws.column_dimensions["C"].width = 50

    # ── 总标题 ──────────────────────────────────────────────────────────────
    ws.merge_cells("A1:C1")
    c = ws.cell(row=1, column=1, value="游戏术语抽取 — 项目信息填写表")
    apply(c, fill=HEADER_FILL, font=HEADER_FONT, align=CENTER)
    ws.row_dimensions[1].height = 36

    ws.merge_cells("A2:C2")
    c = ws.cell(row=2, column=1,
                value="🟡 黄色区域请填写  |  灰色为填写提示，不用修改  |  填完后原文件发回即可")
    apply(c, fill=HINT_FILL, font=HINT_FONT, align=CENTER)
    ws.row_dimensions[2].height = 18

    # ── 栏头 ─────────────────────────────────────────────────────────────────
    for col, text in [(1, "问题"), (2, "填写提示"), (3, "⬇ 请在这里填写")]:
        c = ws.cell(row=3, column=col, value=text)
        apply(c, fill=SECTION_FILL, font=SECTION_FONT, align=CENTER)
    ws.row_dimensions[3].height = 22

    row = 4

    # ── 第一部分：基本信息 ──────────────────────────────────────────────────
    section_header(ws, row, "一、基本信息")
    row += 1

    question_row(ws, row,
        "1. 游戏名称",
        "游戏的完整中文名称",
        30)
    row += 1

    question_row(ws, row,
        "2. 游戏风格 / 世界观",
        "例如：古风武侠、西幻奇幻、科幻末日、现代都市……\n一两句话描述游戏背景即可",
        50)
    row += 1

    question_row(ws, row,
        "3. 本次任务说明",
        "例如：抽取游戏内所有专有名词供翻译团队使用",
        40)
    row += 1

    # ── 第二部分：要提取什么 ───────────────────────────────────────────────
    section_header(ws, row, "二、要提取的内容（告诉 AI 抓什么）")
    row += 1

    question_row(ws, row,
        "4. 必须提取的术语类型",
        "用自然语言列出所有需要提取的类型。\n"
        "例如：\n"
        "· 所有人名/NPC名（不管主次）\n"
        "· 武学招式名\n"
        "· 地点、建筑名\n"
        "· 门派、组织名\n"
        "· 道具、圣物名\n"
        "· 战斗技能/BUFF名\n"
        "……越详细越好",
        160)
    row += 1

    question_row(ws, row,
        "5. 不要提取的内容",
        "例如：\n"
        "· 日常通用物品（木炭、草鞋）\n"
        "· 泛称/称谓（大侠、公子、弟子）\n"
        "· 时间词（子时、春分）\n"
        "· 成语固定短语",
        120)
    row += 1

    question_row(ws, row,
        "6. 特别注意事项",
        '有没有容易搞混的边界情况？\n'
        '例如：\n'
        '· "青"单独出现时是角色名要提取，但"青色"不要\n'
        '· 带"老X、小X、阿X"前缀的一律是人名要提取\n'
        '· 排行式命名（戈老大、戈老二）全部提取',
        100)
    row += 1

    # ── 第三部分：术语分类 ─────────────────────────────────────────────────
    section_header(ws, row, "三、术语分类")
    row += 1

    question_row(ws, row,
        "7. 术语分类列表",
        "列出这个游戏的术语分类，每行一个。\n"
        "常见参考：\n"
        "NPC名、BOSS名、武学招式、武学心法、\n"
        "地名建筑、场景区域、门派势力、组织帮会、\n"
        "道具物品、圣物法宝、代币货币、资源材料、\n"
        "战斗BUFF、战斗机制、UI系统、玩法机制、\n"
        "任务名、成就称号、外观皮肤\n"
        "（可以直接复制修改，也可自己写）",
        200)
    row += 1

    # ── 第四部分：翻译方向 ─────────────────────────────────────────────────
    section_header(ws, row, "四、翻译策略（选填）")
    row += 1

    question_row(ws, row,
        "8. 目标语言",
        "例如：英文、日文、韩文、繁体中文……",
        30)
    row += 1

    question_row(ws, row,
        "9. 翻译策略说明",
        "对各类术语的翻译方向说明。\n"
        "例如：\n"
        "· 人名：音译（拼音）\n"
        "· 招式名：意译，传达含义\n"
        "· 地点：意译为主\n"
        "· 称谓（公子、长老）：对应英文 Master / Elder\n"
        '如果没有特别要求，写"统一意译"即可',
        120)
    row += 1

    # ── 第五部分：举例 ─────────────────────────────────────────────────────
    section_header(ws, row, "五、举例（越多越准确）")
    row += 1

    question_row(ws, row,
        "10. 应该提取的例子",
        "贴几条游戏原文，标注哪些词是术语。\n"
        "格式随意，例如：\n"
        "「万大海常年往来于沦波坊和神仙渡」\n"
        "→ 万大海（NPC名）、沦波坊（地名）、神仙渡（地名）\n\n"
        "多写几条，覆盖不同类型的术语",
        200)
    row += 1

    question_row(ws, row,
        "11. 不该提取的例子",
        "贴几条不含术语、或容易误判的原文。\n"
        "格式随意，例如：\n"
        "「用木炭生火，草鞋踩在石板上」→ 无术语\n"
        "「先生说弟子不得擅自出门」→ 无术语（先生/弟子是泛称）",
        120)
    row += 1

    # ── 第六部分：其他 ─────────────────────────────────────────────────────
    section_header(ws, row, "六、其他补充（选填）")
    row += 1

    question_row(ws, row,
        "12. 其他说明",
        "有什么额外需要告知的信息，都可以写在这里。",
        80)

    wb.save(OUT)
    print(f"已生成：{OUT}")


if __name__ == "__main__":
    main()
