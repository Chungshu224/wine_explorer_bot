"""
每日布根地雙語聽力練習腳本（edge-tts 版，難度漸進 + 小測驗）
"""

import os
import asyncio
from datetime import date

import requests
import edge_tts

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

EN_VOICE = "en-US-AriaNeural"
FR_VOICE = "fr-FR-DeniseNeural"

START_DATE = date(2026, 9, 16)

CONTENT = [
    {
        "topic": "Chablis",
        "en": "Chablis is a wine region far north of the rest of Burgundy, close to the border of Champagne. It only makes white wine from Chardonnay grapes. The soil is called Kimmeridgian, full of ancient sea fossils. This gives Chablis wine a special mineral taste, often described as flinty or like seashells. Chablis wines are usually fresh, dry, and don't use much oak.",
        "fr": "Chablis est une region viticole situee loin au nord du reste de la Bourgogne, proche de la Champagne. On y produit uniquement du vin blanc, a partir du Chardonnay. Le sol, appele kimmeridgien, est riche en fossiles marins anciens. Cela donne au vin de Chablis un gout mineral particulier, souvent decrit comme pierre a fusil ou proche du coquillage. Les vins de Chablis sont generalement frais, secs, et peu boises.",
        "vocab_en": ["fossil - 化石", "mineral - 礦物的", "flinty - 燧石味的", "seashell - 貝殼"],
        "vocab_fr": ["fossile marin - 海洋化石", "mineral - 礦物的", "pierre a fusil - 燧石味", "boise - 有橡木味的"],
        "quiz_en": "What grape does Chablis use?",
        "quiz_fr": "Quel cepage utilise Chablis?",
        "answer": "Chardonnay",
    },
    {
        "topic": "Volnay",
        "en": "Volnay is a small village in Burgundy, France. It makes only red wine, from the Pinot Noir grape. People often say Volnay wines are very elegant and soft. The soil here has more limestone than nearby Pommard. Because of this, Volnay wines are usually lighter and more delicate. Many wine lovers compare Volnay to a woman: graceful and refined.",
        "fr": "Volnay est un petit village viticole situe en Bourgogne. On y produit uniquement du vin rouge, a partir du cepage Pinot Noir. Les vins de Volnay sont reputes pour leur elegance et leur finesse. Le sol y est riche en calcaire, ce qui donne des vins plus legers que ceux de Pommard, le village voisin. On dit souvent que Volnay est le village le plus feminin de la Cote de Beaune.",
        "vocab_en": ["limestone - 石灰岩", "delicate - 細緻的", "graceful - 優雅的", "refined - 精緻的"],
        "vocab_fr": ["repute pour - 以...聞名", "finesse - 細膩", "calcaire - 石灰岩", "voisin - 鄰近的"],
        "quiz_en": "Which grape does Volnay use?",
        "quiz_fr": "Quel cepage utilise Volnay?",
        "answer": "Pinot Noir",
    },
    {
        "topic": "Pommard",
        "en": "Pommard sits right next to Volnay in Burgundy, but its wines are very different. Pommard makes powerful, firm red wines from Pinot Noir. The soil has more clay and iron than Volnay's limestone. Because of this, Pommard wines are darker, stronger, and need more years to soften. Many people call Pommard the masculine twin of gentle Volnay.",
        "fr": "Pommard est le voisin direct de Volnay, mais leurs vins sont tres differents. Pommard produit des vins rouges puissants et charpentes a partir du Pinot Noir. Le sol contient plus d'argile et de fer que celui de Volnay, plus calcaire. Ces vins sont donc plus fonces, plus tanniques, et demandent davantage de temps pour s'assouplir. On surnomme souvent Pommard le jumeau masculin du delicat Volnay.",
        "vocab_en": ["clay - 黏土", "iron - 鐵質", "firm - 結實的", "soften - 變柔和"],
        "vocab_fr": ["charpente - 結構紮實的", "argile - 黏土", "tannique - 單寧重的", "s'assouplir - 變柔順"],
        "quiz_en": "Which village is Pommard next to?",
        "quiz_fr": "De quel village Pommard est-il voisin?",
        "answer": "Volnay",
    },
    {
        "topic": "Meursault",
        "en": "Meursault is famous for white wine, made from Chardonnay grapes. Unlike its neighbors, it makes almost no red wine. Meursault wines are rich, creamy, and often taste like butter or hazelnuts. Winemakers here often use oak barrels, which add warm, toasty flavors. Many people consider Meursault one of the best white wine villages in the whole world.",
        "fr": "Meursault est celebre pour ses vins blancs, produits a partir du cepage Chardonnay. Contrairement a ses voisins, le village produit tres peu de vin rouge. Les vins de Meursault sont riches, onctueux, et evoquent souvent le beurre ou la noisette. Les vignerons utilisent frequemment des futs de chene, qui apportent des aromes chaleureux et grilles. Beaucoup considerent Meursault comme l'un des meilleurs villages blancs au monde.",
        "vocab_en": ["creamy - 濃郁滑順的", "hazelnut - 榛果", "oak barrel - 橡木桶", "toasty - 烤香的"],
        "vocab_fr": ["onctueux - 濃郁滑順", "noisette - 榛果", "fut de chene - 橡木桶", "grille - 烤香的"],
        "quiz_en": "What flavor is Meursault often compared to?",
        "quiz_fr": "A quel arome compare-t-on souvent Meursault?",
        "answer": "Butter or hazelnuts / Beurre ou noisette",
    },
    {
        "topic": "Chambolle-Musigny",
        "en": "Chambolle-Musigny is known as the most feminine and perfumed red wine village in the Cote de Nuits. Its wines are light in color but very complex, often compared to silk and flowers rather than power. The Grand Cru Musigny is especially prized for its floral, delicate character. Many people say Chambolle wines show that Pinot Noir can be both light and deeply serious.",
        "fr": "Chambolle-Musigny est considere comme le village rouge le plus feminin et parfume de la Cote de Nuits. Ses vins ont une couleur pale mais une grande complexite, souvent compares a la soie et aux fleurs plutot qu'a la puissance. Le Grand Cru Musigny est particulierement apprecie pour son caractere floral et delicat. Beaucoup disent que les vins de Chambolle prouvent que le Pinot Noir peut etre a la fois leger et profondement serieux.",
        "vocab_en": ["feminine - 陰柔的", "perfumed - 香氣濃郁的", "floral - 花香的", "delicate - 細緻的"],
        "vocab_fr": ["feminin - 陰柔的", "parfume - 香氣濃郁的", "floral - 花香的", "soie - 絲綢"],
        "quiz_en": "What is Chambolle-Musigny's Grand Cru called?",
        "quiz_fr": "Comment s'appelle le Grand Cru de Chambolle-Musigny?",
        "answer": "Musigny",
    },
    {
        "topic": "Nuits-Saint-Georges",
        "en": "Nuits-Saint-Georges gives its name to the whole Cote de Nuits region. It makes almost only red wine from Pinot Noir. The wines are known for being sturdy, earthy, and full-bodied, with flavors of dark fruit and forest floor. Unlike Gevrey-Chambertin, this village has no Grand Cru vineyards, but many excellent Premier Crus. It remains a favorite among serious Burgundy collectors.",
        "fr": "Nuits-Saint-Georges donne son nom a toute la region de la Cote de Nuits. Le village produit presque exclusivement du vin rouge a partir du Pinot Noir. Ses vins sont reputes robustes, terreux, et corses, avec des notes de fruits noirs et de sous-bois. Contrairement a Gevrey-Chambertin, ce village ne possede aucun Grand Cru, mais de nombreux excellents Premiers Crus. Il reste un favori parmi les collectionneurs serieux de Bourgogne.",
        "vocab_en": ["sturdy - 結實的", "earthy - 泥土味的", "full-bodied - 酒體飽滿的", "forest floor - 森林地被物氣息"],
        "vocab_fr": ["robuste - 結實的", "terreux - 泥土味的", "corse - 酒體飽滿的", "sous-bois - 森林地被物"],
        "quiz_en": "Does Nuits-Saint-Georges have any Grand Cru vineyards?",
        "quiz_fr": "Nuits-Saint-Georges possede-t-il des Grands Crus?",
        "answer": "No / Non",
    },
    {
        "topic": "Gevrey-Chambertin",
        "en": "Gevrey-Chambertin is one of the most powerful red wine villages in Burgundy. It has nine Grand Cru vineyards, more than any other village. The wines are known for deep color, strong tannins, and a long life in the bottle. Napoleon Bonaparte was said to love wine from Chambertin. Today, these wines are still considered some of the greatest in the world.",
        "fr": "Gevrey-Chambertin est l'un des villages rouges les plus puissants de Bourgogne. Il compte neuf Grands Crus, plus que n'importe quel autre village. Ses vins se distinguent par une couleur profonde, des tanins puissants, et un grand potentiel de garde. On raconte que Napoleon Bonaparte appreciait particulierement le vin de Chambertin. Aujourd'hui encore, ces vins comptent parmi les plus grands du monde entier.",
        "vocab_en": ["Grand Cru - 特級園", "tannin - 單寧", "deep color - 深色澤", "bottle age - 瓶陳能力"],
        "vocab_fr": ["potentiel de garde - 陳年潛力", "tanin - 單寧", "profond - 深沉的", "apprecier - 喜愛"],
        "quiz_en": "How many Grand Cru vineyards does Gevrey-Chambertin have?",
        "quiz_fr": "Combien de Grands Crus compte Gevrey-Chambertin?",
        "answer": "Nine / Neuf",
    },
    {
        "topic": "Aloxe-Corton",
        "en": "Aloxe-Corton is unusual because it makes both excellent red and white Grand Cru wines. The red Corton is powerful and structured, while the white Corton-Charlemagne is rich and complex. Legend says Charlemagne himself once owned vines here, and asked for white wine so he wouldn't stain his beard red. Today, Corton-Charlemagne remains one of Burgundy's most respected white wines.",
        "fr": "Aloxe-Corton est un village particulier, car il produit a la fois d'excellents Grands Crus rouges et blancs. Le Corton rouge est puissant et structure, tandis que le Corton-Charlemagne blanc est riche et complexe. La legende raconte que Charlemagne lui-meme possedait des vignes ici, et demandait du vin blanc pour ne pas tacher sa barbe de rouge. Aujourd'hui, le Corton-Charlemagne reste l'un des blancs les plus respectes de Bourgogne.",
        "vocab_en": ["legend - 傳說", "stain - 弄髒", "beard - 鬍鬚", "respected - 受尊崇的"],
        "vocab_fr": ["legende - 傳說", "tacher - 弄髒", "barbe - 鬍鬚", "respecte - 受尊崇的"],
        "quiz_en": "Who is said to have owned vines in Aloxe-Corton?",
        "quiz_fr": "Qui aurait possede des vignes a Aloxe-Corton?",
        "answer": "Charlemagne",
    },
    {
        "topic": "Puligny-Montrachet",
        "en": "Puligny-Montrachet is often called the greatest white wine village in the world. It shares the famous Montrachet vineyard with its neighbor Chassagne-Montrachet. The wines are powerful yet elegant, combining richness with fine minerality. Unlike Meursault's buttery style, Puligny wines tend to be more structured and precise. Many sommeliers consider a top Puligny-Montrachet the ultimate expression of Chardonnay.",
        "fr": "Puligny-Montrachet est souvent considere comme le plus grand village blanc au monde. Il partage le celebre climat du Montrachet avec son voisin Chassagne-Montrachet. Ses vins sont puissants tout en restant elegants, alliant richesse et mineralite fine. Contrairement au style beurre de Meursault, les vins de Puligny sont plutot structures et precis. Beaucoup de sommeliers considerent un grand Puligny-Montrachet comme l'expression ultime du Chardonnay.",
        "vocab_en": ["minerality - 礦物感", "structured - 結構分明的", "precise - 精準的", "sommelier - 侍酒師"],
        "vocab_fr": ["mineralite - 礦物感", "structure - 結構分明的", "precis - 精準的", "allier - 結合"],
        "quiz_en": "Which village shares the Montrachet vineyard with Puligny?",
        "quiz_fr": "Quel village partage le climat du Montrachet avec Puligny?",
        "answer": "Chassagne-Montrachet",
    },
    {
        "topic": "Vosne-Romanee",
        "en": "Vosne-Romanee is considered the most prestigious red wine village in all of Burgundy. It is home to Romanee-Conti, often called the most expensive wine on earth. The village has several Grand Cru vineyards known for silky texture and incredible perfume. Because production is tiny and demand is huge, prices here can reach astonishing levels. Many wine lovers see it as the peak of Pinot Noir.",
        "fr": "Vosne-Romanee est considere comme le village rouge le plus prestigieux de toute la Bourgogne. C'est ici que se trouve la Romanee-Conti, souvent qualifiee de vin le plus cher au monde. Le village compte plusieurs Grands Crus reputes pour leur texture soyeuse et leur parfum incroyable. La production y etant minuscule et la demande immense, les prix peuvent atteindre des sommets etourdissants. Beaucoup de passionnes y voient l'apogee du Pinot Noir.",
        "vocab_en": ["prestigious - 聲望崇高的", "silky - 絲滑的", "perfume - 香氣", "astonishing - 驚人的"],
        "vocab_fr": ["prestigieux - 聲望崇高的", "soyeux - 絲滑的", "etourdissant - 令人暈眩的", "apogee - 巔峰"],
        "quiz_en": "What is often called the most expensive wine on earth?",
        "quiz_fr": "Quel vin est souvent qualifie de plus cher au monde?",
        "answer": "Romanee-Conti",
    },
    {
        "topic": "climat 分級概念",
        "en": "In Burgundy, a climat is a specific named vineyard plot with its own unique character. Even two climats right next to each other can taste very different, because of small changes in soil, slope, and sunlight. There are over 1,200 climats in Burgundy, and many are protected by UNESCO as World Heritage. This idea, that exact location shapes flavor, is central to how Burgundy wine works.",
        "fr": "En Bourgogne, un climat est une parcelle de vigne precisement nommee, avec son propre caractere unique. Meme deux climats voisins peuvent avoir un gout tres different, a cause de petites variations de sol, de pente et d'ensoleillement. La Bourgogne compte plus de 1200 climats, dont beaucoup sont proteges par l'UNESCO comme patrimoine mondial. Cette idee, que l'emplacement exact faconne le gout, est au coeur du fonctionnement du vin bourguignon.",
        "vocab_en": ["plot - 地塊", "slope - 坡度", "sunlight - 日照", "heritage - 遺產"],
        "vocab_fr": ["parcelle - 地塊", "pente - 坡度", "ensoleillement - 日照", "patrimoine - 遺產"],
        "quiz_en": "About how many climats does Burgundy have?",
        "quiz_fr": "Combien de climats compte environ la Bourgogne?",
        "answer": "Over 1,200 / Plus de 1200",
    },
    {
        "topic": "Premier Cru 與 Grand Cru 的差異",
        "en": "Burgundy has a strict system for ranking vineyards. At the top are Grand Crus, the very best plots, making up only about 1% of production. Below them are Premier Crus, still excellent but slightly less prestigious. Most Burgundy wine is simple village wine, without either label. Understanding this ranking helps explain why two bottles from the same village can have very different prices.",
        "fr": "La Bourgogne possede un systeme strict de classement des vignobles. Au sommet se trouvent les Grands Crus, les meilleures parcelles, qui ne representent qu'environ 1% de la production. Juste en dessous viennent les Premiers Crus, toujours excellents mais legerement moins prestigieux. La plupart des vins de Bourgogne sont de simples vins de village, sans aucune de ces deux mentions. Comprendre ce classement explique pourquoi deux bouteilles du meme village peuvent avoir des prix tres differents.",
        "vocab_en": ["rank - 分級", "plot - 地塊", "prestigious - 有聲望的", "label - 標示"],
        "vocab_fr": ["classement - 分級系統", "parcelle - 地塊", "prestigieux - 有聲望的", "mention - 標示"],
        "quiz_en": "About what percent of Burgundy production is Grand Cru?",
        "quiz_fr": "Environ quel pourcentage de la production est Grand Cru?",
        "answer": "About 1% / Environ 1%",
    },
    {
        "topic": "布根地的石灰岩土壤",
        "en": "Much of Burgundy's soil sits on ancient limestone, formed millions of years ago under a shallow sea. This limestone drains water well and reflects sunlight back onto the grapes. Many winemakers believe limestone gives Burgundy wines their fresh, elegant character and bright acidity. The exact type and depth of limestone changes from one small plot to the next, helping explain Burgundy's incredible variety.",
        "fr": "Une grande partie du sol de Bourgogne repose sur du calcaire ancien, forme il y a des millions d'annees sous une mer peu profonde. Ce calcaire draine bien l'eau et reflechit la lumiere du soleil vers les raisins. Beaucoup de vignerons pensent que le calcaire donne aux vins de Bourgogne leur caractere frais, elegant, et leur belle acidite. Le type et la profondeur exacte du calcaire changent d'une petite parcelle a l'autre, ce qui explique l'incroyable diversite bourguignonne.",
        "vocab_en": ["limestone - 石灰岩", "drain - 排水", "acidity - 酸度", "variety - 多樣性"],
        "vocab_fr": ["calcaire - 石灰岩", "drainer - 排水", "acidite - 酸度", "diversite - 多樣性"],
        "quiz_en": "What kind of ancient environment formed Burgundy's limestone?",
        "quiz_fr": "Sous quel environnement ancien s'est forme le calcaire de Bourgogne?",
        "answer": "A shallow sea / Une mer peu profonde",
    },
    {
        "topic": "Cote de Nuits 與 Cote de Beaune 的差異",
        "en": "Burgundy's heartland is split into two parts: the Cote de Nuits in the north and the Cote de Beaune in the south. The Cote de Nuits is famous mostly for powerful red wines, home to villages like Gevrey-Chambertin and Vosne-Romanee. The Cote de Beaune makes both excellent reds and the world's best whites, including Meursault and Puligny-Montrachet. Together, they form the legendary Golden Slope of Burgundy.",
        "fr": "Le coeur de la Bourgogne se divise en deux parties: la Cote de Nuits au nord et la Cote de Beaune au sud. La Cote de Nuits est celebre surtout pour ses vins rouges puissants, avec des villages comme Gevrey-Chambertin et Vosne-Romanee. La Cote de Beaune produit a la fois d'excellents rouges et les meilleurs blancs du monde, dont Meursault et Puligny-Montrachet. Ensemble, elles forment la legendaire Cote d'Or de Bourgogne.",
        "vocab_en": ["heartland - 核心地帶", "split - 分成", "legendary - 傳奇的", "slope - 坡地"],
        "vocab_fr": ["coeur - 核心地帶", "diviser - 分成", "legendaire - 傳奇的", "cote - 坡地"],
        "quiz_en": "What do the Cote de Nuits and Cote de Beaune together form?",
        "quiz_fr": "Que forment ensemble la Cote de Nuits et la Cote de Beaune?",
        "answer": "The Golden Slope / La Cote d'Or",
    },
    {
        "topic": "Mosel (德國)",
        "en": "The Mosel is a river valley in Germany, famous for Riesling. The vineyards are on very steep slopes, and the soil is full of grey slate. The slate keeps the heat of the sun, which helps the grapes ripen in a cold climate. Mosel wines are light, with low alcohol, high acidity, and flavors of green apple and peach. They can be dry, off-dry, or sweet.",
        "fr": "La Moselle allemande est une vallee fluviale celebre pour le Riesling. Les vignes poussent sur des pentes tres raides, et le sol est plein d'ardoise grise. L'ardoise garde la chaleur du soleil, ce qui aide les raisins a murir sous un climat froid. Les vins de la Moselle sont legers, avec peu d'alcool, une forte acidite et des aromes de pomme verte et de peche. Ils peuvent etre secs, demi-secs ou doux.",
        "vocab_en": ["slate - 板岩", "steep - 陡峭的", "ripen - 成熟", "off-dry - 微甜的"],
        "vocab_fr": ["ardoise - 板岩", "raide - 陡峭的", "murir - 成熟", "demi-sec - 微甜的"],
        "quiz_en": "What type of soil is common in the Mosel?",
        "quiz_fr": "Quel type de sol est courant en Moselle?",
        "answer": "Slate / Ardoise",
    },
    {
        "topic": "Rioja (西班牙)",
        "en": "Rioja is the most famous wine region in Spain. Its main red grape is Tempranillo, often blended with Garnacha. Rioja wines are known for long aging in oak barrels, often American oak, which adds flavors of vanilla and coconut. The labels show the aging level: Crianza, Reserva, and Gran Reserva. Gran Reserva wines are aged the longest.",
        "fr": "La Rioja est la region viticole la plus celebre d'Espagne. Son principal cepage rouge est le Tempranillo, souvent assemble avec le Garnacha. Les vins de Rioja sont connus pour leur long elevage en futs de chene, souvent americain, qui apporte des aromes de vanille et de noix de coco. Les etiquettes indiquent le niveau de vieillissement: Crianza, Reserva et Gran Reserva. Les Gran Reserva sont ceux qui vieillissent le plus longtemps.",
        "vocab_en": ["aging - 陳年熟成", "oak barrel - 橡木桶", "vanilla - 香草", "coconut - 椰子"],
        "vocab_fr": ["elevage - 熟成", "fut de chene - 橡木桶", "vanille - 香草", "noix de coco - 椰子"],
        "quiz_en": "Which Rioja level is aged the longest?",
        "quiz_fr": "Quel niveau de Rioja vieillit le plus longtemps?",
        "answer": "Gran Reserva",
    },
    {
        "topic": "Douro 與波特酒 (葡萄牙)",
        "en": "Port is a sweet, strong wine from the Douro Valley in Portugal. It is a fortified wine. During fermentation, producers add grape spirit to the wine. This stops the fermentation early, so a lot of natural sugar stays in the wine, and the alcohol becomes higher. Port is then aged in cellars in the city of Vila Nova de Gaia, near the sea.",
        "fr": "Le Porto est un vin doux et fort de la vallee du Douro, au Portugal. C'est un vin muté. Pendant la fermentation, les producteurs ajoutent de l'alcool de raisin au vin. Cela arrete la fermentation plus tot, donc beaucoup de sucre naturel reste dans le vin, et le degre d'alcool augmente. Le Porto vieillit ensuite dans des caves de la ville de Vila Nova de Gaia, pres de la mer.",
        "vocab_en": ["fortified - 加烈的", "spirit - 烈酒", "sugar - 糖", "cellar - 酒窖"],
        "vocab_fr": ["mute - 加烈的", "alcool de raisin - 葡萄烈酒", "sucre - 糖", "cave - 酒窖"],
        "quiz_en": "What do producers add to make Port?",
        "quiz_fr": "Qu'ajoutent les producteurs pour faire le Porto?",
        "answer": "Grape spirit / De l'alcool de raisin",
    },
    {
        "topic": "Napa Valley (美國)",
        "en": "Napa Valley is the most famous wine region in the United States. It is in California, north of San Francisco. The valley is warm and sunny, and Cabernet Sauvignon grows very well here. The wines are rich and full of dark fruit. In 1976, Napa wines beat famous French wines in a blind tasting in Paris. This event is called the Judgment of Paris.",
        "fr": "La Napa Valley est la region viticole la plus celebre des Etats-Unis. Elle se trouve en Californie, au nord de San Francisco. La vallee est chaude et ensoleillee, et le Cabernet Sauvignon y pousse tres bien. Les vins sont riches et pleins de fruits noirs. En 1976, des vins de Napa ont battu de celebres vins francais lors d'une degustation a l'aveugle a Paris. Cet evenement s'appelle le Jugement de Paris.",
        "vocab_en": ["blind tasting - 盲品", "dark fruit - 黑色水果", "valley - 山谷", "rich - 濃郁的"],
        "vocab_fr": ["degustation a l'aveugle - 盲品", "fruits noirs - 黑色水果", "vallee - 山谷", "riche - 濃郁的"],
        "quiz_en": "In what year was the Judgment of Paris?",
        "quiz_fr": "En quelle annee a eu lieu le Jugement de Paris?",
        "answer": "1976",
    },
    {
        "topic": "Barossa Valley (澳洲)",
        "en": "Barossa Valley is a famous wine region in South Australia. It is best known for Shiraz, a rich red wine with flavors of blackberry, pepper, and chocolate. The region is warm and dry. Some vineyards have very old vines, more than one hundred years old. Wines from old vines give small amounts of grapes, but the flavors are deep and concentrated.",
        "fr": "La Barossa Valley est une region viticole celebre du sud de l'Australie. Elle est surtout connue pour la Shiraz, un vin rouge riche aux aromes de mure, de poivre et de chocolat. La region est chaude et seche. Certains vignobles ont de tres vieilles vignes, de plus de cent ans. Les vieilles vignes donnent peu de raisins, mais les aromes sont profonds et concentres.",
        "vocab_en": ["blackberry - 黑莓", "pepper - 胡椒", "old vines - 老藤", "concentrated - 濃縮的"],
        "vocab_fr": ["mure - 黑莓", "poivre - 胡椒", "vieilles vignes - 老藤", "concentre - 濃縮的"],
        "quiz_en": "Which grape is Barossa Valley best known for?",
        "quiz_fr": "Pour quel cepage la Barossa Valley est-elle surtout connue?",
        "answer": "Shiraz",
    },
    {
        "topic": "Mendoza (阿根廷)",
        "en": "Mendoza is the largest wine region in Argentina. It sits at the foot of the Andes mountains, and the vineyards are very high, often more than nine hundred meters above sea level. The air is dry and there is almost no rain, so farmers use water from melting snow in the mountains. The most famous grape here is Malbec, which makes dark, soft, fruity red wines.",
        "fr": "Mendoza est la plus grande region viticole d'Argentine. Elle se trouve au pied de la cordillere des Andes, et les vignes sont tres hautes, souvent a plus de neuf cents metres d'altitude. L'air est sec et il ne pleut presque pas, donc les agriculteurs utilisent l'eau de la fonte des neiges des montagnes. Le cepage le plus celebre ici est le Malbec, qui donne des vins rouges sombres, souples et fruites.",
        "vocab_en": ["altitude - 海拔", "melting snow - 融雪", "irrigation - 灌溉", "fruity - 果香豐富的"],
        "vocab_fr": ["altitude - 海拔", "fonte des neiges - 融雪", "irrigation - 灌溉", "fruite - 果香豐富的"],
        "quiz_en": "Where does the water for Mendoza vineyards come from?",
        "quiz_fr": "D'ou vient l'eau des vignobles de Mendoza?",
        "answer": "Melting snow from the Andes / La fonte des neiges des Andes",
    },
    {
        "topic": "Marlborough (紐西蘭)",
        "en": "Marlborough is the largest wine region in New Zealand, at the top of the South Island. It is famous for Sauvignon Blanc. The days are sunny and the nights are cool, which keeps the acidity high. The wines are very aromatic, with flavors of passion fruit, lime, and fresh-cut grass. Marlborough Sauvignon Blanc became popular around the world in the 1980s.",
        "fr": "Marlborough est la plus grande region viticole de Nouvelle-Zelande, tout en haut de l'ile du Sud. Elle est celebre pour son Sauvignon Blanc. Les jours sont ensoleilles et les nuits sont fraiches, ce qui garde une acidite elevee. Les vins sont tres aromatiques, avec des aromes de fruit de la passion, de citron vert et d'herbe fraiche coupee. Le Sauvignon Blanc de Marlborough est devenu populaire dans le monde entier dans les annees 1980.",
        "vocab_en": ["aromatic - 香氣豐富的", "passion fruit - 百香果", "lime - 萊姆", "cool nights - 涼爽的夜晚"],
        "vocab_fr": ["aromatique - 香氣豐富的", "fruit de la passion - 百香果", "citron vert - 萊姆", "nuits fraiches - 涼爽的夜晚"],
        "quiz_en": "On which island is Marlborough?",
        "quiz_fr": "Sur quelle ile se trouve Marlborough?",
        "answer": "The South Island / L'ile du Sud",
    },
    {
        "topic": "Chianti Classico (義大利)",
        "en": "Chianti Classico is a famous red wine from Tuscany, in central Italy. Its main grape is Sangiovese, which gives high acidity, firm tannins, and flavors of red cherry. The bottles carry a black rooster on the neck. This symbol shows that the wine comes from the historic heart of the region. Chianti Classico goes very well with tomato dishes and grilled meat.",
        "fr": "Le Chianti Classico est un celebre vin rouge de Toscane, dans le centre de l'Italie. Son principal cepage est le Sangiovese, qui donne une forte acidite, des tanins fermes et des aromes de cerise rouge. Les bouteilles portent un coq noir sur le col. Ce symbole montre que le vin vient du coeur historique de la region. Le Chianti Classico s'accorde tres bien avec les plats a la tomate et les viandes grillees.",
        "vocab_en": ["rooster - 公雞", "grilled - 燒烤的", "red cherry - 紅櫻桃", "symbol - 標誌"],
        "vocab_fr": ["coq - 公雞", "grille - 燒烤的", "cerise rouge - 紅櫻桃", "symbole - 標誌"],
        "quiz_en": "What symbol is on a Chianti Classico bottle?",
        "quiz_fr": "Quel symbole figure sur une bouteille de Chianti Classico?",
        "answer": "A black rooster / Un coq noir",
    },
    {
        "topic": "Bordeaux 左岸與右岸",
        "en": "Bordeaux is split by two rivers, the Garonne and the Dordogne, which meet in the Gironde estuary. The Left Bank has gravel soils, and its wines are mostly Cabernet Sauvignon, which is firm and long-lived. The Right Bank has more clay and limestone, and Merlot is the main grape, making softer, rounder wines. Most Bordeaux reds are blends, not single grape wines.",
        "fr": "Bordeaux est divise par deux fleuves, la Garonne et la Dordogne, qui se rejoignent dans l'estuaire de la Gironde. La Rive Gauche a des sols de graves, et ses vins sont surtout a base de Cabernet Sauvignon, structure et apte a la garde. La Rive Droite a plus d'argile et de calcaire, et le Merlot y domine, donnant des vins plus souples et plus ronds. La plupart des rouges de Bordeaux sont des assemblages, pas des vins d'un seul cepage.",
        "vocab_en": ["gravel - 礫石", "estuary - 河口", "blend - 調配/混釀", "long-lived - 耐久存的"],
        "vocab_fr": ["graves - 礫石土", "estuaire - 河口", "assemblage - 調配/混釀", "apte a la garde - 適合陳年"],
        "quiz_en": "Which grape is the main grape on the Right Bank?",
        "quiz_fr": "Quel cepage domine sur la Rive Droite?",
        "answer": "Merlot",
    },
    {
        "topic": "Pauillac",
        "en": "Pauillac is the most famous village of the Medoc, on the Left Bank of Bordeaux. Its wines are powerful and full of Cabernet Sauvignon, with flavors of blackcurrant and cedar. In the famous 1855 classification, five estates were named First Growths. Three of those five are in Pauillac: Lafite Rothschild, Latour, and Mouton Rothschild.",
        "fr": "Pauillac est le village le plus celebre du Medoc, sur la Rive Gauche de Bordeaux. Ses vins sont puissants et riches en Cabernet Sauvignon, avec des aromes de cassis et de cedre. Dans le celebre classement de 1855, cinq chateaux ont ete nommes Premiers Crus Classes. Trois de ces cinq sont a Pauillac: Lafite Rothschild, Latour et Mouton Rothschild.",
        "vocab_en": ["blackcurrant - 黑醋栗", "cedar - 雪松", "classification - 分級制度", "estate - 酒莊"],
        "vocab_fr": ["cassis - 黑醋栗", "cedre - 雪松", "classement - 分級制度", "chateau - 酒莊"],
        "quiz_en": "How many of the five First Growths are in Pauillac?",
        "quiz_fr": "Combien des cinq Premiers Crus Classes sont a Pauillac?",
        "answer": "Three / Trois",
    },
    {
        "topic": "Sauternes",
        "en": "Sauternes is a sweet white wine from Bordeaux. It is made mainly from Semillon grapes. In autumn, morning mist from the small Ciron river helps a fungus called noble rot grow on the grapes. The fungus removes water and concentrates the sugar, giving rich flavors of honey and apricot. The most famous estate is Chateau d'Yquem.",
        "fr": "Le Sauternes est un vin blanc liquoreux de Bordeaux. Il est fait surtout a partir de Semillon. En automne, la brume du matin venant du petit Ciron aide un champignon, la pourriture noble, a se developper sur les raisins. Le champignon fait perdre de l'eau aux grains et concentre le sucre, ce qui donne des aromes riches de miel et d'abricot. Le domaine le plus celebre est le Chateau d'Yquem.",
        "vocab_en": ["noble rot - 貴腐", "mist - 薄霧", "concentrate - 濃縮", "honey - 蜂蜜"],
        "vocab_fr": ["pourriture noble - 貴腐", "brume - 薄霧", "concentrer - 濃縮", "miel - 蜂蜜"],
        "quiz_en": "What helps noble rot grow on the grapes in Sauternes?",
        "quiz_fr": "Qu'est-ce qui aide la pourriture noble a se developper a Sauternes?",
        "answer": "Morning mist from the Ciron river / La brume du Ciron",
    },
    {
        "topic": "Champagne",
        "en": "Champagne is a sparkling wine from northern France. It is made from Chardonnay, Pinot Noir, and Pinot Meunier. The bubbles come from a second fermentation, which happens inside the bottle. The soil is full of chalk, which stores water and gives the wines a fresh, mineral taste. Champagne can only be called Champagne if it comes from this region.",
        "fr": "Le Champagne est un vin mousseux du nord de la France. Il est elabore a partir de Chardonnay, de Pinot Noir et de Pinot Meunier. Les bulles viennent d'une seconde fermentation, qui a lieu dans la bouteille. Le sol est riche en craie, qui garde l'eau et donne aux vins un gout frais et mineral. Un vin ne peut s'appeler Champagne que s'il vient de cette region.",
        "vocab_en": ["sparkling - 氣泡的", "bubbles - 氣泡", "chalk - 白堊土", "fermentation - 發酵"],
        "vocab_fr": ["mousseux - 氣泡的", "bulles - 氣泡", "craie - 白堊土", "fermentation - 發酵"],
        "quiz_en": "Where does the second fermentation happen in Champagne?",
        "quiz_fr": "Ou a lieu la seconde fermentation en Champagne?",
        "answer": "Inside the bottle / Dans la bouteille",
    },
    {
        "topic": "Sancerre",
        "en": "Sancerre is a village in the Loire Valley, in central France. It is famous for white wine made from Sauvignon Blanc. The vineyards sit on hills with limestone, clay, and flint soils. The wines are dry and fresh, with flavors of lemon, grapefruit, and sometimes a smoky or flinty note. Sancerre goes very well with goat cheese from the same region.",
        "fr": "Sancerre est un village de la vallee de la Loire, dans le centre de la France. Il est celebre pour son vin blanc fait a partir de Sauvignon Blanc. Les vignes poussent sur des collines aux sols de calcaire, d'argile et de silex. Les vins sont secs et frais, avec des aromes de citron, de pamplemousse, et parfois une note fumee ou de pierre a fusil. Le Sancerre s'accorde tres bien avec le fromage de chevre de la meme region.",
        "vocab_en": ["flint - 燧石", "grapefruit - 葡萄柚", "smoky - 煙燻的", "goat cheese - 羊奶起司"],
        "vocab_fr": ["silex - 燧石", "pamplemousse - 葡萄柚", "fume - 煙燻的", "fromage de chevre - 羊奶起司"],
        "quiz_en": "Which grape is Sancerre white wine made from?",
        "quiz_fr": "De quel cepage est fait le Sancerre blanc?",
        "answer": "Sauvignon Blanc",
    },
    {
        "topic": "Chateauneuf-du-Pape",
        "en": "Chateauneuf-du-Pape is a famous wine village in the southern Rhone Valley. The name means the pope's new castle, because popes lived nearby in the fourteenth century. The vineyards are covered with large round stones, which keep the heat of the sun at night. Thirteen grape varieties are allowed, and Grenache is usually the main one. The wines are warm, rich, and full of spice.",
        "fr": "Chateauneuf-du-Pape est un village viticole celebre du sud de la vallee du Rhone. Son nom signifie le nouveau chateau du pape, car des papes vivaient tout pres au quatorzieme siecle. Les vignes sont couvertes de gros galets ronds, qui gardent la chaleur du soleil pendant la nuit. Treize cepages sont autorises, et le Grenache est generalement le principal. Les vins sont chauds, riches et pleins d'epices.",
        "vocab_en": ["pope - 教皇", "castle - 城堡", "spice - 香料", "allowed - 被允許的"],
        "vocab_fr": ["pape - 教皇", "chateau - 城堡", "epices - 香料", "autorise - 被允許的"],
        "quiz_en": "How many grape varieties are allowed in Chateauneuf-du-Pape?",
        "quiz_fr": "Combien de cepages sont autorises a Chateauneuf-du-Pape?",
        "answer": "Thirteen / Treize",
    },
    {
        "topic": "Alsace",
        "en": "Alsace is a wine region in eastern France, next to Germany. The Vosges mountains protect the vineyards from rain, so the region is dry and sunny. Unlike most French regions, Alsace puts the grape name on the label. The main grapes are Riesling, Gewurztraminer, Pinot Gris, and Muscat. Most Alsace wines are white and range from dry to sweet.",
        "fr": "L'Alsace est une region viticole de l'est de la France, a cote de l'Allemagne. Les montagnes des Vosges protegent les vignes de la pluie, donc la region est seche et ensoleillee. Contrairement a la plupart des regions francaises, l'Alsace indique le nom du cepage sur l'etiquette. Les principaux cepages sont le Riesling, le Gewurztraminer, le Pinot Gris et le Muscat. La plupart des vins d'Alsace sont blancs, du sec au doux.",
        "vocab_en": ["label - 酒標", "protect - 保護", "range - 涵蓋範圍", "sunny - 日照充足的"],
        "vocab_fr": ["etiquette - 酒標", "proteger - 保護", "du sec au doux - 從不甜到甜", "ensoleille - 日照充足的"],
        "quiz_en": "What do Alsace wine labels usually show that most French labels do not?",
        "quiz_fr": "Qu'indiquent souvent les etiquettes alsaciennes, contrairement a la plupart des etiquettes francaises?",
        "answer": "The grape name / Le nom du cepage",
    },
    {
        "topic": "Barolo",
        "en": "Barolo is a famous red wine from Piedmont, in northwest Italy. It is made only from the Nebbiolo grape. Nebbiolo makes wines that are light in color, but very high in tannin and acidity. Young Barolo can taste hard, so it needs many years to open up. With age, it shows flavors of roses, tar, and dried cherries.",
        "fr": "Le Barolo est un celebre vin rouge du Piemont, dans le nord-ouest de l'Italie. Il est fait uniquement a partir du cepage Nebbiolo. Le Nebbiolo donne des vins de couleur claire, mais tres riches en tanins et en acidite. Un jeune Barolo peut etre dur, donc il faut de nombreuses annees pour qu'il s'ouvre. Avec l'age, il montre des aromes de rose, de goudron et de cerise seche.",
        "vocab_en": ["tannin - 單寧", "acidity - 酸度", "tar - 焦油", "dried cherry - 乾櫻桃"],
        "vocab_fr": ["tanin - 單寧", "acidite - 酸度", "goudron - 焦油", "cerise seche - 乾櫻桃"],
        "quiz_en": "Which grape is Barolo made from?",
        "quiz_fr": "De quel cepage est fait le Barolo?",
        "answer": "Nebbiolo",
    },
]


def pick_content():
    day_index = (date.today() - START_DATE).days % len(CONTENT)
    return CONTENT[day_index], day_index + 1


def escape_md(text):
    chars = "_*[]()~`>#+-=|{}.!"
    for c in chars:
        text = text.replace(c, "\\" + c)
    return text


async def _synthesize_async(text, voice_name, filepath):
    communicate = edge_tts.Communicate(text, voice_name)
    await communicate.save(filepath)


def synthesize_speech(text, voice_name, filepath):
    asyncio.run(_synthesize_async(text, voice_name, filepath))
    return filepath


def send_telegram_message(text, markdown=False):
    url = "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN + "/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    if markdown:
        payload["parse_mode"] = "MarkdownV2"
    r = requests.post(url, json=payload)
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
    item, day_number = pick_content()

    en_file = synthesize_speech(item["en"], EN_VOICE, "/tmp/daily_en.mp3")
    fr_file = synthesize_speech(item["fr"], FR_VOICE, "/tmp/daily_fr.mp3")

    send_telegram_audio(en_file, "英文語音 - Day " + str(day_number) + " - " + item["topic"])
    send_telegram_audio(fr_file, "法文語音 - Day " + str(day_number) + " - " + item["topic"])

    vocab_en = "\n".join("- " + v for v in item["vocab_en"])
    vocab_fr = "\n".join("- " + v for v in item["vocab_fr"])

    message = (
        "Day " + str(day_number) + " 每日布根地聽力：" + item["topic"] + "\n\n"
        + "EN: " + item["en"] + "\n\n生字：\n" + vocab_en + "\n\n"
        + "FR: " + item["fr"] + "\n\n生字：\n" + vocab_fr
    )
    send_telegram_message(message)

    quiz_text = (
        "小測驗：\n"
        + escape_md(item["quiz_en"]) + "\n"
        + escape_md(item["quiz_fr"]) + "\n\n"
        + "答案（點擊顯示）：||" + escape_md(item["answer"]) + "||"
    )
    send_telegram_message(quiz_text, markdown=True)


if __name__ == "__main__":
    main()