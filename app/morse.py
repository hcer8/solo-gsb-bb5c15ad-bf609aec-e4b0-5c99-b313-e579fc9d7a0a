"""缺分隔电报码校读核心算法。

给定一段无分隔的点划记录和若干候选英文单词，候选词按国际摩尔斯
字母表编码后可无分隔地拼接成一个词序列（1～6 个词，词可重复）。
本模块以"点划的插入 / 删除 / 替换各计一次"的编辑距离为准则，
对所有合法词序列做全局搜索（非贪心、非逐词纠错），按以下优先级
选出唯一最优序列：

  1. 与记录的编辑距离最小；
  2. 词数最少；
  3. 词序列字典序最小。

实现方式：把所有候选词的摩尔斯编码构造成一棵 trie，trie 的各层
节点即为一个识别"1～6 个编码拼接"的 NFA 的状态；编辑距离的
DP 在该 NFA 上铺开（Levenshtein 自动机思路），保证全局最优。
"""

from __future__ import annotations

# 国际摩尔斯字母表（26 个大写英文字母）
MORSE_TABLE = {
    "A": ".-",
    "B": "-...",
    "C": "-.-.",
    "D": "-..",
    "E": ".",
    "F": "..-.",
    "G": "--.",
    "H": "....",
    "I": "..",
    "J": ".---",
    "K": "-.-",
    "L": ".-..",
    "M": "--",
    "N": "-.",
    "O": "---",
    "P": ".--.",
    "Q": "--.-",
    "R": ".-.",
    "S": "...",
    "T": "-",
    "U": "..-",
    "V": "...-",
    "W": ".--",
    "X": "-..-",
    "Y": "-.--",
    "Z": "--..",
}

MAX_RECORD_LEN = 60
MAX_WORDS = 20
MAX_WORD_LEN = 12
MAX_SEQ_LEN = 6  # 一个词序列最多拼接的词数

_SYMBOLS = (".", "-")


class InvalidInput(ValueError):
    """输入不满足接口契约。"""


def _build_trie(words: list[str]) -> tuple[dict[tuple[int, str], int], list[str | None]]:
    """由候选词编码构造 trie。

    返回 ``(children, terminal)``：``children[(node, sym)]`` 是沿
    点划 ``sym`` 转移到的子节点；``terminal[node]`` 是在该节点
    结束的、字典序最小的候选词（同编码的多个词只可能在拼写上不同，
    按字典序保留最小者即可）。
    """
    children: dict[tuple[int, str], int] = {}
    terminal: list[str | None] = [None]  # 0 为根

    for word in sorted(words):
        code = "".join(MORSE_TABLE[ch] for ch in word)
        node = 0
        for sym in code:
            nxt = children.get((node, sym))
            if nxt is None:
                nxt = len(terminal)
                terminal.append(None)
                children[(node, sym)] = nxt
            node = nxt
        # sorted(words) 保证首个到达该节点的词即字典序最小者
        if terminal[node] is None:
            terminal[node] = word

    return children, terminal


def best_correction(record: str, words: list[str]) -> dict[str, object]:
    """求最优词序列。

    返回 ``{"words": [...], "morse": "拼接点划串", "edits": 最少次数}``。
    输入合法性由 :func:`validate_input` 保证，本函数假定输入合法。
    """
    children, terminal = _build_trie(words)

    # NFA 状态 = (已完成词数 layer, trie 节点 node)。
    # 每条 row 对应处理完记录前 i 个点划后的 DP；state ->
    # (编辑次数, 词序列)。同一状态下编辑次数严格更优，或次数相同
    # 但词序列字典序更小时，才需要保留。
    row: dict[tuple[int, int], tuple[int, tuple[str, ...]]] = {(0, 0): (0, ())}

    for ch in record:
        nxt: dict[tuple[int, int], tuple[int, tuple[str, ...]]] = {}

        def relax(state, cost, seq):
            old = nxt.get(state)
            if old is None or cost < old[0] or (cost == old[0] and seq < old[1]):
                nxt[state] = (cost, seq)

        for (layer, node), (cost, seq) in row.items():
            # 删除记录中的一个点划（NFA 不动）
            relax((layer, node), cost + 1, seq)
            # 匹配 / 替换：沿 trie 的字符边消耗一个点划
            for sym in _SYMBOLS:
                child = children.get((node, sym))
                if child is not None:
                    relax((layer, child), cost + (sym != ch), seq)

        # 词尾的零代价 epsilon 闭包：词结束后可回到下一层根节点
        # 继续拼接新词（layer < MAX_SEQ_LEN），也可停在词尾继续
        # 沿 trie 延伸（如编码 AT 与 ET 前缀重叠的情形）。
        # trie 节点按深度递增分配，按节点顺序遍历即可保证闭包传播。
        for node in range(len(terminal)):
            word = terminal[node]
            if word is None:
                continue
            for layer in range(MAX_SEQ_LEN):
                cur = nxt.get((layer, node))
                if cur is not None:
                    cost, seq = cur
                    relax((layer + 1, 0), cost, seq + (word,))

        row = nxt

    # 消耗完整个记录后，接受状态为"恰好停在词边界"的各层根节点
    best: tuple[int, tuple[str, ...]] | None = None
    for layer in range(1, MAX_SEQ_LEN + 1):
        cur = row.get((layer, 0))
        if cur is None:
            continue
        cost, seq = cur
        key = (cost, len(seq), seq)
        if best is None or key < (best[0], len(best[1]), best[1]):
            best = (cost, seq)

    assert best is not None, "合法输入下至少存在一个可接受序列"
    cost, seq = best
    morse = "".join("".join(MORSE_TABLE[ch] for ch in word) for word in seq)
    return {"words": list(seq), "morse": morse, "edits": cost}


def validate_input(record: object, words: object) -> tuple[str, list[str]]:
    """校验接口输入，非法时抛 :class:`InvalidInput`（对应 HTTP 400）。"""
    if not isinstance(record, str) or not record:
        raise InvalidInput("record 必须是 1～%d 个点划符号组成的非空字符串" % MAX_RECORD_LEN)
    if len(record) > MAX_RECORD_LEN:
        raise InvalidInput("record 长度不能超过 %d" % MAX_RECORD_LEN)
    if any(ch not in ".-" for ch in record):
        raise InvalidInput("record 只能包含 '.' 和 '-'")

    if not isinstance(words, list) or not words:
        raise InvalidInput("words 必须是 1～%d 个候选词组成的非空数组" % MAX_WORDS)
    if len(words) > MAX_WORDS:
        raise InvalidInput("候选词数量不能超过 %d" % MAX_WORDS)

    clean: list[str] = []
    seen: set[str] = set()
    for word in words:
        if not isinstance(word, str) or not word:
            raise InvalidInput("每个候选词必须是长度 1～%d 的字符串" % MAX_WORD_LEN)
        if len(word) > MAX_WORD_LEN:
            raise InvalidInput("候选词长度不能超过 %d：%s" % (MAX_WORD_LEN, word))
        if any(not ("A" <= ch <= "Z") for ch in word):
            raise InvalidInput("候选词只能含大写英文字母 A-Z：%s" % word)
        if word not in seen:
            seen.add(word)
            clean.append(word)

    return record, clean
