import os
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties


def setup_cjk_font():
    candidates = [
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        '/mnt/c/Windows/Fonts/msyh.ttc',
        'C:/Windows/Fonts/msyh.ttc',
        '/mnt/c/Windows/Fonts/simhei.ttf',
        'C:/Windows/Fonts/simhei.ttf',
    ]
    for path in candidates:
        if os.path.isfile(path):
            font_manager.fontManager.addfont(path)
            prop = FontProperties(fname=path)
            plt.rcParams['font.family'] = prop.get_name()
            plt.rcParams['axes.unicode_minus'] = False
            return prop

    plt.rcParams['font.sans-serif'] = [
        'Microsoft YaHei',
        'SimHei',
        'Noto Sans CJK SC',
        'Arial Unicode MS',
        'sans-serif',
    ]
    plt.rcParams['axes.unicode_minus'] = False
    return FontProperties(family=plt.rcParams['font.sans-serif'][0])
