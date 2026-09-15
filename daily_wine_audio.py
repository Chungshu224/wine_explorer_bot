"""
每日布根地雙語聽力練習腳本（edge-tts 版，固定文章庫，無需 API）
"""

import os
import random
import asyncio
from datetime import datetime

import requests
import edge_tts

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

EN_VOICE = "en-US-AriaNeural"
FR_VOICE = "fr-FR-DeniseNeural"

CONTENT = [
    {
        "topic": "Volnay",
        "en": "Volnay is a small village in Burgundy, France. It makes only red wine, from the Pinot Noir grape. People often say Volnay wines are very elegant and soft. The soil here has more limestone than nearby Pommard. Because of this, Volnay wines are usually lighter and more delicate. Many wine lovers compare Volnay to a woman: graceful and refined.",
        "fr": "Volnay est un petit village viticole situe en Bourgogne. On y produit uniquement du vin rouge, a partir du cepage Pinot Noir. Les vins de Volnay sont reputes pour leur elegance et leur finesse. Le sol y est riche en calcaire, ce qui donne des vins plus legers que ceux de Pommard, le village voisin. On dit souvent que Volnay est le village le plus feminin de la Cote de Beaune.",
        "vocab_en": ["limestone - 石灰岩", "delicate - 細緻的", "graceful - 優雅的", "refined - 精緻的"],
        "vocab_fr": ["repute pour - 以...聞名", "finesse - 細膩", "calcaire - 石灰岩", "voisin - 鄰近的"],
    },
    {
        "topic": "Pommard",
        "en": "Pommard sits right next to Volnay in Burgundy, but its wines are very different. Pommard makes powerful, firm red wines from Pinot Noir. The soil has more clay and iron than Volnay's limestone. Because of this, Pommard wines are darker, stronger, and need more years to soften. Many people call Pommard the masculine twin of gentle Volnay.",
        "fr": "Pommard est le voisin direct de Volnay, mais leurs vins sont tres differents. Pommard produit des vins rouges puissants et charpentes a partir du Pinot Noir. Le sol contient plus d'argile et de fer que celui de Volnay, plus calcaire. Ces vins sont donc plus fonces, plus tanniques, et demandent davantage de temps pour s'assouplir. On surnomme souvent Pommard le jumeau masculin du delicat Volnay.",
        "vocab_en": ["clay - 黏土", "iron - 鐵質", "firm - 結實的", "soften - 變柔和"],
        "vocab_fr": ["charpente - 結構紮實的", "argile - 黏土", "tannique - 單寧重的", "s'assouplir - 變柔順"],
    },
    {
        "topic": "Meursault",
        "en": "Meursault is famous for white wine, made from Chardonnay grapes. Unlike its neighbors, it makes almost no red wine. Meursault wines are rich, creamy, and often taste like butter or hazelnuts. Winemakers here often use oak barrels, which add warm, toasty flavors. Many people consider Meursault one of the best white wine villages in the whole world.",
        "fr": "Meursault est celebre pour ses vins blancs, produits a partir du cepage Chardonnay. Contrairement a ses voisins, le village produit tres peu de vin rouge. Les vins de Meursault sont riches, onctueux, et evoquent souvent le beurre ou la noisette. Les vignerons utilisent frequemment des futs de chene, qui apportent des aromes chaleureux et grilles. Beaucoup considerent Meursault comme l'un des meilleurs villages blancs au monde.",
        "vocab_en": ["creamy - 濃郁滑順的", "hazelnut - 榛果", "oak barrel - 橡木桶", "toasty - 烤香的"],
        "vocab_fr": ["onctueux - 濃郁滑順", "noisette - 榛果", "fut de chene - 橡木桶", "grille - 烤香的"],
    },
    {
        "topic": "Gevrey-Chambertin",
        "en": "Gevrey-Chambertin is one of the most powerful red wine villages in Burgundy. It has nine Grand Cru vineyards, more than any other village. The wines are known for deep color, strong tannins, and a long life in the bottle. Napoleon Bonaparte was said to love wine from Chambertin. Today, these wines are still considered some of the greatest in the world.",
        "fr": "Gevrey-Chambertin est l'un des villages rouges les plus puissants de Bourgogne. Il compte neuf Grands Crus, plus que n'importe quel autre village. Ses vins se distinguent par une couleur profonde, des tanins puissants, et un grand potentiel de garde. On raconte que Napoleon Bonaparte appreciait particulierement le vin de Chambertin. Aujourd'hui encore, ces vins comptent parmi les plus grands du monde entier.",
        "vocab_en": ["Grand Cru - 特級園", "tannin - 單寧", "deep color - 深色澤", "bottle age - 瓶陳能力"],
        "vocab_fr": ["potentiel de garde - 陳年潛力", "tanin - 單寧", "profond - 深沉的", "apprecier - 喜愛"],
    },
    {
        "topic": "Chablis",
        "en": "Chablis is a wine region far north of the rest of Burgundy, close to the border of Champagne. It only makes white wine from Chardonnay grapes. The soil is called Kimmeridgian, full of ancient sea fossils. This gives Chablis wine a special mineral taste, often described as flinty or like seashells. Chablis wines are usually fresh, dry, and don't use much oak.",
        "fr": "Chablis est une region viticole situee loin au nord du reste de la Bourgogne, proche de la Champagne. On y produit uniquement du vin blanc, a partir du Chardonnay. Le sol, appele kimmeridgien, est riche en fossiles marins anciens. Cela donne au vin de Chablis un gout mineral particulier, souvent decrit comme pierre a fusil ou proche du coquillage. Les vins de Chablis sont generalement frais, secs, et peu boises.",
        "vocab_en": ["fossil - 化石", "mineral - 礦物的", "flinty - 燧石味的", "seashell - 貝殼"],
        "vocab_fr": ["fossile marin - 海洋化石", "mineral - 礦物的", "pierre a fusil - 燧石味", "boise - 有橡木味的"],
    },
    {
        "topic": "Nuits-Saint-Georges",
        "en": "Nuits-Saint-Georges gives its name to the whole Cote de Nuits region. It makes almost only red wine from Pinot Noir. The wines are known for being sturdy, earthy, and full-bodied, with flavors of dark fruit and forest floor. Unlike Gevrey-Chambertin, this village has no Grand Cru vineyards, but many excellent Premier Crus. It remains a favorite among serious Burgundy collectors.",
        "fr": "Nuits-Saint-Georges donne son nom a toute la region de la Cote de Nuits. Le village produit presque exclusivement du vin rouge a partir du Pinot Noir. Ses vins sont reputes robustes, terreux, et corses, avec des notes de fruits noirs et de sous-bois. Contrairement a Gevrey-Chambertin, ce village ne possede aucun Grand Cru, mais de nombreux excellents Premiers Crus. Il reste un favori parmi les collectionneurs serieux de Bourgogne.",
        "vocab_en": ["sturdy - 結實的", "earthy - 泥土味的", "full-bodied - 酒體飽滿的", "forest floor - 森林地被物氣息"],
        "vocab_fr": ["robuste - 結實的", "terreux - 泥土味的", "corse - 酒體飽滿的", "sous-bois - 森林地被物"],
    },
    {
        "topic": "Vosne-Romanee",
        "en": "Vosne-Romanee is considered the most prestigious red wine village in all of Burgundy. It is home to Romanee-Conti, often called the most expensive wine on earth. The village has several Grand Cru vineyards known for silky texture and incredible perfume. Because production is tiny and demand is huge, prices here can reach astonishing levels. Many wine lovers see it as the peak of Pinot Noir.",
        "fr": "Vosne-Romanee est considere comme le village rouge le plus prestigieux de toute la Bourgogne. C'est ici que se trouve la Romanee-Conti, souvent qualifiee de vin le plus cher au monde. Le village compte plusieurs Grands Crus reputes pour leur texture soyeuse et leur parfum incroyable. La production y etant minuscule et la demande immense, les prix peuvent atteindre des sommets etourdissants. Beaucoup de passionnes y voient l'apogee du Pinot Noir.",
        "vocab_en": ["prestigious - 聲望崇高的", "silky - 絲滑的", "perfume - 香氣", "astonishing - 驚人的"],
        "vocab_fr": ["prestigieux - 聲望崇高的", "soyeux - 絲滑的", "etourdissant - 令人暈眩的", "apogee - 巔峰"],
    },
    {
        "topic": "Puligny-Montrachet",
        "en": "Puligny-Montrachet is often called the greatest white wine village in the world. It shares the famous Montrachet vineyard with its neighbor Chassagne-Montrachet. The wines are powerful yet elegant, combining richness with fine minerality. Unlike Meursault's buttery style, Puligny wines tend to be more structured and precise. Many sommeliers consider a top Puligny-Montrachet the ultimate expression of Chardonnay.",
        "fr": "Puligny-Montrachet est souvent considere comme le plus grand village blanc au monde. Il partage le celebre climat du Montrachet avec son voisin Chassagne-Montrachet. Ses vins sont puissants tout en restant elegants, alliant richesse et mineralite fine. Contrairement au style beurre de Meursault, les vins de Puligny sont plutot structures et precis. Beaucoup de sommeliers considerent un grand Puligny-Montrachet comme l'expression ultime du Chardonnay.",
        "vocab_en": ["minerality - 礦物感", "structured - 結構分明的", "precise - 精準的", "sommelier - 侍酒師"],
        "vocab_fr": ["mineralite - 礦物感", "structure - 結構分明的", "precis - 精準的", "allier - 結合"],
    },
    {
        "topic": "Chambolle-Musigny",
        "en": "Chambolle-Musigny is known as the most feminine and perfumed red wine village in the Cote de Nuits. Its wines are light in color but very complex, often compared to silk and flowers rather than power. The Grand Cru Musigny is especially prized for its floral, delicate character. Many people say Chambolle wines show that Pinot Noir can be both light and deeply serious.",
        "fr": "Chambolle-Musigny est considere comme le village rouge le plus feminin et parfume de la Cote de Nuits. Ses vins ont une couleur pale mais une grande complexite, souvent compares a la soie et aux fleurs plutot qu'a la puissance. Le Grand Cru Musigny est particulierement apprecie pour son caractere floral et delicat. Beaucoup disent que les vins de Chambolle prouvent que le Pinot Noir peut etre a la fois leger et profondement serieux.",
        "vocab_en": ["feminine - 陰柔的", "perfumed - 香氣濃郁的", "floral - 花香的", "delicate - 細緻的"],
        "vocab_fr": ["feminin - 陰柔的", "parfume - 香氣濃郁的", "floral - 花香的", "soie - 絲綢"],
    },
    {
        "topic": "Aloxe-Corton",
        "en": "Aloxe-Corton is unusual because it makes both excellent red and white Grand Cru wines. The red Corton is powerful and structured, while the white Corton-Charlemagne is rich and complex. Legend says Charlemagne himself once owned vines here, and asked for white wine so he wouldn't stain his beard red. Today, Corton-Charlemagne remains one of Burgundy's most respected white wines.",
        "fr": "Aloxe-Corton est un village particulier, car il produit a la fois d'excellents Grands Crus rouges et blancs. Le Corton rouge est puissant et structure, tandis que le Corton-Charlemagne blanc est riche et complexe. La legende raconte que Charlemagne lui-meme possedait des vignes ici, et demandait du vin blanc pour ne pas tacher sa barbe de rouge. Aujourd'hui, le Corton-Charlemagne reste l'un des blancs les plus respectes de Bourgogne.",
        "vocab_en": ["legend - 傳說", "stain - 弄髒", "beard - 鬍鬚", "respected - 受尊崇的"],
        "vocab_fr": ["legende - 傳說", "tacher - 弄髒", "barbe - 鬍鬚", "respecte - 受尊崇的"],
    },
    {
        "topic": "climat 分級概念",
        "en": "In Burgundy, a climat is a specific named vineyard plot with its own unique character. Even two climats right next to each other can taste very different, because of small changes in soil, slope, and sunlight. There are over 1,200 climats in Burgundy, and many are protected by UNESCO as World Heritage. This idea, that exact location shapes flavor, is central to how Burgundy wine works.",
        "fr": "En Bourgogne, un climat est une parcelle de vigne precisement nommee, avec son propre caractere unique. Meme deux climats voisins peuvent avoir un gout tres different, a cause de petites variations de sol, de pente et d'ensoleillement. La Bourgogne compte plus de 1200 climats, dont beaucoup sont proteges par l'UNESCO comme patrimoine mondial. Cette idee, que l'emplacement exact faconne le gout, est au coeur du fonctionnement du vin bourguignon.",
        "vocab_en": ["plot - 地塊", "slope - 坡度", "sunlight - 日照", "heritage - 遺產"],
        "vocab_fr": ["parcelle - 地塊", "pente - 坡度", "ensoleillement - 日照", "patrimoine - 遺產"],
    },
    {
        "topic": "Premier Cru 與 Grand Cru 的差異",
        "en": "Burgundy has a strict system for ranking vineyards. At the top are Grand Crus, the very best plots, making up only about 1% of production. Below them are Premier Crus, still excellent but slightly less prestigious. Most Burgundy wine is simple village wine, without either label. Understanding this ranking helps explain why two bottles from the same village can have very different prices.",
        "fr": "La Bourgogne possede un systeme strict de classement des vignobles. Au sommet se trouvent les Grands Crus, les meilleures parcelles, qui ne representent qu'environ 1% de la production. Juste en dessous viennent les Premiers Crus, toujours excellents mais legerement moins prestigieux. La plupart des vins de Bourgogne sont de simples vins de village, sans aucune de ces deux mentions. Comprendre ce classement explique pourquoi deux bouteilles du meme village peuvent avoir des prix tres differents.",
        "vocab_en": ["rank - 分級", "plot - 地塊", "prestigious - 有聲望的", "label - 標示"],
        "vocab_fr": ["classement - 分級系統", "parcelle - 地塊", "prestigieux - 有聲望的", "mention - 標示"],
    },
    {
        "topic": "布根地的石灰岩土壤",
        "en": "Much of Burgundy's soil sits on ancient limestone, formed millions of years ago under a shallow sea. This limestone drains water well and reflects sunlight back onto the grapes. Many winemakers believe limestone gives Burgundy wines their fresh, elegant character and bright acidity. The exact type and depth of limestone changes from one small plot to the next, helping explain Burgundy's incredible variety.",
        "fr": "Une grande partie du sol de Bourgogne repose sur du calcaire ancien, forme il y a des millions d'annees sous une mer peu profonde. Ce calcaire draine bien l'eau et reflechit la lumiere du soleil vers les raisins. Beaucoup de vignerons pensent que le calcaire donne aux vins de Bourgogne leur caractere frais, elegant, et leur belle acidite. Le type et la profondeur exacte du calcaire changent d'une petite parcelle a l'autre, ce qui explique l'incroyable diversite bourguignonne.",
        "vocab_en": ["limestone - 石灰岩", "drain - 排水", "acidity - 酸度", "variety - 多樣性"],
        "vocab_fr": ["calcaire - 石灰岩", "drainer - 排水", "acidite - 酸度", "diversite - 多樣性"],
    },
    {
        "topic": "Cote de Nuits 與 Cote de Beaune 的差異",
        "en": "Burgundy's heartland is split into two parts: the Cote de Nuits in the north and the Cote de Beaune in the south. The Cote de Nuits is famous mostly for powerful red wines, home to villages like Gevrey-Chambertin and Vosne-Romanee. The Cote de Beaune makes both excellent reds and the world's best whites, including Meursault and Puligny-Montrachet. Together, they form the legendary Golden Slope of Burgundy.",
        "fr": "Le coeur de la Bourgogne se divise en deux parties: la Cote de Nuits au nord et la Cote de Beaune au sud. La Cote de Nuits est celebre surtout pour ses vins rouges puissants, avec des villages comme Gevrey-Chambertin et Vosne-Romanee. La Cote de Beaune produit a la fois d'excellents rouges et les meilleurs blancs du monde, dont Meursault et Puligny-Montrachet. Ensemble, elles forment la legendaire Cote d'Or de Bourgogne.",
        "vocab_en": ["heartland - 核心地帶", "split - 分成", "legendary - 傳奇的", "slope - 坡地"],
        "vocab_fr": ["coeur - 核心地帶", "diviser - 分成", "legendaire - 傳奇的", "cote - 坡地"],
    },
]


def pick_content():
    return random.choice(CONTENT)


async def _synthesize_async(text, voice_name, filepath):
    communicate = edge_tts.Communicate(text, voice_name)
    await communicate.save(filepath)


def synthesize_speech(text, voice_name, filepath):
    asyncio.run(_synthesize_async(text, voice_name, filepath))
    return filepath


def send_telegram_message(text):
    url = "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN + "/sendMessage"
    r = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text})
    r.raise_for_status()


def send_telegram_audio(filepath, caption):
    url = "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN + "/sendAudio"
    with open(filepath, "rb") as f:
        r = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
            files={"audio": f},
        )
    r.raise_for_status()


def main():
    item = pick_content()

    vocab_en = "\n".join("- " + v for v in item["vocab_en"])
    vocab_fr = "\n".join("- " + v for v in item["vocab_fr"])

    message = (
        datetime.now().strftime("%Y-%m-%d") + " 每日布根地聽力：" + item["topic"] + "\n\n"
        + "EN: " + item["en"] + "\n\n生字：\n" + vocab_en + "\n\n"
        + "FR: " + item["fr"] + "\n\n生字：\n" + vocab_fr
    )
    send_telegram_message(message)

    en_file = synthesize_speech(item["en"], EN_VOICE, "/tmp/daily_en.mp3")
    fr_file = synthesize_speech(item["fr"], FR_VOICE, "/tmp/daily_fr.mp3")

    send_telegram_audio(en_file, "英文語音")
    send_telegram_audio(fr_file, "法文語音")


if __name__ == "__main__":
    main()