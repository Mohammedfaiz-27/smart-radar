"""
Test script to verify language detection works correctly
"""
from social_test import detect_language

# Test cases - these should all be detected as 'other' (not English or Tamil)
test_posts = [
    "@addp1988 @RevisionistaCL Sí, pero Stalin y Hitler sabían que en algún día iba a estallar una guerra entre los dos, había preparativos por parte del ejército comunista.",
    "@polo_tom11594 @TrLarem_21 Tarih boyunca masum sivilleri toplu katleden devlet örnekleri arasında: - Nazi Almanya (Holokost, 6 milyon+ ölüm) - SSCB (Stalin dönemi, Holodomor ve tasfiyeler, milyonlarca ölüm) - Çin (Mao dönemi, Büyük Atılım, 20-45 milyon ölüm) - Kamboçya (Khmer Rouge, 1.5-2 milyon ölüm) -…",
    "@Cris_quella Se il tuo leader ha scelto di farsi invadere fatti suoi,con i soldi degli europei sta riempiendo i suoi granai personali e per giunta dobbiamo vivere sotto le sue presunte continue minacce. il rancore per i russi l'URSS Stalin e chi volete...tenetelo a casa vostra",
    "Y mientras Stalin esperando al otro lado del Vistula que nazis y polacos se mataran entre ellos para después cruzarlo y arrasar con todo.",
    "@miagmarsuren Ma anche Giuseppe Stalin",
]

# Test cases for English
english_posts = [
    "This is a test post in English about local news",
    "Breaking news: New development in the city center",
    "The weather today is sunny and warm",
]

# Test cases for Tamil
tamil_posts = [
    "சார் இங்க வாங்க பொம்பள இருக்குற வீட்டுல எப்படி நீங்க எகிறி குதிக்கலாம்?",
    "மாமியாரை ஆள் வைத்து தாக்கிய மருமகள் கைது",
    "இன்றைய தமிழ் செய்தி",
]

print("Testing Non-English (should be 'other'):")
print("=" * 60)
for i, post in enumerate(test_posts, 1):
    lang = detect_language(post)
    status = "✓" if lang == 'other' else "✗"
    print(f"{status} Post {i}: {lang}")
    print(f"   Text: {post[:80]}...")
    print()

print("\nTesting English (should be 'english'):")
print("=" * 60)
for i, post in enumerate(english_posts, 1):
    lang = detect_language(post)
    status = "✓" if lang == 'english' else "✗"
    print(f"{status} Post {i}: {lang}")
    print(f"   Text: {post}")
    print()

print("\nTesting Tamil (should be 'tamil'):")
print("=" * 60)
for i, post in enumerate(tamil_posts, 1):
    lang = detect_language(post)
    status = "✓" if lang == 'tamil' else "✗"
    print(f"{status} Post {i}: {lang}")
    print(f"   Text: {post}")
    print()
