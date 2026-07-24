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
    "broth": "汤底",  # if appeared
    "seafood": "海鲜"   # if needed
}

import re

def to_Chinese_meal_name(food_name: str) -> str:
    """Translate an English meal description into Chinese using known map entries."""
    if not isinstance(food_name, str) or not food_name.strip():
        return food_name

    text = food_name.lower()
    for eng, chi in sorted(
        English_to_Chinese_map.items(),
        key=lambda item: len(item[0]),
        reverse=True
    ):
        pattern = rf"\b{re.escape(eng.lower())}\b"
        text = re.sub(pattern, chi, text)

    return text if text.strip() else food_name
