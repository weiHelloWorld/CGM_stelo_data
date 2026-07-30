"""
Bidirectional food name map for meal description translation.

Provides `convert_meal_name_language()` which translates food names
between English and Chinese based on config.TEXT_LANGUAGE.
"""

import re

# ── English → Chinese ──────────────────────────────────────────

English_to_Chinese_map = {
    "lettuce": "生菜",
    "tofu": "豆腐",
    "milk": "牛奶",
    "oats": "燕麦片",
    "oatmeal": "燕麦片",
    "protein powder": "蛋白粉",
    "pasta": "意面",
    "tomato sauce": "番茄酱",
    "pork": "猪肉",
    "yogurt": "酸奶",
    "chobani zero sugar yogurt": "零糖酸奶",
    "oikos triple zero mixed berry": "零脂混合莓酸奶",
    "oikos triple zero strawberry flavored yogurt": "草莓味零脂酸奶",
    "orange": "橙子",
    "yakult": "养乐多",
    "yakult light drink": "低糖养乐多",
    "imitation crab meat": "蟹肉棒",
    "pistachios": "开心果",
    "pistachio": "开心果",
    "apple": "苹果",
    "fish tofu": "鱼豆腐",
    "eggs": "鸡蛋",
    "egg": "鸡蛋",
    "Pocky": "百奇",
    "Swiss roll": "瑞士卷",
    "coke": "可乐",
    "zero sugar coke": "零糖可乐",
    "Kung Pao chicken": "宫保鸡丁",
    "white rice": "白米饭",
    "instant ramen": "方便面",
    "maruchan instant ramen": "日清方便面",
    "sardine": "沙丁鱼",
    "sweet potato": "红薯",
    "pork bbq": "烤猪肉",
    "shrimp tempura": "天妇罗虾",
    "shrimp": "虾",
    "mushrooms": "蘑菇",
    "mushroom": "蘑菇",
    "peas": "豌豆",
    "carrots": "胡萝卜",
    "chicken nuggets": "炸鸡块",
    "chicken nugget": "炸鸡块",
    "beef": "牛肉",
    "swai": "巴沙鱼",
    "chicken breast": "鸡胸肉",
    "chickpeas": "鹰嘴豆",
    "walnuts": "核桃",
    "glucose": "葡萄糖",
    "pasta sauce": "意面酱",
    "red leaf lettuce": "红叶生菜",
    "chow mein": "炒面",
    "mushroom chicken": "蘑菇鸡",
    "Beijing beef": "北京牛肉",
    "pepperoni pizza": "意大利辣香肠披萨",
    "pizza": "披萨",
    "noodles": "面条",
    "broth": "汤底",
    "seafood": "海鲜",
    "with": "配",
}

# ── Chinese → English (reverse of above + additional entries) ──

Chinese_to_English_map = {
    # Reverse of English_to_Chinese_map
    "生菜": "lettuce",
    "豆腐": "tofu",
    "牛奶": "milk",
    "燕麦片": "oatmeal",
    "蛋白粉": "protein powder",
    "意面": "pasta",
    "番茄酱": "tomato sauce",
    "猪肉": "pork",
    "酸奶": "yogurt",
    "零糖酸奶": "zero-sugar yogurt",
    "零脂混合莓酸奶": "zero-sugar yogurt",
    "草莓味零脂酸奶": "zero-sugar yogurt",
    "橙子": "orange",
    "养乐多": "yakult",
    "低糖养乐多": "yakult light drink",
    "蟹肉棒": "imitation crab meat",
    "开心果": "pistachios",
    "苹果": "apple",
    "鱼豆腐": "fish tofu",
    "鸡蛋": "eggs",
    "百奇": "Pocky",
    "瑞士卷": "Swiss roll",
    "可乐": "coke",
    "零糖可乐": "zero sugar coke",
    "宫保鸡丁": "Kung Pao chicken",
    "白米饭": "white rice",
    "方便面": "instant ramen",
    "日清方便面": "instant ramen",
    "沙丁鱼": "sardine",
    "红薯": "sweet potato",
    "烤猪肉": "pork bbq",
    "天妇罗虾": "shrimp tempura",
    "虾": "shrimp",
    "蘑菇": "mushroom",
    "豌豆": "peas",
    "胡萝卜": "carrots",
    "炸鸡块": "chicken nuggets",
    "牛肉": "beef",
    "巴沙鱼": "swai",
    "鸡胸肉": "chicken breast",
    "鹰嘴豆": "chickpeas",
    "核桃": "walnuts",
    "葡萄糖": "glucose",
    "意面酱": "pasta sauce",
    "红叶生菜": "red leaf lettuce",
    "炒面": "chow mein",
    "蘑菇鸡": "mushroom chicken",
    "北京牛肉": "Beijing beef",
    "意大利辣香肠披萨": "pepperoni pizza",
    "披萨": "pizza",
    "面条": "noodles",
    "汤底": "broth",
    "海鲜": "seafood",
    # Additional Chinese entries found in food log
    "烤鸭": "roast duck",
    "带骨烤鸭": "roast duck",
    "辣子鸡": "spicy chicken",
    "盐水鸭": "salty duck",
    "半份盐水鸭": "1/2 salty duck",
    "酸菜鱼": "sour cabbage fish",
    "黑鱼": "black fish",
    "金鲳鱼": "golden pomfret",
    "跳跳鱼": "jumping fish",
    "三峡人家跳跳鱼": "Spicy Jumping fish",
    "炒饭": "fried rice",
    "螺蛳粉": "Rice Noodles",
    "水煮鱼": "boiled fish in chili",
    "麻婆豆腐": "Mapo Tofu",
    "好人家麻婆豆腐调料": "Mapo Tofu seasoning",
    "鸡块": "chicken nuggets",
    "鸡胸肉罐头": "chicken breast",
    "辛拉面": "Shin Ramyun (instant noodles)",
    "带壳开心果": "pistachios",
    "熟米饭": "rice",
    "沙丁鱼罐头": "sardine",
    "包菜": "cabbage",
    "紫菜": "seaweed",
    "海带": "kelp",
    "豆芽": "bean sprouts",
    "香菇": "shiitake mushroom",
    "黑豆": "black beans",
    "肉松": "meat floss",
    "益力多": "yakult",
    "鸡": "chicken",
    "Weee": '',
    # Measure words (remove)
    "个": " ",
    # Quantity qualifiers (trailing space avoids gluing words)
    "半份": "1/2 ",
    "粉包": "seasoning packet",
    "调料": " seasoning",
    # Punctuation / connectors
    "，": ", ",
    "、": ", ",
    "（": " (",
    "）": ") ",
}


# ── Helpers ─────────────────────────────────────────────────────

def _clean(text: str) -> str:
    """Clean up spacing artifacts after replacement."""
    def _split_unit(m):
        num, unit, next_l = m.groups()
        if unit.lower() in ('g', 'mg', 'kg', 'oz'):
            return f"{num}{unit} {next_l}"
        return m.group(0)
    # Fix gluing: when a unit suffix (g, mg, kg) is followed directly by a letter
    text = re.sub(r"(\d+)([a-zA-Z]{1,3}?)([a-zA-Z])", _split_unit, text)
    # Fix gluing: fraction like "1/2noodle" → "1/2 noodle"
    text = re.sub(r"(/\d+)([a-zA-Z])", r"\1 \2", text)
    # Fix digit + parenthesis
    text = re.sub(r"(\d)(\()", r"\1 \2", text)
    text = re.sub(r"(\))(\d)", r"\1 \2", text)
    # Collapse spaces
    text = re.sub(r" +", " ", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\s+\)", ")", text)
    text = re.sub(r"\(\s+", "(", text)
    text = text.strip().strip(",").strip()
    return text


# ── Main public API ─────────────────────────────────────────────

def convert_meal_name_language(food_name: str) -> str:
    """Translate a food name based on the configured TEXT_LANGUAGE.

    When TEXT_LANGUAGE is "zh", translates English terms → Chinese.
    When TEXT_LANGUAGE is "en", translates Chinese terms → English.

    Mixed Chinese/English strings are supported. Unrecognised tokens
    are left as-is.
    """
    from config import TEXT_LANGUAGE as _LANG

    if not isinstance(food_name, str) or not food_name.strip():
        return food_name

    text = food_name

    if _LANG == "en":
        # Chinese → English: simple substring replace (Chinese chars are word-like)
        for chi, eng in sorted(
            Chinese_to_English_map.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        ):
            text = text.replace(chi, eng)
        text = _clean(text)
    else:
        # English → Chinese: use word-boundary regex matching on lowercased text,
        # then re-capitalise the first letter of the result for proper appearance.
        text_lower = food_name.lower()
        for eng, chi in sorted(
            English_to_Chinese_map.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        ):
            pattern = rf"\b{re.escape(eng.lower())}\b"
            text_lower = re.sub(pattern, chi, text_lower)
        text = text_lower[0].upper() + text_lower[1:] if text_lower else text_lower

    return text if text.strip() else food_name

