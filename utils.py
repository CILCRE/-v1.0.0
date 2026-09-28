def auto_analyze(img):
    """扫描 alpha 通道，推断横向帧数、纵向行数"""
    w, h = img.size
    alpha = img.split()[-1]
    pixels = alpha.load()

    def col_empty(x):
        for y in range(h):
            if pixels[x, y] > 10:
                return False
        return True

    def row_empty(y):
        for x in range(w):
            if pixels[x, y] > 10:
                return False
        return True

    col_blocks, in_block, start = [], False, 0
    for x in range(w):
        if not col_empty(x):
            if not in_block:
                in_block, start = True, x
        else:
            if in_block:
                col_blocks.append((start, x - 1))
                in_block = False
    if in_block:
        col_blocks.append((start, w - 1))

    row_blocks, in_block, start = [], False, 0
    for y in range(h):
        if not row_empty(y):
            if not in_block:
                in_block, start = True, y
        else:
            if in_block:
                row_blocks.append((start, y - 1))
                in_block = False
    if in_block:
        row_blocks.append((start, h - 1))

    return col_blocks, row_blocks