"""
分句工具：在不修改原始文本内容的前提下完成句子切分
输出包含 text/start/end/token_count 的字典列表，位置索引对应原始文本
"""
import json
import re
import tiktoken
from typing import Dict, List, Tuple, Union, Any

# 初始化tiktoken编码器
ENCODING = tiktoken.get_encoding("cl100k_base")

# 常见缩写（完整列表，与 sentence_splitter 保持一致）
COMMON_ABBREVIATIONS = {
    # 通用学术
    "e.g.", "i.e.", "etc.", "et al.", "cf.", "vs.", "ca.", "approx.",
    # 材料领域
    "wt.", "wt.%", "vol.", "vol.%", "mol.", "mol.%", "at.", "at.%", "conc.",
    "temp.", "ref.", "Fig.", "Figs.", "Fig.-", "Tab.", "Tabs.", "Eq.", "Eqs.",
    "No.", "Nos.", "Dr.", "Mr.", "Ms.", "Prof.", "Ph.D.",
    # 常见英文缩略词尾点
    "U.S.", "U.K.", "Jr.", "Sr."
}

# 元素符号（完整列表）
ELEMENT_SYMBOLS = {
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar",
    "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr",
    "Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
    "In", "Sn", "Sb", "Te", "I", "Xe",
    "Cs", "Ba", "La", "Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd",
    "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu",
    "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Tl", "Pb", "Bi", "Po", "At", "Rn",
    "Fr", "Ra", "Ac", "Th", "Pa", "U", "Np", "Pu", "Am", "Cm",
    "Bk", "Cf", "Es", "Fm", "Md", "No", "Lr",
    "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds", "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og"
}

# 正则模式
# 图表引用模式：匹配 Fig. 1, Fig. 2a, (Fig. 2f), Fig. S1 等
FIG_TAB_PATTERN = re.compile(r'(?:Fig|Tab|Scheme|Eq|Ref|No|Chart)\.\s*S?\d+[a-zA-Z]?')
# 带括号的图表引用模式：匹配 (Fig. 2f) 或 (Fig. S1) 等
FIG_TAB_PAREN_PATTERN = re.compile(r'\((?:Fig|Tab|Scheme|Eq|Ref|Chart)\.\s*S?\d+[a-zA-Z,\-\s]*\)')
UNIT_PATTERN = re.compile(r'\b\d+(?:\.\d+)?\s*(?:wt|vol|mol|at|mass|volum|area|thick|temp)\.?%?\b', re.IGNORECASE)
DECIMAL_PATTERN = re.compile(r'\d+\.\d+')
SCIENTIFIC_PATTERN = re.compile(r'\b\d+(?:\.\d+)?(?:[eE][+-]?\d+|×10(?:\^\d+|\s*\d+))\b')
CHEM_FORMULA_PATTERN = re.compile(r'''
    (?:[A-Z][a-z]?)(?:_\{?\d+(?:\.\d+)?\}?)*
    (?:[A-Z][a-z]?\d*(?:\.\d+)?)*
''', re.X)

SENT_END_CANDIDATE_WITH_SPACE = re.compile(r'([.?!])(?=\s+["\'(\[{<]*[A-Z0-9])')
SENT_END_CANDIDATE_NO_SPACE = re.compile(r'([.?!])(?=["\'(\[{<]*[A-Z])')


def _mask_protected_regions(text: str) -> Tuple[str, List[Tuple[int, int]]]:
    """
    将需要保护的区域（数学表达式、LaTeX 等）用空格替换，
    返回掩码后的文本和被保护区域的位置列表。
    保护的内容在断句时不会被误切。
    """
    masked = list(text)
    protected_regions = []

    # 1. 保护 $$...$$ (块级数学表达式)
    for match in re.finditer(r'\$\$(?:[^$]|\$(?!\$))*?\$\$', text, flags=re.DOTALL):
        start, end = match.start(), match.end()
        protected_regions.append((start, end))
        for i in range(start, end):
            masked[i] = ' '

    # 2. 保护 $...$ (行内数学表达式)
    for match in re.finditer(r'\$(?:[^$\n]|\\\$)*?\$', text):
        start, end = match.start(), match.end()
        # 检查是否与已保护区域重叠
        if not any(s <= start < e or s < end <= e for s, e in protected_regions):
            protected_regions.append((start, end))
            for i in range(start, end):
                masked[i] = ' '

    # 3. 保护 LaTeX 命令 \command{...}
    for match in re.finditer(r'\\[a-zA-Z]+\{[^}]*\}', text):
        start, end = match.start(), match.end()
        if not any(s <= start < e or s < end <= e for s, e in protected_regions):
            protected_regions.append((start, end))
            for i in range(start, end):
                masked[i] = ' '

    return ''.join(masked), protected_regions


def should_split(text: str, idx: int) -> bool:
    """
    idx 指向句末符号（., !, ?）。
    根据上下文决定是否切句（有空格的情况）。
    与 sentence_splitter.py 保持一致的逻辑。
    """
    prev_chunk = text[:idx].rstrip()
    next_chunk = text[idx + 1:].lstrip()

    # 1. 若前面为空，直接返回 False
    if not prev_chunk:
        return False

    # 2. 获取前一个 token
    prev_token_match = re.search(r'([\w\\\{\}\^\-\+\%\·]+)$', prev_chunk)
    prev_token = prev_token_match.group(1) if prev_token_match else ""

    # 3. 小数 / 科学计数法
    if DECIMAL_PATTERN.search(prev_token):
        return False
    if SCIENTIFIC_PATTERN.search(prev_chunk[-12:]):
        return False

    # 4. 图表/方程引用
    if FIG_TAB_PATTERN.search(prev_chunk[-20:]):
        return False

    # 4.5 检查是否是 "Fig. 2f" 这种模式的开始部分
    # 如果 prev_chunk 以 Fig/Tab/Scheme 等结尾，且 next_chunk 以数字或 S（补充材料）开头
    fig_prefix_match = re.search(r'\b(Fig|Tab|Scheme|Eq|Ref|Chart)$', prev_chunk, re.IGNORECASE)
    if fig_prefix_match and next_chunk:
        # 检查 next_chunk 是否以数字或 S（如 S1, S2 等补充材料图）开头
        if re.match(r'^[S\d]', next_chunk):
            return False

    # 5. 单位表达式
    if UNIT_PATTERN.search(prev_chunk[-30:]):
        return False

    # 6. LaTeX/化学式结构
    if "_" in prev_token or "^" in prev_token or CHEM_FORMULA_PATTERN.fullmatch(prev_token):
        return False

    # 7. 缩写列表
    if any(prev_chunk.endswith(abbrev) for abbrev in COMMON_ABBREVIATIONS):
        return False

    # 8. 元素符号结尾（例如 "Mo."），避免误切
    if prev_token.rstrip(".") in ELEMENT_SYMBOLS and prev_token.endswith("."):
        return False

    # 9. 下一个 token 若以小写字母开头，极可能是量纲缩写或公式延续
    if next_chunk and next_chunk[0].islower():
        return False

    # 10. 若 next_chunk 以 ) } ] 等闭合符号开头，也倾向于不切
    if next_chunk and next_chunk[0] in ")]}":
        return False

    return True


def should_split_no_space(text: str, idx: int) -> bool:
    """
    idx 指向句末符号（., !, ?），且后面直接跟大写字母（无空格）。
    需要更仔细判断，避免误判小数、缩写等。
    与 sentence_splitter.py 保持一致的逻辑。
    """
    prev_chunk = text[:idx].rstrip()
    next_chunk = text[idx + 1:].lstrip()

    # 1. 若前面为空，直接返回 False
    if not prev_chunk:
        return False

    # 2. 获取前一个 token（更长的上下文）
    prev_token_match = re.search(r'([\w\\\{\}\^\-\+\%\·\[\]]+)$', prev_chunk)
    prev_token = prev_token_match.group(1) if prev_token_match else ""

    # 3. 检查是否是小数
    if DECIMAL_PATTERN.search(prev_token):
        return False

    # 4. 检查是否是引用格式（例如 "[1].Electrolyzing"）
    if prev_chunk and prev_chunk[-1] in '])':
        ref_match = re.search(r'\[[\d\-,]+\]|\([\d\-,]+\)', prev_chunk[-10:])
        if ref_match:
            return True

    # 5. 检查是否是缩写
    if any(prev_chunk.endswith(abbrev) for abbrev in COMMON_ABBREVIATIONS):
        return False

    # 6. 检查是否是元素符号
    if prev_token.rstrip(".") in ELEMENT_SYMBOLS and prev_token.endswith("."):
        return False

    # 7. 检查是否是图表引用
    if FIG_TAB_PATTERN.search(prev_chunk[-20:]):
        return False

    # 8. 检查前一个 token 是否以数字结尾
    if prev_token and prev_token[-1].isdigit():
        if len(prev_token) > 1 and prev_token[-2].isalpha():
            return True

    # 9. 检查前一个 token 是否以常见句末词结尾
    last_word_match = re.search(r'([a-zA-Z]+)$', prev_token)
    if last_word_match:
        last_word = last_word_match.group(1).lower()
        common_sentence_endings = [
            'result', 'conclusion', 'method', 'experiment', 'analysis',
            'study', 'finding', 'work', 'treatment', 'electrolysis',
            'schedules', 'content', 'alloy', 'alloys', 'phase', 'phases',
            'cost', 'production', 'way', 'role', 'target', 'agreement',
            'source', 'kinetics', 'overpotentials', 'resistance',
            'efficiency', 'applications', 'catalysis', 'proportions',
            'activities', 'durability', 'overpotential',
            'increase', 'decrease', 'change', 'transition', 'transitioned'
        ]
        if last_word in common_sentence_endings:
            return True

    # 10. 检查更大的上下文，看是否以常见句末短语结尾
    if prev_chunk:
        last_words_match = re.search(r'([a-zA-Z\s]+)$', prev_chunk.rstrip('.,!?;:'))
        if last_words_match:
            last_words = ' '.join(last_words_match.group(1).lower().split())
            sentence_ending_patterns = [
                'with the increase of', 'with the decrease of',
                'with increase of', 'with decrease of',
                'with the increase', 'with the decrease',
                'of content', 'of phase', 'of phases', 'of alloy', 'of alloys',
                'mo content', 'mo phase', 'mo phases'
            ]
            for pattern in sentence_ending_patterns:
                if last_words.endswith(pattern):
                    return True

    # 11. 如果前一个 token 是单个大写字母加句号
    if len(prev_token) == 2 and prev_token[0].isupper() and prev_token[1] == '.':
        return True

    # 12. 检查更大的上下文
    if prev_chunk:
        last_context = prev_chunk[-30:].lower()
        sentence_ending_phrases = [
            'with the increase of', 'with the decrease of',
            'with increase of', 'with decrease of',
            'with the increase', 'with the decrease',
            'according to', 'due to', 'based on',
            'of content', 'of phase', 'of phases', 'of alloy', 'of alloys',
            'the microstructure', 'the structure', 'the properties'
        ]
        for phrase in sentence_ending_phrases:
            if last_context.endswith(phrase) or last_context.rstrip('.,!?;:').endswith(phrase):
                return True

    # 13. 默认情况：如果前面看起来像完整句子，且后面跟大写字母，倾向于分句
    if len(prev_token) > 3 and prev_chunk.rstrip()[-1] == '.':
        if prev_token.lower() not in ['fig', 'tab', 'eq', 'ref', 'no', 'dr', 'mr', 'ms', 'prof']:
            return True

    return False


def _find_newline_positions(text: str) -> List[int]:
    """找到所有换行符的位置"""
    positions = []
    for i, char in enumerate(text):
        if char == '\n':
            positions.append(i)
    return positions


def _collect_sentence_boundaries(text: str, masked_text: str, block_start: int, block_end: int) -> List[int]:
    """
    在指定的文本块内收集所有句子断点位置。
    使用 masked_text 进行断句判断，但返回的位置是相对于原始文本的。
    """
    boundaries = []
    block_text = masked_text[block_start:block_end]

    # 1. 有空格的情况
    for match in SENT_END_CANDIDATE_WITH_SPACE.finditer(block_text):
        local_idx = match.start(1)
        global_idx = block_start + local_idx
        if should_split(masked_text, global_idx):
            boundaries.append(global_idx)

    # 2. 无空格但直接跟大写字母的情况
    for match in SENT_END_CANDIDATE_NO_SPACE.finditer(block_text):
        local_idx = match.start(1)
        global_idx = block_start + local_idx
        if should_split_no_space(masked_text, global_idx):
            boundaries.append(global_idx)

    return sorted(set(boundaries))


def split_text_to_chunks(text: str) -> List[Dict[str, Union[int, str]]]:
    """
    按照句子级别切分文本，并返回包含 text/start/end/token_count 的字典列表。
    start 为起始字符索引，end 为结束字符索引（不含）。
    token_count 为使用 tiktoken (cl100k_base) 编码计算的 token 数量。

    核心逻辑：
    1. 换行符是最高优先级的分割点
    2. 在每个文本块内，保护数学表达式后进行断句
    3. 返回的 text 是原始文本的切片，位置索引不变
    4. 每个 chunk 包含使用 tiktoken 计算的 token 数量
    5. 合并 token_count < 20 的小句子
    """
    if not text:
        return []

    # 第一步：创建掩码文本（保护数学表达式等）
    masked_text, _ = _mask_protected_regions(text)

    # 第二步：找到所有换行符位置作为强制分割点
    newline_positions = _find_newline_positions(text)

    # 第三步：确定所有文本块的范围（按换行符分割）
    block_ranges = []
    current_start = 0
    for nl_pos in newline_positions:
        if nl_pos > current_start:
            block_ranges.append((current_start, nl_pos))
        current_start = nl_pos + 1
    if current_start < len(text):
        block_ranges.append((current_start, len(text)))

    # 第四步：在每个文本块内收集句子断点
    all_boundaries = set()
    
    # 添加所有换行符位置作为强制断点（在换行符之前断开）
    for nl_pos in newline_positions:
        if nl_pos > 0:
            all_boundaries.add(nl_pos - 1)

    # 在每个块内收集句子断点
    for block_start, block_end in block_ranges:
        block_boundaries = _collect_sentence_boundaries(text, masked_text, block_start, block_end)
        all_boundaries.update(block_boundaries)

    # 第五步：根据断点生成 chunks
    sorted_boundaries = sorted(all_boundaries)
    chunks = []
    current_start = 0

    for boundary in sorted_boundaries:
        # boundary 是句末符号的位置，切分点在 boundary + 1
        end_idx = boundary + 1

        if end_idx <= current_start:
            continue

        # 跳过末尾的空白字符，但不跨越换行符
        while end_idx < len(text) and text[end_idx] == ' ':
            end_idx += 1

        chunk_text = text[current_start:end_idx]
        if chunk_text.strip():  # 只添加非空的 chunk
            token_count = len(ENCODING.encode(chunk_text))
            chunks.append({
                "text": chunk_text,
                "start": current_start,
                "end": end_idx,
                "token_count": token_count
            })

        current_start = end_idx

    # 处理剩余部分
    if current_start < len(text):
        remaining = text[current_start:]
        if remaining.strip():
            token_count = len(ENCODING.encode(remaining))
            chunks.append({
                "text": remaining,
                "start": current_start,
                "end": len(text),
                "token_count": token_count
            })

    # 第六步：后处理 - 将以公式符号开头的 chunk 合并回上一个 chunk
    merged_chunks = []
    for chunk in chunks:
        chunk_text = chunk["text"].lstrip()
        if merged_chunks and re.match(r'^[\^\_\{\}\(\)\[\]\\]', chunk_text):
            # 合并到上一个 chunk
            prev = merged_chunks[-1]
            merged_text = text[prev["start"]:chunk["end"]]
            prev["text"] = merged_text
            prev["end"] = chunk["end"]
            prev["token_count"] = len(ENCODING.encode(merged_text))
        else:
            merged_chunks.append(chunk)

    # 第七步：合并 token_count 过小的句子
    final_chunks = []
    i = 0
    while i < len(merged_chunks):
        current_chunk = merged_chunks[i]
        current_token_count = current_chunk["token_count"]

        # 如果当前句子的 token_count >= 20，直接保留
        if current_token_count >= 20:
            final_chunks.append(current_chunk)
            i += 1
            continue

        # 如果当前句子的 token_count < 20，需要向下合并
        merged_text = current_chunk["text"]
        merged_end = current_chunk["end"]
        merged_token_count = current_token_count

        # 继续合并后续句子，直到 token_count >= 20 或没有更多句子
        j = i + 1
        while j < len(merged_chunks) and merged_token_count < 20:
            next_chunk = merged_chunks[j]
            merged_text = text[current_chunk["start"]:next_chunk["end"]]
            merged_end = next_chunk["end"]
            merged_token_count = len(ENCODING.encode(merged_text))
            j += 1

        # 创建合并后的 chunk
        final_chunk = {
            "text": merged_text,
            "start": current_chunk["start"],
            "end": merged_end,
            "token_count": merged_token_count
        }
        final_chunks.append(final_chunk)

        # 更新索引，跳过已合并的句子
        i = j

    # 转换为最终输出格式
    result = []
    for idx, chunk in enumerate(final_chunks, 1):
        result.append({
            "id": idx,
            "sentence": chunk["text"]
        })

    return result


def main():
    """主函数：读取文件，进行分句，并保存结果"""
    input_file = "/Users/xiaokong/task/2025/electrocatalysis/new_ex/test.txt"
    output_file = "sentence_split.json"

    with open(input_file, "r", encoding="utf-8") as f:
        text = f.read()

    sentences = split_text_to_chunks(text)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(sentences, f, indent=2, ensure_ascii=False)

    print(f"处理完成，共切分 {len(sentences)} 个句子，结果已保存到: {output_file}")


if __name__ == "__main__":
    main()
