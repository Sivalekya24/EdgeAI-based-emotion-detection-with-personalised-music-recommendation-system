'''def get_spotify_targets(emotion):
    """
    Maps 7 human emotions to high-quality search keywords.
    Adding 'movie' and 'soundtrack' ensures you get famous film songs.
    """
    mapping = {
        "happy":    {"genre": "dance melody upbeat soundtrack pop hits"},
        "angry":    {"genre": "mass action intense fast soundtrack rock"},
        "sad":      {"genre": "sad melody acoustic soulful soundtrack"},
        "fear":     {"genre": "suspense horror bgm ambient theme soundtrack"},
        "neutral":  {"genre": "chill melody calm peaceful soundtrack"},
        "disgust":  {"genre": "dark intense heavy grunge metal thriller bgm soundtrack"},
        "surprise": {"genre": "party dance electronic energetic soundtrack"}
    }
    
    # Returns mapping for detected emotion, defaults to neutral if not found
    return mapping.get(emotion.lower(), mapping["neutral"])'''



def get_spotify_targets(emotion, language):
    """
    Maps 7 human emotions to specialized keywords based on language.
    Prevents classical music (Bach) in English while keeping Movie hits in Telugu.
    """
    lang_lower = language.lower()
    
    # 1. ENGLISH MAP (Modern Pop to block Bach/Classical)
        # 1. ENGLISH MAP (Strictly targeting individual hits)
    english_map = {
        "happy":    "billboard top 100 pop dance upbeat single 2024",
        "angry":    "modern rock aggressive intense gym energy single",
        "sad":      "top ballads soulful acoustic emotional pop single",
        "fear":     "dark modern cinematic suspense tension ambient",
        "neutral":  "chill modern pop coffee shop lo-fi vibes",
        "disgust":  "alternative heavy dark industrial modern beats",
        "surprise": "top 40 dance party electronic energetic single"
    }


    # 2. KOREAN MAP (K-Pop & K-Drama OST)
    korean_map = {
        "happy":    "k-pop dance upbeat idols bubblegum summer",
        "angry":    "k-hip-hop aggressive rap powerful performance",
        "sad":      "k-drama ost emotional ballad soulful piano",
        "fear":     "korean thriller horror movie bgm eerie ambient",
        "neutral":  "k-indie chill coffee shop acoustic relaxed",
        "disgust":  "dark k-pop intense heavy electronic industrial",
        "surprise": "k-pop party energetic dance colorful electronic"
    }

    # 3. JAPANESE MAP (J-Pop & Anime)
    japanese_map = {
        "happy":    "j-pop upbeat anime opening high energy dance",
        "angry":    "j-rock aggressive metal anime battle theme",
        "sad":      "j-pop ballad emotional anime ending soulful",
        "fear":     "japanese horror theme suspense ambient dark",
        "neutral":  "city pop japanese chill lo-fi relaxed",
        "disgust":  "japanese dark intense industrial heavy rock",
        "surprise": "j-pop party energetic dance electronic neon"
    }

    # 4. REGIONAL MAP (Telugu, Hindi, Tamil, Punjabi)
    # Keeping your original 'Movie' and 'Mass' keywords here
    regional_map = {
        "happy":    {"genre": "dance melody upbeat soundtrack pop hits"},
        "angry":    {"genre": "mass action intense fast soundtrack rock"},
        "sad":      {"genre": "sad melody acoustic soulful soundtrack"},
        "fear":     {"genre": "suspense horror bgm ambient theme soundtrack"},
        "neutral":  {"genre": "chill melody calm peaceful soundtrack"},
        "disgust":  {"genre": "dark intense heavy grunge metal thriller bgm soundtrack"},
        "surprise": {"genre": "party dance electronic energetic soundtrack"}
    }
    # Selection Logic
    if lang_lower == "english":
        selected_map = english_map
    elif lang_lower == "korean":
        selected_map = korean_map
    elif lang_lower == "japanese":
        selected_map = japanese_map
    else:
        # For Telugu, Hindi, Tamil, Punjabi
        selected_map = regional_map

    genre_string = selected_map.get(emotion.lower(), selected_map["neutral"])
    return {"genre": genre_string}
