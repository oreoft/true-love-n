#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video Prompt - 视频生成提示词系统

使用方法：
1. 调用 get_style_matcher_prompt() 获取风格匹配的系统 prompt
2. 用 LLM 判断用户描述属于哪个风格 ID
3. 调用 get_prompt_template(style_id) 获取对应模板
4. 调用 get_prompt_generator_prompt(template, user_desc) 生成最终 prompt
"""

from typing import Optional

# ==================== 风格定义 ====================
STYLE_CATEGORIES = [
    {
        "id": "mirror_selfie_video",
        "name": "对镜自拍视频（Mirror Selfie Video）",
        "keywords": ["自拍", "镜子", "对镜", "mirror", "selfie", "韩系", "日系", "卧室", "bedroom"],
        "summary": "对镜自拍风格视频：手机拍摄感、卧室氛围、自然光线、轻微动作。",
        "best_for": ["个人展示", "穿搭分享", "日常 vlog 风格"],
        "defaults": {"aspect_ratio": "9:16", "duration": "5-8s"},
        "template_prompt": "A natural smartphone mirror selfie video of {SUBJECT}. Setting: cozy bedroom with {DECOR_ELEMENTS}. The person is standing in front of a full-length mirror, holding phone, making subtle movements like {MOVEMENTS}. Lighting: soft natural window light mixed with warm ambient light. Style: authentic phone camera look, visible natural skin texture, no heavy filters. Mood: casual, intimate, {MOOD}. Camera: slight natural hand movements, not overly stabilized.",
        "negative_prompt": "professional studio, harsh lighting, plastic skin, over-processed, unnatural poses, horror elements"
    },
    {
        "id": "product_diorama",
        "name": "产品微缩场景（Product Diorama）",
        "keywords": ["产品", "玩具", "微缩", "盒子", "展示", "product", "toy", "diorama", "miniature", "unboxing"],
        "summary": "将主体变成精致的微缩模型/玩具，放在透明展示盒中，高端产品广告风格。",
        "best_for": ["产品展示", "创意广告", "收藏品风格"],
        "defaults": {"aspect_ratio": "1:1", "duration": "5-8s"},
        "template_prompt": "A hyper-realistic product video of {SUBJECT} transformed into an ultra-detailed miniature figurine inside a clear acrylic collector toy box. The miniature is surrounded by {MINI_PROPS}. Packaging: premium clear acrylic front, matte paper backer, subtle emboss feel. Camera movement: slow 360° rotation or gentle push-in. Lighting: clean studio softbox, crisp reflections, subtle shadows. Style: luxury toy photography, product hero shot.",
        "negative_prompt": "cheap plastic look, cluttered background, harsh shadows, text/logos, watermarks"
    },
    {
        "id": "macro_photography",
        "name": "微距摄影视频（Macro Photography Video）",
        "keywords": ["微距", "特写", "macro", "closeup", "细节", "放大", "昆虫", "花", "水滴"],
        "summary": "微距摄影风格：极致细节、浅景深、微观世界的奇妙视角。",
        "best_for": ["自然细节", "产品特写", "艺术视觉"],
        "defaults": {"aspect_ratio": "16:9", "duration": "5-10s"},
        "template_prompt": "A stunning macro video of {SUBJECT}. Extreme close-up revealing intricate details: {DETAILS}. Camera movement: slow gentle drift or subtle rack focus. Depth of field: very shallow, creamy bokeh background. Lighting: {LIGHTING}. Environment: {ENVIRONMENT}. Style: photoreal macro photography, tilt-shift effect optional. Mood: mesmerizing, revealing hidden beauty.",
        "negative_prompt": "blurry subject, flat lighting, wide angle, busy background, low detail"
    },
    {
        "id": "cinematic_scene",
        "name": "电影级场景（Cinematic Scene）",
        "keywords": ["电影", "cinematic", "大片", "史诗", "epic", "dramatic", "戏剧", "电影感"],
        "summary": "电影级画面：宽银幕比例、戏剧性光影、专业运镜、强烈情绪张力。",
        "best_for": ["故事叙事", "情感表达", "高端广告"],
        "defaults": {"aspect_ratio": "21:9", "duration": "8-15s"},
        "template_prompt": "A cinematic video scene of {SUBJECT}. Composition: {COMPOSITION}. Camera movement: {CAMERA_MOVEMENT} (dolly/crane/steadicam). Lighting: {LIGHTING} with dramatic contrast, volumetric rays optional. Color grading: {COLOR_GRADE} (teal-orange/desaturated/warm vintage). Sound design hint: {SOUND_MOOD}. Aspect ratio: 2.39:1 widescreen. Style: high-end film production, shallow depth of field, lens flares optional. Mood: {MOOD}.",
        "negative_prompt": "amateur footage, shaky cam, flat lighting, over-saturated, TV look"
    },
    {
        "id": "anime_style",
        "name": "动画风格（Anime Style）",
        "keywords": ["动画", "anime", "二次元", "卡通", "cartoon", "动漫", "吉卜力", "ghibli", "漫画", "海绵宝宝", "派大星", "皮卡丘", "哆啦A梦", "蜡笔小新", "喜羊羊", "熊出没", "迪士尼"],
        "summary": "日式动画风格：手绘质感、流畅动画、标志性的动漫美学。",
        "best_for": ["创意表达", "角色动画", "奇幻场景"],
        "defaults": {"aspect_ratio": "16:9", "duration": "5-10s"},
        "template_prompt": "An anime-style animated video of {SUBJECT}. Art style: {ART_STYLE} (Studio Ghibli soft watercolor / modern sharp anime / retro 90s anime). Character design: {CHARACTER_DETAILS}. Animation: fluid movements, {ANIMATION_STYLE} (wind in hair, cloth physics, expressive gestures). Background: {BACKGROUND} with painterly details. Lighting: {LIGHTING}. Camera: {CAMERA} (static with parallax / slow pan / dynamic action shots). Mood: {MOOD}.",
        "negative_prompt": "3D CGI, photorealistic, uncanny valley, choppy animation, western cartoon style"
    },
    {
        "id": "nature_landscape",
        "name": "自然风景（Nature Landscape）",
        "keywords": ["风景", "自然", "nature", "landscape", "山脉", "大海", "海边", "海景", "森林", "日落", "sunrise", "sunset", "mountain", "ocean", "forest"],
        "summary": "自然风景视频：壮丽的自然景观、延时/慢动作、大气感光影。",
        "best_for": ["风景展示", "旅行记录", "冥想背景"],
        "defaults": {"aspect_ratio": "16:9", "duration": "10-20s"},
        "template_prompt": "A breathtaking nature video of {LOCATION}. Scene: {SCENE_DESCRIPTION}. Time: {TIME_OF_DAY}. Weather: {WEATHER}. Camera movement: {CAMERA} (slow drone flyover / timelapse / hyperlapse / static with natural movement). Natural elements: {ELEMENTS} (clouds drifting, water flowing, leaves rustling, light rays). Style: documentary nature photography, 4K clarity. Color: natural vibrant colors, no over-saturation. Sound hint: ambient nature sounds. Mood: {MOOD} (peaceful/majestic/dramatic).",
        "negative_prompt": "urban elements, people crowds, artificial structures, over-processed HDR, flat lighting"
    },
    {
        "id": "urban_street",
        "name": "城市街景（Urban Street）",
        "keywords": ["城市", "街头", "urban", "street", "city", "夜景", "霓虹", "neon", "东京", "纽约", "赛博朋克", "cyberpunk"],
        "summary": "城市街景视频：都市氛围、霓虹灯光、人流车流、现代都市感。",
        "best_for": ["城市风情", "街拍 vlog", "氛围视频"],
        "defaults": {"aspect_ratio": "16:9", "duration": "8-15s"},
        "template_prompt": "An atmospheric urban street video of {CITY/LOCATION}. Scene: {SCENE} (busy intersection / quiet alley / rooftop view / subway station). Time: {TIME} (golden hour / blue hour / night with neon). Elements: {ELEMENTS} (pedestrians, traffic, reflections on wet pavement, steam vents). Camera: {CAMERA} (walking POV / static observation / slow dolly). Style: {STYLE} (documentary / cinematic / cyberpunk aesthetic). Lighting: {LIGHTING}. Mood: {MOOD} (energetic/melancholic/mysterious).",
        "negative_prompt": "empty streets (unless intended), rural setting, poor weather visibility, shaky amateur footage"
    },
    {
        "id": "action_sports",
        "name": "运动动态（Action Sports）",
        "keywords": ["运动", "动作", "action", "sports", "跑步", "跳跃", "极限", "slow motion", "慢动作", "速度", "大战", "战斗", "打架", "fight", "battle", "对决", "PK"],
        "summary": "动态运动视频：高速动作、慢动作回放、动感张力、速度感。",
        "best_for": ["体育广告", "动作展示", "活力表达"],
        "defaults": {"aspect_ratio": "16:9", "duration": "5-10s"},
        "template_prompt": "A dynamic action video of {SUBJECT} performing {ACTION}. Speed: {SPEED} (real-time burst / slow-motion 120fps+ / speed ramping). Camera: {CAMERA} (tracking shot / POV / drone follow / static with subject motion blur). Environment: {ENVIRONMENT}. Key moment: {KEY_MOMENT} (peak action freeze, impact, launch). Lighting: {LIGHTING} (dramatic backlight / natural bright / stadium lights). Style: sports commercial quality, sharp focus on subject. Energy: high intensity, powerful, {MOOD}.",
        "negative_prompt": "static boring shot, blurry action, poor timing, flat energy, amateur quality"
    },
    {
        "id": "food_video",
        "name": "美食视频（Food Video）",
        "keywords": ["美食", "食物", "food", "cooking", "料理", "烹饪", "吃播", "甜点", "dessert", "餐厅"],
        "summary": "美食视频：诱人的食物特写、烹饪过程、质感展示、令人垂涎。",
        "best_for": ["美食广告", "烹饪展示", "餐厅宣传"],
        "defaults": {"aspect_ratio": "9:16", "duration": "8-15s"},
        "template_prompt": "A mouthwatering food video of {DISH}. Sequence: {SEQUENCE} (preparation / cooking process / plating / hero shot / eating). Close-ups: {CLOSEUPS} (sizzling, steam rising, sauce dripping, cheese pull, crispy textures). Camera: {CAMERA} (overhead / 45-degree / macro details / smooth slider movements). Lighting: {LIGHTING} (soft natural / warm restaurant / bright commercial). Style: food commercial quality, rich colors, appetizing presentation. Props: {PROPS}. Mood: {MOOD} (cozy homemade / luxury dining / casual comfort).",
        "negative_prompt": "unappetizing presentation, cold flat lighting, messy unappealing, fast food cheap look"
    },
    {
        "id": "fashion_ad",
        "name": "时尚广告（Fashion Ad）",
        "keywords": ["时尚", "fashion", "穿搭", "模特", "model", "runway", "秀场", "服装", "outfit", "lookbook"],
        "summary": "时尚广告视频：模特展示、高级质感、杂志级拍摄、风格化呈现。",
        "best_for": ["服装展示", "品牌广告", "时尚内容"],
        "defaults": {"aspect_ratio": "9:16", "duration": "8-15s"},
        "template_prompt": "A high-fashion video featuring {SUBJECT} showcasing {OUTFIT/STYLE}. Setting: {SETTING} (studio backdrop / urban location / minimalist space / luxury interior). Model movement: {MOVEMENT} (confident walk / graceful turns / static poses with subtle motion / fabric flowing). Camera: {CAMERA} (slow-motion details / full body pan / face close-up / multi-angle cuts). Lighting: {LIGHTING} (editorial studio / natural golden hour / dramatic shadows). Style: {STYLE} (high fashion editorial / street style / luxury brand aesthetic). Hair & makeup: {STYLING}. Mood: {MOOD} (powerful / elegant / edgy / romantic).",
        "negative_prompt": "cheap clothing look, poor posture, amateur modeling, unflattering angles, cluttered background"
    }
]

# ==================== 通用 Prompt ====================
GENERAL_PROMPT = {
    "id": "general",
    "name": "通用视频生成（General Video Generation）",
    "summary": "适用于无法匹配特定风格的通用视频生成请求。",
    "template_prompt": "Create a high-quality video of {SUBJECT}. Scene: {SCENE}. Action/Movement: {ACTION}. Camera: {CAMERA} (appropriate movement for the content). Lighting: {LIGHTING} (suitable for the mood). Duration: 5-10 seconds. Style: professional quality, visually engaging. Mood: {MOOD}. Ensure smooth motion, good composition, and clear focus on the main subject.",
    "negative_prompt": "low quality, blurry, shaky, poorly lit, amateur footage, jarring cuts, watermark, logo"
}


# ==================== 风格匹配器系统 Prompt ====================
def get_style_matcher_prompt() -> str:
    """
    获取用于风格匹配的系统 prompt
    让 LLM 分析用户描述并返回最匹配的风格 ID
    """
    style_list = "\n".join([
        f"- **{s['id']}**: {s['name']} - {s['summary']} (关键词: {', '.join(s['keywords'][:5])})"
        for s in STYLE_CATEGORIES
    ])
    
    return f"""你是一个视频风格分析专家。分析用户的视频生成描述，判断它最匹配下面哪个风格类别。

## 可用风格类别：
{style_list}

## 规则：
1. 仔细分析用户描述中的关键词、场景、主体、动作、风格暗示
2. 如果描述明确匹配某个风格的关键词或场景，返回该风格 ID
3. 如果描述模糊或无法匹配任何特定风格，返回 "general"
4. 只返回风格 ID，不要返回其他内容

## 输出格式：
只输出一个风格 ID，例如：cinematic_scene"""


def get_prompt_by_id(style_id: str) -> dict:
    """
    根据风格 ID 获取对应的 prompt 配置
    
    Args:
        style_id: 风格 ID
        
    Returns:
        包含 template_prompt 和 negative_prompt 的字典
    """
    for style in STYLE_CATEGORIES:
        if style["id"] == style_id:
            return {
                "id": style["id"],
                "name": style["name"],
                "template_prompt": style["template_prompt"],
                "negative_prompt": style.get("negative_prompt", ""),
                "defaults": style.get("defaults", {})
            }
    
    # 返回通用 prompt
    return {
        "id": GENERAL_PROMPT["id"],
        "name": GENERAL_PROMPT["name"],
        "template_prompt": GENERAL_PROMPT["template_prompt"],
        "negative_prompt": GENERAL_PROMPT["negative_prompt"],
        "defaults": {}
    }


def get_prompt_generator_prompt(style_id: str, user_description: str) -> str:
    """
    生成最终视频 prompt 的系统指令
    
    Args:
        style_id: 匹配到的风格 ID
        user_description: 用户的原始描述
        
    Returns:
        系统 prompt，用于让 LLM 生成最终的视频描述
    """
    style = get_prompt_by_id(style_id)
    
    return f"""你是一个专业的 AI 视频生成提示词专家。根据用户的描述，生成一个详细的英文视频生成提示词（prompt）。

## 参考模板（{style['name']}）：
{style['template_prompt']}

## 负面提示词参考：
{style['negative_prompt']}

## 视频 Prompt 特殊要求：
1. 必须描述**动态元素**：主体动作、镜头运动、环境变化
2. 考虑**时间性**：开始→发展→（可选的结束）
3. 指定**节奏感**：快/慢/变速
4. 注意**连贯性**：确保描述的动作在 5-15 秒内可以完成

## ⚠️ 版权与安全规避（重要）：
为避免视频生成被过滤，你必须对以下内容进行创意转换：
1. **版权角色**：不要直接使用版权角色名（如海绵宝宝、美国队长、皮卡丘、哆啦A梦等）
   - 转换方式：用通用描述替代，保留角色特征但不提及名字
   - 例如："海绵宝宝" → "a cheerful yellow square-shaped sea sponge character with big blue eyes"
   - 例如："美国队长" → "a heroic super soldier in a star-spangled red, white and blue suit with a round shield"
   - 例如："皮卡丘" → "a cute yellow electric mouse creature with red cheeks and lightning-bolt tail"
2. **品牌/商标**：不要提及具体品牌名，用通用描述替代
3. **真实名人**：不要使用真实名人名字，用角色类型描述替代
4. **暴力内容**：将"打架/战斗/大战"等转换为更温和的表达
   - "大战" → "epic showdown", "friendly competition", "action scene"
   - 避免血腥、伤害等描述
5. **敏感内容**：避免政治、宗教、色情等敏感话题

## 规则：
1. 输出必须是**纯英文**的视频描述
2. 将用户描述中的关键信息填充到模板的占位符中
3. 如果用户没有提供某些细节，根据风格合理补充
4. 保持模板的核心风格特征
5. 输出应该是一段连贯的描述，不需要包含占位符
6. 不要输出负面提示词，只输出正面描述
7. 长度控制在 100-300 个英文单词
8. **必须应用版权规避规则**，用创意描述替代版权内容，同时尽量满足用户意图

## 用户描述：
{user_description}

## 输出格式：
直接输出英文视频描述，不要有任何前缀或解释。"""


def get_all_style_ids() -> list[str]:
    """获取所有风格 ID 列表"""
    return [s["id"] for s in STYLE_CATEGORIES] + ["general"]


def get_style_keywords_map() -> dict[str, list[str]]:
    """获取风格 ID 到关键词的映射，用于快速匹配"""
    return {s["id"]: s["keywords"] for s in STYLE_CATEGORIES}


def quick_match_style(user_description: str) -> Optional[str]:
    """
    快速关键词匹配风格（不使用 LLM）
    
    Args:
        user_description: 用户描述
        
    Returns:
        匹配到的风格 ID，如果没有匹配返回 None
    """
    desc_lower = user_description.lower()
    
    # 计算每个风格的匹配分数
    scores = {}
    for style in STYLE_CATEGORIES:
        score = 0
        for keyword in style["keywords"]:
            if keyword.lower() in desc_lower:
                score += 1
        if score > 0:
            scores[style["id"]] = score
    
    # 返回得分最高的风格
    if scores:
        return max(scores, key=scores.get)
    
    return None
