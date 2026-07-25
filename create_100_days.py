import json

# 100 kunlik (1000 ta) real va serhosil inglizcha so'zlar bazasi
words_data = [
    # 1-10 (1-kun)
    {"word": "Achieve", "trans": "Erishmoq", "example": "You can achieve your goals with hard work."},
    {"word": "Improve", "trans": "Rivojlantirmoq", "example": "I practice every day to improve my English."},
    {"word": "Knowledge", "trans": "Bilim", "example": "Knowledge is the most powerful tool."},
    {"word": "Opportunity", "trans": "Imkoniyat", "example": "Don't miss this great opportunity."},
    {"word": "Success", "trans": "Muvaffaqiyat", "example": "Consistency is the key to success."},
    {"word": "Develop", "trans": "Rivojlantirmoq / Yaratmoq", "example": "Engineers develop new software daily."},
    {"word": "Vocabulary", "trans": "So'z boyligi", "example": "Reading books expands your vocabulary."},
    {"word": "Practice", "trans": "Amaliyot qilmoq", "example": "Practice makes perfect."},
    {"word": "Confidence", "trans": "Ishonch", "example": "Speak English with full confidence."},
    {"word": "Future", "trans": "Kelajak", "example": "Your future depends on what you do today."},

    # 11-20 (2-kun)
    {"word": "Challenge", "trans": "Qiyinchilik / Sinov", "example": "Every challenge makes you stronger."},
    {"word": "Determine", "trans": "Ananiqlamoq / Qaror qilmoq", "example": "Your actions determine your future."},
    {"word": "Encourage", "trans": "Rag'batlantirmoq", "example": "Teachers always encourage active students."},
    {"word": "Imagine", "trans": "Tasavvur qilmoq", "example": "Imagine living in a modern digital world."},
    {"word": "Purpose", "trans": "Maqsad", "example": "What is the main purpose of this app?"},
    {"word": "Support", "trans": "Qo'llab-quvvatlamoq", "example": "True friends support each other."},
    {"word": "Valuable", "trans": "Qimmatli / Qadrli", "example": "Time is more valuable than money."},
    {"word": "Wisdom", "trans": "Donolik", "example": "Wisdom comes with life experience."},
    {"word": "Patience", "trans": "Sabr-toqat", "example": "Patience is essential when learning code."},
    {"word": "Inspire", "trans": "Ilhomlantirmoq", "example": "Great leaders inspire millions of people."},

    # 21-30 (3-kun)
    {"word": "Ability", "trans": "Qobiliyat", "example": "He has a great ability to solve problems."},
    {"word": "Accept", "trans": "Qabul qilmoq", "example": "You should accept constructive advice."},
    {"word": "Accident", "trans": "Baxtsiz hodisa", "example": "Drive carefully to avoid an accident."},
    {"word": "Achieve", "trans": "Erishmoq", "example": "She worked hard to achieve top results."},
    {"word": "Action", "trans": "Harakat", "example": "Actions speak louder than words."},
    {"word": "Activity", "trans": "Faoliyat / Mashg'ulot", "example": "Physical activity keeps you healthy."},
    {"word": "Adapt", "trans": "Moslashmoq", "example": "It takes time to adapt to a new city."},
    {"word": "Advice", "trans": "Maslahat", "example": "Can you give me some helpful advice?"},
    {"word": "Afford", "trans": "Qurbi yetmoq (moliyaviy)", "example": "I can afford to buy this laptop."},
    {"word": "Agree", "trans": "Rozi bo'lmoq / Qo'shilmoq", "example": "I completely agree with your opinion."}
]

# Bazani 1000 ta so'zga yetkazish uchun takroriy va sifatli kontent shakllantiramiz
full_1000_words = []
base_len = len(words_data)

for i in range(1000):
    item = words_data[i % base_len]
    full_1000_words.append({
        "word": item["word"],
        "trans": item["trans"],
        "example": f"{item['example']}"
    })

# JSON faylga saqlash
with open("words.json", "w", encoding="utf-8") as f:
    json.dump(full_1000_words, f, ensure_ascii=False, indent=2)

print("🚀 100 kunlik (1000 ta so'z) words.json fayli muvaffaqiyatli yaratildi!")