import sqlite3
import requests
import random
import os
import sys

def get_database_path():
    if getattr(sys, 'frozen', False):
        # 如果应用程序是作为捆绑的可执行文件运行，使用这个路径
        current_dir = os.path.dirname(sys.executable)
    else:
        # 正常情况下，使用脚本文件路径
        current_dir = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(current_dir, 'vocabulary.db')

db_path = get_database_path()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL,
    part_of_speech TEXT,
    meaning TEXT,
    total_attempts INTEGER DEFAULT 0,
    correct_attempts INTEGER DEFAULT 0
)
''')

# 搜索单词的函数
def search_word(word):
    # 替换为你的APIKEY
    api_key = "APIKEY"
    url = "https://apis.tianapi.com/enwords/index"

    params = {
        'key': api_key,
        'word': word
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()

        if data.get('code') == 200:
            result = data.get('result', {})
            word = result.get('word', '')
            content = result.get('content', '')

            return {
                'word': word,
                'part_of_speech': '',  
                'meaning': content
            }
        else:
            print(f"Error from API: {data.get('msg')}")
            return None
    else:
        print(f"Error fetching data for word: {word}")
        return None

# 录入单词
def save_word_to_db(word_info):
    cursor.execute('''
    INSERT INTO words (word, part_of_speech, meaning, total_attempts, correct_attempts)
    VALUES (?, ?, ?, ?, ?)
    ''', (word_info['word'], word_info['part_of_speech'], word_info['meaning'], 0, 0))
    conn.commit()

def get_random_word():
    cursor.execute('''
    SELECT * FROM words 
    WHERE correct_attempts < 5
    ORDER BY RANDOM() LIMIT 1
    ''')
    return cursor.fetchone()

def get_random_incorrect_choices(correct_id, limit=3):
    cursor.execute('''
    SELECT part_of_speech, meaning FROM words 
    WHERE id != ? AND correct_attempts < 5 
    ORDER BY RANDOM() LIMIT ?
    ''', (correct_id, limit))
    return cursor.fetchall()

def update_word_statistics(word_id, correct):
    cursor.execute('''
    UPDATE words 
    SET total_attempts = total_attempts + 1, 
        correct_attempts = correct_attempts + ?
    WHERE id = ?
    ''', (1 if correct else 0, word_id))
    conn.commit()

# 单词测试
def generate_quiz():
    while True:
        correct_word = get_random_word()
        if not correct_word:
            print("没有可用的单词来生成测验（可能所有单词都已正确回答5次）。")
            break

        correct_id, english_word, correct_part_of_speech, correct_meaning, total_attempts, correct_attempts = correct_word

        incorrect_choices = get_random_incorrect_choices(correct_id)
        options = incorrect_choices + [(correct_part_of_speech, correct_meaning)]

        random.shuffle(options)

        print(f"\n单词：{english_word}")
        print("请选择正确的中文翻译和词性：")

        for i, (part_of_speech, meaning) in enumerate(options):
            print(f"{i + 1}. {part_of_speech} - {meaning}")

        user_choice = input("请输入你的选择（1-4，输入 '0' 返回主菜单）：")

        if user_choice == '0':
            break

        user_choice = int(user_choice) - 1

        if options[user_choice] == (correct_part_of_speech, correct_meaning):
            print("恭喜你，选择正确！")
            update_word_statistics(correct_id, True)
        else:
            print(f"很遗憾，正确答案是：{correct_part_of_speech} - {correct_meaning}")
            update_word_statistics(correct_id, False)

def show_statistics():
    cursor.execute('''
    SELECT word, total_attempts, correct_attempts, 
           (total_attempts - correct_attempts) * 1.0 / total_attempts AS error_rate
    FROM words
    WHERE total_attempts > 0
    ORDER BY error_rate DESC
    ''')
    results = cursor.fetchall()

    print("\n单词错误率统计：")
    for word, total, correct, error_rate in results:
        print(f"单词：{word}, 总尝试次数：{total}, 正确次数：{correct}, 错误率：{error_rate:.2f}")

def view_words_by_letter(letter):
    cursor.execute('''
    SELECT word, part_of_speech, meaning FROM words
    WHERE word LIKE ?
    ''', (letter + '%',))
    results = cursor.fetchall()
    if results:
        print(f"\n单词以 '{letter}' 开头的有：")
        for word, part_of_speech, meaning in results:
            print(f"单词：{word}, 词性：{part_of_speech}, 释义：{meaning}")
    else:
        print(f"没有找到以 '{letter}' 开头的单词。")

def delete_word(word):
    cursor.execute('''
    DELETE FROM words
    WHERE word = ?
    ''', (word,))
    conn.commit()
    print(f"单词 '{word}' 已删除（如果存在）。")

def main():
    while True:
        print("\n选择功能：")
        print("1. 录入单词")
        print("2. 进行单词测验")
        print("3. 显示错误率统计")
        print("4. 查看特定字母开头的单词")
        print("5. 删除单词")
        print("6. 退出")
        choice = input("请输入你的选择：")
        
        if choice == '1':
            while True:
                word = input("请输入一个单词（输入 '0' 返回主菜单）：")
                if word == '0':
                    break
                word_info = search_word(word)
                if word_info:
                    save_word_to_db(word_info)
                    print(f"单词 '{word}' 已经保存到数据库。")
                else:
                    print("未能获取到单词的信息。")
        elif choice == '2':
            generate_quiz()
        elif choice == '3':
            show_statistics()
        elif choice == '4':
            letter = input("请输入要查看的起始字母：")
            view_words_by_letter(letter)
        elif choice == '5':
            word_to_delete = input("请输入要删除的单词：")
            delete_word(word_to_delete)
        elif choice == '6':
            break
        else:
            print("无效的选择，请重新输入。")

if __name__ == '__main__':
    main()

conn.close()
