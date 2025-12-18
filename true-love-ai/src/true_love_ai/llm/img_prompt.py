#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Prompt - 图像生成提示词系统

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
        "id": "photoreal_editorial_portrait",
        "name": "真实感人像（Editorial Hyper-Realism）",
        "keywords": ["写真", "人像", "头像", "真实", "杂志", "肖像", "editorial", "portrait", "headshot", "realistic"],
        "summary": "极致写实的商业/杂志质感人像：清晰眼神、真实皮肤纹理、摄影参数显式化。",
        "best_for": ["高写实人像", "头像/写真", "展示级真实感"],
        "defaults": {"aspect_ratio": "9:16", "resolution_hint": "4K–8K", "camera_hint": "75mm / f1.2"},
        "template_prompt": "Ultra-realistic editorial portrait of {SUBJECT}. Strict identity preservation if reference is provided. Tight head-and-shoulders close-up, pin-sharp focus on eyes, natural skin texture with visible pores, subtle under-eye shadows, realistic hair strands. Camera: DSLR look, 75mm prime lens, f/1.2, 1/200s, ISO 100, eye-level. Lighting: {LIGHTING} (e.g., golden hour soft diffusion, subtle rim light). Mood: {MOOD} (ethereal/romantic/calm). High detail, realistic color, no HDR.",
        "negative_prompt": "cartoon, anime, illustration, CGI, plastic skin, over-smoothing, beauty filter, face reshaping, uncanny, artifacts, watermark, text"
    },
    {
        "id": "natural_snapshot_selfie",
        "name": "自然清晰度 / 生活快照自拍（Raw Natural Snapshot）",
        "keywords": ["自拍", "生活照", "日常", "随拍", "快照", "selfie", "snapshot", "candid", "casual"],
        "summary": "像生活中随手拍到的一张：构图略随意、不过度精致、不修饰感强，但仍保持清晰真实。",
        "best_for": ["日常自拍", "窗边光生活照", "低修图真实感"],
        "defaults": {"aspect_ratio": "9:16", "resolution_hint": "1080p–4K", "camera_hint": "front camera / phone"},
        "template_prompt": "A candid raw smartphone selfie photo of {SUBJECT} in {SCENE}. Front camera look, slightly tilted angle, imperfect composition, casual pose. Lighting: {LIGHTING} (e.g., window light with tree-shadow patterns, Rembrandt-style soft shadow). Skin: natural, unretouched texture, realistic tone. Atmosphere: calm, everyday moment, no heavy styling.",
        "negative_prompt": "studio lighting, over-posed, heavy retouching, doll-like face, plastic skin, extreme HDR, cartoon, anime, CGI, watermark, random text"
    },
    {
        "id": "bedroom_mirror_selfie",
        "name": "卧室镜自拍（Bedroom Mirror Selfie）",
        "keywords": ["镜子", "卧室", "mirror", "bedroom", "镜像", "房间"],
        "summary": "卧室镜子自拍：手机镜像反射、床与家具道具、自然光+氛围灯。",
        "best_for": ["卧室镜自拍", "手机摄影质感"],
        "defaults": {"aspect_ratio": "9:16", "resolution_hint": "4K–8K", "camera_hint": "smartphone mirror reflection"},
        "template_prompt": "Realistic smartphone mirror selfie in a bedroom. Subject: {SUBJECT}. Pose: standing facing mirror, holding phone taking photo. Environment: unmade bed with white sheets, wooden headboard, mirror frame visible. Lighting: natural daylight from window with sheer curtains + subtle {AMBIENT_LIGHT} LED strip. Look: amateur/influencer candid, photorealistic textures, sharp on subject.",
        "negative_prompt": "heavy makeup, heavy photoshop, smooth skin, cartoon, anime, 3d render, distorted hands, bad anatomy, missing fingers, extra limbs, blurry, low quality, dark room"
    },
    {
        "id": "cute_animal_pov",
        "name": "萌宠广告视角（Cute Animal POV）",
        "keywords": ["宠物", "猫", "狗", "萌宠", "可爱", "动物", "pet", "cat", "dog", "cute", "animal", "puppy", "kitten"],
        "summary": "广角视角下的可爱动物，鼻子贴近镜头、强畸变、直视相机，广告级可爱冲击力。",
        "best_for": ["萌宠病毒传播图", "广告可爱风", "极端 POV 创意"],
        "defaults": {"aspect_ratio": "1:1", "resolution_hint": "1080p–4K", "camera_hint": "wide-angle f1.4"},
        "template_prompt": "Advertising photo, extreme POV from a low angle. An incredibly cute {ANIMAL} looking straight at camera with nose close to lens, strong wide-angle distortion, large soulful eyes, direct eye contact. Setting: {SCENE}. Soft vibrant lighting, clean ad photography, joyful mood, maximum cuteness.",
        "negative_prompt": "horror, scary mood, flat perspective, normal portrait angle, low emotion, blur, lowres, bad anatomy, watermark, text"
    },
    {
        "id": "anime_to_real",
        "name": "二次元真人化（Anime to Real）",
        "keywords": ["真人化", "二次元", "动漫", "角色", "cosplay", "anime", "manga", "character", "漫画"],
        "summary": "把漫画/动漫角色转换成逼真人类：保留发型、服装、表情与角色识别。",
        "best_for": ["角色真人化", "Cosplay 真人感", "电影感"],
        "defaults": {"aspect_ratio": "2:3", "resolution_hint": "4K+", "camera_hint": "smartphone f8–f11 deep DOF"},
        "template_prompt": "Transform {CHARACTER} into an ultra-realistic human while preserving original hairstyle, outfit, facial expression, and overall identity. Cinematic ultra-realistic fashion photography. High-resolution camera aesthetic with crisp sharp details. Deep depth of field, keep both model and environment extremely sharp. Lighting: {LIGHTING}. Scene: {SCENE} with rich environmental details.",
        "negative_prompt": "blurry background, shallow depth of field, distorted face, cartoon style, CGI, illustration, low quality, pixelation, harsh direct sunlight, overexposed"
    },
    {
        "id": "calendar_illustration",
        "name": "手绘日历插画（Calendar Illustration）",
        "keywords": ["日历", "插画", "手绘", "水彩", "calendar", "illustration", "watercolor", "打卡"],
        "summary": "竖版日历信息排版 + 可爱时尚手绘/水彩人物；白底留白充足，文字清晰可读。",
        "best_for": ["日历插画", "每日打卡海报", "节气/本地化日历卡"],
        "defaults": {"aspect_ratio": "9:16", "resolution_hint": "1440x2560+", "camera_hint": "illustration"},
        "template_prompt": "Create a cute stylish calendar illustration, vertical 9:16, fresh bright hand-drawn watercolor texture. Main character: {CHARACTER_DESC}. Background: pure white minimalist, lots of whitespace for text; character centered. Calendar typography layout: top center large date '{DATE}'. Include subtle decorative elements. Ensure all text is readable and clean; balanced whitespace; no clutter.",
        "negative_prompt": "messy layout, overlapping text, unreadable letters, random glyphs, crowded decorations, lowres, blurry text, watermark, logo"
    },
    {
        "id": "city_diorama",
        "name": "城市微缩模型（City Diorama）",
        "keywords": ["微缩", "模型", "城市", "建筑", "diorama", "miniature", "city", "architecture", "3D"],
        "summary": "城市做成圆形漂浮平台微缩模型，强 3D 体积感与模型工艺细节。",
        "best_for": ["城市建筑", "博物馆级 Diorama", "信息可视化"],
        "defaults": {"aspect_ratio": "16:9", "resolution_hint": "4K", "camera_hint": "architectural miniature photography"},
        "template_prompt": "A stunning hyper-realistic 3D render of {CITY}'s miniature model diorama on a circular floating platform. Platform shows detailed 3D miniature buildings with tangible textures. Include miniature vehicles and tiny human figures. Background: atmospheric skyline. Lighting: {LIGHTING}. Style: museum-quality diorama, tilt-shift miniature photography look, hyper-detailed model craftsmanship, 4K.",
        "negative_prompt": "flat 2D buildings, low detail, muddy textures, bad typography, unreadable text, noisy render, artifacts, watermark"
    },
    {
        "id": "child_drawing",
        "name": "儿童蜡笔画（Child Crayon Drawing）",
        "keywords": ["蜡笔", "儿童画", "童趣", "可爱", "crayon", "child", "drawing", "童真", "简笔画"],
        "summary": "像小朋友画的：蜡笔/彩铅线条、可爱不完美透视，但比真实小孩更整洁可读。",
        "best_for": ["童趣海报", "亲子风", "轻松可爱视觉"],
        "defaults": {"aspect_ratio": "1:1", "resolution_hint": "1080x1080", "camera_hint": "crayon on paper"},
        "template_prompt": "A neat colorful crayon and colored-pencil drawing of {SUBJECT}, featuring {ELEMENTS}. Slightly more polished than a typical child's drawing—clean but playful lines, uneven perspective, charming imperfections. White textured paper background.",
        "negative_prompt": "photorealistic, 3D render, glossy, perfect perspective, ultra-sharp realism, watermark, logo"
    },
    {
        "id": "isometric_scene",
        "name": "等距微缩场景（Isometric Scene）",
        "keywords": ["等距", "isometric", "俯视", "45度", "C4D", "卡通3D", "股票", "数据"],
        "summary": "45°俯视等距微缩 3D 卡通场景（Cinema4D 质感 + PBR 材质 + 温柔光影）。",
        "best_for": ["数据可视化", "品牌微缩场景", "卡通 3D 数据卡"],
        "defaults": {"aspect_ratio": "1:1", "resolution_hint": "2048x2048+", "camera_hint": "45° top-down isometric"},
        "template_prompt": "Present an exquisite miniature isometric 3D cartoon-style scene for {SUBJECT}, viewed from a 45° top-down perspective. Centerpiece: {MAIN_ELEMENT} as a tangible miniature model, surrounded by {SURROUNDING_ELEMENTS}. Rendering: Cinema 4D style, refined rounded modeling, realistic PBR materials, gentle lifelike lighting and soft shadows, clean solid-color background.",
        "negative_prompt": "flat 2D scene, messy layout, unreadable text, random letters, lowpoly, noisy render, harsh shadows, watermark, logo"
    },
    {
        "id": "weather_card",
        "name": "天气卡片（Weather Card）",
        "keywords": ["天气", "weather", "气象", "温度", "晴", "雨", "雪", "阴"],
        "summary": "45°俯视等距微缩城市场景，天气元素与建筑互动；清晰排版城市名、天气图标、日期与温度。",
        "best_for": ["天气信息卡", "城市等距插画", "轻量数据可视化"],
        "defaults": {"aspect_ratio": "9:16", "resolution_hint": "1440x2560+", "camera_hint": "45° top-down isometric"},
        "template_prompt": "Present a clear 45° top-down view of a vertical isometric miniature 3D cartoon scene of {CITY}. Iconic landmarks centered; refined textures with realistic PBR materials; gentle lifelike lighting and soft shadows. Creatively integrate weather elements for {WEATHER} into the architecture. Typography: city name '{CITY}' (large), weather icon, date '{DATE}', temperature '{TEMP}'. Clean minimalist composition with soft solid-color background.",
        "negative_prompt": "clutter, busy background, unreadable text, random glyphs, photorealistic city, harsh contrast, watermark, logo"
    },
    {
        "id": "japanese_photobook",
        "name": "日系写真集（Japanese Photobook）",
        "keywords": ["日系", "写真", "胶片", "九宫格", "日本", "photobook", "film", "japanese", "富士"],
        "summary": "高端日系写真书扫描页：九宫格叙事，胶片质感，纸张纹理、宽白边。",
        "best_for": ["写真集版式", "九宫格故事", "日系电影感胶片"],
        "defaults": {"aspect_ratio": "2:3", "resolution_hint": "4K+", "camera_hint": "photobook scan"},
        "template_prompt": "A scanned page from a high-end Japanese photobook (Shashin-shu) printed on textured matte art paper. Layout: 9-grid photo layout with wide white bottom margin. Subject: {SUBJECT} in various poses and scenes. Aesthetic: film stock Fujifilm Pro 400H (airy highlights, cyan shadows), slight vignette, visible paper texture. Grid narrative: outdoor, indoor, and intimate scenes showing progression.",
        "negative_prompt": "modern UI layout, messy grid, uneven margins, unreadable typography, random letters, plastic skin, CGI look, watermark"
    },
    {
        "id": "outdoor_lifestyle",
        "name": "户外休闲人像（Outdoor Lifestyle）",
        "keywords": ["户外", "公园", "草地", "阳光", "outdoor", "park", "lifestyle", "自然光"],
        "summary": "户外公园/绿地休闲人像：阳光自然、生活方式摄影。",
        "best_for": ["户外人像", "生活方式摄影"],
        "defaults": {"aspect_ratio": "2:3", "resolution_hint": "4K", "camera_hint": "50–85mm"},
        "template_prompt": "Modern outdoor lifestyle portrait of {SUBJECT}. Pose: {POSE}. Wardrobe: {OUTFIT}. Environment: sunny park/green area with grass and a paved path; background softly blurred. Lighting: bright natural daylight with defined highlights and natural shadows. Camera: full-frame look, 85mm f/1.8, ISO100. Sharp subject with natural textures.",
        "negative_prompt": "plastic skin, heavy retouching, distorted hands, bad anatomy, overexposed, unnatural HDR, cartoon, anime, watermark, logo"
    },
    {
        "id": "kawaii_street",
        "name": "可爱日系街拍（Kawaii Street）",
        "keywords": ["日系", "街拍", "可爱", "kawaii", "sweet", "street", "东京", "tokyo"],
        "summary": "日系街头可爱风格：阴天柔光、色彩自然偏鲜、手机拍摄感与轻微可爱滤镜。",
        "best_for": ["日系街拍", "可爱社交媒体风"],
        "defaults": {"aspect_ratio": "2:3", "resolution_hint": "1440x2160+", "camera_hint": "smartphone"},
        "template_prompt": "Cute Japanese street photo, soft overcast daylight, vibrant natural colors, smartphone photo aesthetic with gentle kawaii filters. Subject: {SUBJECT}. Outfit: {OUTFIT}. Accessories: {ACCESSORIES}. Pose: {POSE}. Setting: busy street with softly blurred background. Mood: friendly, sweet, playful.",
        "negative_prompt": "sexualized pose, explicit content, lowres, blur, distorted faces, watermark, logo"
    },
    {
        "id": "travel_poster",
        "name": "旅行海报（Travel Poster）",
        "keywords": ["旅行", "旅游", "地图", "travel", "trip", "journey", "海报", "poster", "纪念"],
        "summary": "电影级旅行回忆海报：地图模块 + 多张照片叠加 + 路径标注。",
        "best_for": ["旅行纪念海报", "路线地图海报", "多图叙事"],
        "defaults": {"aspect_ratio": "9:16", "resolution_hint": "2160x3840", "camera_hint": "poster layout"},
        "template_prompt": "Design a cinematic travel memory poster, vertical 9:16. Subject: {SUBJECT} visiting {DESTINATIONS}. Layout: Top title bar with scenic background and title '{TITLE}'. A main rectangular map module (modern style). Overlay borderless photos showing the journey. Map: numbered pins, route line, and distance labels. Bottom info bar with trip details. Clean professional layout.",
        "negative_prompt": "messy layout, unreadable map labels, random letters, hand-drawn map, watermark, logo"
    },
    {
        "id": "watercolor_landscape",
        "name": "水彩风景（Watercolor Landscape）",
        "keywords": ["水彩", "风景", "印象派", "watercolor", "landscape", "impressionist", "艺术", "油画"],
        "summary": "印象派水彩风景：松散笔触、颜色晕染、强调光与空气感。",
        "best_for": ["风景插画", "水彩明信片", "氛围感艺术图"],
        "defaults": {"aspect_ratio": "3:2", "resolution_hint": "3K+", "camera_hint": "watercolor illustration"},
        "template_prompt": "{SUBJECT} rendered as an Impressionist watercolor landscape with loose brushstrokes and soft color blending to capture light and atmosphere. Use a palette dominated by {COLORS}. Paper texture, gentle granulation, airy highlights, subtle edge blooms, calm poetic mood.",
        "negative_prompt": "photorealistic, hard edges, flat digital shading, 3D render, heavy outlines, noisy artifacts, watermark, logo"
    },
    {
        "id": "cinematic_portrait",
        "name": "电影感人像（Cinematic Portrait）",
        "keywords": ["电影", "cinematic", "戏剧", "dramatic", "海报", "电影感", "大片"],
        "summary": "电影级写实人像：戏剧光强调轮廓，强情绪张力。",
        "best_for": ["电影海报式人像", "强对比棚拍", "情绪写实头像"],
        "defaults": {"aspect_ratio": "2:3", "resolution_hint": "4K–8K", "camera_hint": "studio portrait"},
        "template_prompt": "Create an ultra-realistic cinematic portrait of {SUBJECT}. Dramatic {LIGHTING} highlights the contours of face, jawline, and neck. Background: {BACKGROUND}. Expression: {EXPRESSION}. Wardrobe: {OUTFIT}. Cinematic moody atmosphere, high detail, natural skin texture.",
        "negative_prompt": "cartoon, anime, CGI, plastic skin, over-smoothing, face reshaping, lowres, blur, watermark, logo"
    },
    {
        "id": "retro_tech",
        "name": "复古科技风（Retro Tech）",
        "keywords": ["复古", "科技", "电子", "游戏机", "retro", "tech", "vintage", "electronics", "gameboy"],
        "summary": "复古电子产品做成巨型物体，微缩工人维修场景，创意工业风。",
        "best_for": ["复古电子主题", "微缩工地场景", "创意工业风"],
        "defaults": {"aspect_ratio": "4:3", "resolution_hint": "4K+", "camera_hint": "tilt-shift macro"},
        "template_prompt": "A wide-angle, tilt-shift macro photograph of a colossal vintage {DEVICE} being overhauled by miniature technicians on a cluttered workbench. The device shows realistic wear, scratches, aged plastic. Intricate scaffolding surrounds it; tiny workers use oversized tools. Cinematic workshop lighting, hyper-detailed craftsmanship, tactile materials.",
        "negative_prompt": "flat scene, low detail, clean new plastic, unrealistic scale, noisy, watermark, logo"
    },
    {
        "id": "fantasy_scene",
        "name": "奇幻场景（Fantasy Scene）",
        "keywords": ["奇幻", "魔幻", "fantasy", "magic", "神话", "龙", "精灵", "仙境", "梦幻"],
        "summary": "奇幻/魔幻场景：魔法元素、神秘氛围、史诗级构图。",
        "best_for": ["奇幻插画", "游戏概念图", "魔幻场景"],
        "defaults": {"aspect_ratio": "16:9", "resolution_hint": "4K+", "camera_hint": "concept art"},
        "template_prompt": "A breathtaking fantasy scene depicting {SUBJECT}. Epic composition with {ELEMENTS}. Magical atmosphere with {LIGHTING_EFFECTS}. Rich details, mystical colors, dramatic sky. Style: high fantasy concept art, painterly yet detailed.",
        "negative_prompt": "modern elements, urban setting, mundane objects, low detail, flat lighting, watermark, logo"
    },
    {
        "id": "food_photography",
        "name": "美食摄影（Food Photography）",
        "keywords": ["美食", "食物", "料理", "food", "dish", "cuisine", "餐", "甜点", "蛋糕"],
        "summary": "专业美食摄影：诱人的食物特写，精心布光，强调质感和色彩。",
        "best_for": ["美食广告", "菜单图片", "社交媒体美食"],
        "defaults": {"aspect_ratio": "1:1", "resolution_hint": "4K", "camera_hint": "macro 100mm"},
        "template_prompt": "Professional food photography of {DISH}. Composition: {ANGLE} shot, styled on {SURFACE}. Garnish: {GARNISH}. Lighting: {LIGHTING} to highlight textures and colors. Steam/moisture details if applicable. Appetizing, magazine-quality, sharp focus on the dish.",
        "negative_prompt": "unappetizing, messy presentation, bad lighting, plastic-looking food, watermark, logo"
    },
    {
        "id": "product_shot",
        "name": "产品摄影（Product Shot）",
        "keywords": ["产品", "商品", "product", "commercial", "广告", "电商", "商业"],
        "summary": "专业产品摄影：干净背景、精确布光、突出产品细节。",
        "best_for": ["电商产品图", "广告素材", "产品展示"],
        "defaults": {"aspect_ratio": "1:1", "resolution_hint": "4K", "camera_hint": "product photography"},
        "template_prompt": "Professional commercial product photography of {PRODUCT}. Clean {BACKGROUND} background. Studio lighting setup: {LIGHTING}. Hero angle showing key features. Sharp focus, precise reflections, premium quality feel. Style: modern e-commerce / advertising.",
        "negative_prompt": "cluttered background, bad reflections, uneven lighting, low quality, watermark, logo"
    }
]

# ==================== 通用 Prompt ====================
GENERAL_PROMPT = {
    "id": "general",
    "name": "通用图像生成（General Image Generation）",
    "summary": "适用于无法匹配特定风格的通用图像生成请求。",
    "template_prompt": "Create a high-quality image of {SUBJECT}. {DETAILS}. Style: {STYLE}. Mood: {MOOD}. Composition: well-balanced, visually appealing. Lighting: appropriate for the scene. High resolution, professional quality, attention to detail.",
    "negative_prompt": "low quality, blurry, distorted, watermark, logo, text, artifacts, bad anatomy, ugly"
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
    
    return f"""你是一个图像风格分析专家。分析用户的图像生成描述，判断它最匹配下面哪个风格类别。

## 可用风格类别：
{style_list}

## 规则：
1. 仔细分析用户描述中的关键词、场景、主体、风格暗示
2. 如果描述明确匹配某个风格的关键词或场景，返回该风格 ID
3. 如果描述模糊或无法匹配任何特定风格，返回 "general"
4. 只返回风格 ID，不要返回其他内容

## 输出格式：
只输出一个风格 ID，例如：photoreal_editorial_portrait"""


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
    生成最终图像 prompt 的系统指令
    
    Args:
        style_id: 匹配到的风格 ID
        user_description: 用户的原始描述
        
    Returns:
        系统 prompt，用于让 LLM 生成最终的图像描述
    """
    style = get_prompt_by_id(style_id)
    
    return f"""你是一个专业的 AI 图像生成提示词专家。根据用户的描述，生成一个详细的英文图像生成提示词（prompt）。

## 参考模板（{style['name']}）：
{style['template_prompt']}

## 负面提示词参考：
{style['negative_prompt']}

## 规则：
1. 输出必须是**纯英文**的图像描述
2. 将用户描述中的关键信息填充到模板的占位符中
3. 如果用户没有提供某些细节，根据风格合理补充
4. 保持模板的核心风格特征
5. 输出应该是一段连贯的描述，不需要包含占位符
6. 不要输出负面提示词，只输出正面描述
7. 长度控制在 100-300 个英文单词

## 用户描述：
{user_description}

## 输出格式：
直接输出英文图像描述，不要有任何前缀或解释。"""


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
