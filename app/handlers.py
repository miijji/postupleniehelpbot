
from aiogram import F, Router, Bot, types
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import pandas as pd
#import app.keyboards as kb
from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                            InlineKeyboardMarkup, InlineKeyboardButton, 
                            )

from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder



router = Router()



class Form(StatesGroup):
    choose_subjects_count = State()
    choose_subjects_combo = State()
    input_scores = State()
    choosing_university = State()

#загрузка данных из excel
def load_universities(file_path):
    df = pd.read_excel(file_path)
    universities = {}

    for _, row in df.iterrows():
        university_name = row["ВУЗ"]
        direction_name = row["Направление"]
        program_description = row['Описание']

        if university_name not in universities:
            universities[university_name] = {}

        if direction_name not in universities[university_name]:
            universities[university_name][direction_name] = []

        program = {
            "description": program_description,
            "total_score": int(row["Проходной балл"])\
                  if pd.notna(row["Проходной балл"]) else 0,
            "dvi_required": row["Требуется ДВИ"],
            "dvi_min_score": int(row["Мин. балл ДВИ"])\
                  if pd.notna(row["Мин. балл ДВИ"]) else 0,
            "optional": [],
            "math": None,
            "rus": None,
            "fiz": None,
            "inf": None
        }

        # Обработка выборочных предметов
        if pd.notna(row.get("Выборочные предметы", "")) and row["Выборочные предметы"] != "-":
            program["optional"] = [
                "fiz" if "physics" in s.lower() else "inf" 
                for s in str(row["Выборочные предметы"]).split(", ") 
                if s.strip()
            ]

        # Добавляем минимальные баллы с конвертацией ключей
        subject_mapping = {
            "Math": "math",
            "Russian": "rus",
            "Physics": "fiz",
            "Computer_science": "inf"
        }

        for col_name, key in subject_mapping.items():
            if pd.notna(row.get(col_name, "")) and row[col_name] != "-":
                program[key] = int(row[col_name])

        universities[university_name][direction_name].append(program)

    return universities
UNIVERSITIES = load_universities(r'app\Книга1n.xlsx')



SUBJECT_COMBINATIONS = {
    3: [
        {"name": "РУС+МАТ+ИНФ", "subjects": ["rus", "math", "inf"]},
        {"name": "РУС+МАТ+ФИЗ", "subjects": ["rus", "math", "fiz"]}
    ],
    4: [  
        {"name": "РУС+МАТ+ИНФ+ФИЗ", "subjects": ["rus", "math", "inf", "fiz"]}
    ]
}




@router.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text="3 предмета", callback_data="count_3"),
        types.InlineKeyboardButton(text="4 предмета", callback_data="count_4")
    )
    await message.answer("Привет! Сколько предметов ты сдаешь?",\
                          reply_markup=builder.as_markup())
    await state.set_state(Form.choose_subjects_count)

@router.callback_query(Form.choose_subjects_count, F.data.startswith("count_"))
async def process_count(callback: types.CallbackQuery, state: FSMContext):
    count = int(callback.data.split("_")[1])
    await state.update_data(subjects_count=count)
    
    builder = InlineKeyboardBuilder()
    combinations = SUBJECT_COMBINATIONS.get(count, [])
    
    # Динамическое создание кнопок для выбранного количества
    for combo in combinations:
        builder.add(types.InlineKeyboardButton(
            text=combo["name"],
            callback_data=f"combo_{'_'.join(combo['subjects'])}"  
        ))
    
    builder.adjust(1)
    await callback.message.edit_text(
        "Выбери набор предметов:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(Form.choose_subjects_combo)
    await callback.answer()

@router.callback_query(Form.choose_subjects_combo, F.data.startswith("combo_"))
async def process_combo(callback: types.CallbackQuery, state: FSMContext):
    # Получаем выбранные предметы из callback_data
    _, *subjects = callback.data.split("_")  
    await state.update_data(
        subjects=subjects,
        current_subject=0
    )
    
    # Запрашиваем первый предмет
    data = await state.get_data()
    first_subject = data["subjects"][0]
    await callback.message.answer(f"Введи балл по {get_subject_name_komu_chemu(first_subject)}:")
    await state.set_state(Form.input_scores)
    await callback.answer()


@router.message(Form.input_scores)
async def process_score(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    if not validate_score(message.text):
        return await message.answer("Ошибка! Введи целое число от 0 до 100")
    
    current_idx = data["current_subject"]
    subjects = data["subjects"]
    
    # Сохраняем балл
    scores = data.get("scores", {})
    scores[subjects[current_idx]] = int(message.text)
    
    # Проверяем количество оставшихся предметов
    if current_idx + 1 < len(subjects):
        await state.update_data(
            scores=scores,
            current_subject=current_idx + 1
        )
        next_subject = subjects[current_idx + 1]
        await message.answer(f"Введи балл по {get_subject_name_komu_chemu(next_subject)}:")
    else:
        await state.update_data(scores=scores)
        await show_final_results(message, state)


def validate_score(score: str) -> bool:
    try:
        return 0 <= int(score) <= 100
    except ValueError:
        return False

def get_subject_name_komu_chemu(code: str) -> str:
    names = {
        "rus": "русскому языку",
        "math": "математике", 
        "inf": "информатике",
        "fiz": "физике"
    }
    return names.get(code, "предмету")

def get_subject_name_kto_chto(code: str) -> str:
    names = {
        "rus": "русский язык",
        "math": "математика", 
        "inf": "информатика",
        "fiz": "физика"
    }
    return names.get(code, "предмет")



async def show_final_results(message: types.Message, state: FSMContext):
    data = await state.get_data()
    scores = data["scores"]
    result = [
        "✅ Твои результаты:",
        *[f"• {get_subject_name_kto_chto(subj).capitalize()}: {score}" 
          for subj, score in scores.items()],
        f"\n🧮 Сумма баллов: {sum(scores.values())}",
        "\n🏫 Выбери вуз:",
        "/hse - НИУ ВШЭ",
        "/msu - МГУ",
        "/mipt - МФТИ",
        "/bmstu - МГТУ им. Баумана",
        "/mephi - НИЯУ МИФИ"
    ]
    
    await message.answer("\n".join(result))
    
    
    await state.set_state(Form.choosing_university)










@router.message(Command("hse"))
async def show_hse_programs(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        user_scores = data.get("scores", {})
        
        # Расчет базовых баллов
        rus = user_scores.get("rus", 0)
        math = user_scores.get("math", 0)
        fiz = user_scores.get("fiz", 0)
        inf = user_scores.get("inf", 0)
        
        response = ["📚 Подходящие программы НИУ ВШЭ:"]
        has_programs = False
        
        target_university = "ВШЭ"
        if target_university not in UNIVERSITIES:
            await message.answer("Данные по ВШЭ не найдены")
            return
            
        for direction, programs in UNIVERSITIES[target_university].items():
            direction_programs = []
            
            for program in programs:
                meets_requirements = True
                
                # Определение способа расчета баллов
                if program["optional"]:
                    # Случай с выборочными предметами
                    total_score = rus + math + max(fiz, inf)
                elif program["fiz"] is None or program["inf"] is None:
                    # Случай с прочерком в одном из предметов
                    total_score = rus + math + (fiz if program["inf"] is None else inf)
                else:
                    # Общий случай (4 предмета)
                    total_score = rus + math + fiz + inf
                
                score_diff = program["total_score"] - total_score
                
                # Проверка минимальных баллов по предметам
                required_checks = [
                    ("math", program["math"]),
                    ("rus", program["rus"]),
                    ("fiz", program["fiz"]),
                    ("inf", program["inf"])
                ]
                
                for subject, min_score in required_checks:
                    if min_score is not None and user_scores.get(subject, 0) < min_score:
                        meets_requirements = False
                        break
                
                # Проверка выборочных предметов
                if program["optional"]:
                    elective_passed = any(
                        user_scores.get(subj, 0) >= program.get(subj, 0)
                        for subj in program["optional"]
                    )
                    if not elective_passed:
                        meets_requirements = False

                # Проверка проходного балла
                if meets_requirements and total_score + 10 < program["total_score"]:
                    meets_requirements = False
                
                # Формирование информации о программе
                if meets_requirements:
                    min_scores = [
                        f"{name}: {program[subj]}" 
                        for subj, name in [
                            ("math", "Математика"), 
                            ("rus", "Русский"),
                            ("fiz", "Физика"),
                            ("inf", "Информатика")
                        ] 
                        if program[subj] is not None
                    ]
                    
                    program_info = [
                        f"🎓 Программа: {program['description']}",
                        f"├ Минимум: {', '.join(min_scores)}",
                        f"├ Твой суммарный балл: {total_score}",
                    ]

                    if total_score >= program["total_score"]:
                        program_info.extend([
                            f"├ Примерный проходной балл: {program['total_score']}",
                            "├ ✅ Вероятность пройти очень высокая!",
                            f"└ ДВИ: {'✅' if program['dvi_required'] == 'да' else 'Не требуется'}"
                        ])
                    else:
                        program_info.extend([
                            f"⚠️ Не хватает ~{score_diff} баллов",
                            "├ Проверь индивидуальные достижения",
                            f"└ ДВИ: {'✅' if program['dvi_required'] == 'да' else 'Не требуется'}"
                        ])
                    
                    direction_programs.append("\n".join(program_info))
                    has_programs = True
            
            if direction_programs:
                response.append(f"\n🔹 {direction}:")
                response.extend(direction_programs)
                
        await message.answer("\n".join(response) if has_programs else "😔 Нет подходящих программ")
        
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")
        print(f"Ошибка: {e}")






@router.message(Command("mipt"))
async def show_hse_programs(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        user_scores = data.get("scores", {})
        
        # Расчет базовых баллов
        rus = user_scores.get("rus", 0)
        math = user_scores.get("math", 0)
        fiz = user_scores.get("fiz", 0)
        inf = user_scores.get("inf", 0)
        
        response = ["📚 Подходящие программы МФТИ:"]
        has_programs = False
        
        target_university = "МФТИ"
        if target_university not in UNIVERSITIES:
            await message.answer("Данные по МФТИ не найдены")
            return
            
        for direction, programs in UNIVERSITIES[target_university].items():
            direction_programs = []
            
            for program in programs:
                meets_requirements = True
                
                # Определение способа расчета баллов
                if program["optional"]:
                    # Случай с выборочными предметами
                    total_score = rus + math + max(fiz, inf)
                elif program["fiz"] is None or program["inf"] is None:
                    # Случай с прочерком в одном из предметов
                    total_score = rus + math + (fiz if program["inf"] is None else inf)
                else:
                    # Общий случай (4 предмета)
                    total_score = rus + math + fiz + inf
                
                score_diff = program["total_score"] - total_score
                
                # Проверка минимальных баллов по предметам
                required_checks = [
                    ("math", program["math"]),
                    ("rus", program["rus"]),
                    ("fiz", program["fiz"]),
                    ("inf", program["inf"])
                ]
                
                for subject, min_score in required_checks:
                    if min_score is not None and user_scores.get(subject, 0) < min_score:
                        meets_requirements = False
                        break
                
                # Проверка выборочных предметов
                if program["optional"]:
                    elective_passed = any(
                        user_scores.get(subj, 0) >= program.get(subj, 0)
                        for subj in program["optional"]
                    )
                    if not elective_passed:
                        meets_requirements = False

                # Проверка проходного балла
                if meets_requirements and total_score + 10 < program["total_score"]:
                    meets_requirements = False
                
                # Формирование информации о программе
                if meets_requirements:
                    min_scores = [
                        f"{name}: {program[subj]}" 
                        for subj, name in [
                            ("math", "Математика"), 
                            ("rus", "Русский"),
                            ("fiz", "Физика"),
                            ("inf", "Информатика")
                        ] 
                        if program[subj] is not None
                    ]
                    
                    program_info = [
                        f"🎓 Программа: {program['description']}",
                        f"├ Минимум: {', '.join(min_scores)}",
                        f"├ Твой суммарный балл: {total_score}",
                    ]

                    if total_score >= program["total_score"]:
                        program_info.extend([
                            f"├ Примерный проходной балл: {program['total_score']}",
                            "├ ✅ Вероятность пройти очень высокая!",
                            f"└ ДВИ: {'✅' if program['dvi_required'] == 'да' else 'Не требуется'}"
                        ])
                    else:
                        program_info.extend([
                            f"⚠️ Не хватает ~{score_diff} баллов",
                            "├ Проверь индивидуальные достижения",
                            f"└ ДВИ: {'✅' if program['dvi_required'] == 'да' else 'Не требуется'}"
                        ])
                    
                    direction_programs.append("\n".join(program_info))
                    has_programs = True
            
            if direction_programs:
                response.append(f"\n🔹 {direction}:")
                response.extend(direction_programs)
                
        await message.answer("\n".join(response) if has_programs else "😔 Нет подходящих программ")
        
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")
        print(f"Ошибка: {e}")





@router.message(Command("msu"))
async def show_msu_programs(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        user_scores = data.get("scores", {})
        
        # Расчет базовых баллов
        rus = user_scores.get("rus", 0)
        math = user_scores.get("math", 0)
        fiz = user_scores.get("fiz", 0)
        inf = user_scores.get("inf", 0)
        
        response = ["📚 Подходящие программы МГУ:"]
        has_programs = False
        
        target_university = "МГУ"
        if target_university not in UNIVERSITIES:
            await message.answer("Данные по МГУ не найдены")
            return

        DVI_THRESHOLD = 60  # Максимальная разница баллов при наличии ДВИ
            
        for direction, programs in UNIVERSITIES[target_university].items():
            direction_programs = []
            
            for program in programs:
                meets_requirements = True
                is_near = False

                # Определение способа расчета баллов
                if program["optional"]:
                    total_score = rus + math + max(fiz, inf)
                elif program["fiz"] is None or program["inf"] is None:
                    total_score = rus + math + (fiz if program["inf"] is None else inf)
                else:
                    total_score = rus + math + fiz + inf
                
                score_diff = program["total_score"] - total_score

                # Проверка минимальных баллов по предметам
                required_checks = [
                    ("math", program["math"]),
                    ("rus", program["rus"]),
                    ("fiz", program["fiz"]),
                    ("inf", program["inf"])
                ]
                
                for subject, min_score in required_checks:
                    if min_score is not None and user_scores.get(subject, 0) < min_score:
                        meets_requirements = False
                        break

                # Проверка выборочных предметов
                if program["optional"]:
                    elective_passed = any(
                        user_scores.get(subj, 0) >= program.get(subj, 0)
                        for subj in program["optional"]
                    )
                    if not elective_passed:
                        meets_requirements = False

                # Особые условия для ДВИ
                if program["dvi_required"] == "да":
                    if meets_requirements and (0 < score_diff <= DVI_THRESHOLD):
                        is_near = True
                    elif total_score < program["total_score"] - DVI_THRESHOLD:
                        meets_requirements = False
                else:
                    if meets_requirements and total_score < program["total_score"]:
                        meets_requirements = False

                if meets_requirements:
                    # Формирование информации о предметах
                    min_scores = [
                        f"{name}: {program[subj]}" 
                        for subj, name in [
                            ("math", "Математика"), 
                            ("rus", "Русский"),
                            ("fiz", "Физика"),
                            ("inf", "Информатика")
                        ] 
                        if program[subj] is not None
                    ]
                    
                    program_info = [
                        f"🎓 Программа: {program['description']}",
                        f"├ Минимум: {', '.join(min_scores)}",
                        f"├ Твой суммарный балл: {total_score}",
                    ]

                    # Добавляем информацию о ДВИ
                    if is_near:
                        program_info.extend([
                            f"⚠️ Вероятность пройти с ДВИ! (Не хватает {score_diff} баллов)",
                            f"└ Минимальный балл ДВИ: {program['dvi_min_score']}"
                        ])
                    else:
                        program_info.append(
                            f"└ ДВИ: {'✅ Требуется' if program['dvi_required'] == 'да' else '❌ Не требуется'}"
                        )
                    
                    direction_programs.append("\n".join(program_info))
                    has_programs = True
            
            if direction_programs:
                response.append(f"\n🔹 {direction}:")
                response.extend(direction_programs)
        
        await message.answer("\n".join(response) if has_programs else "😔 Нет подходящих программ")
        
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")
        print(f"Ошибка: {e}")


@router.message(Command("bmstu"))
async def show_hse_programs(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        user_scores = data.get("scores", {})
        
        # Расчет базовых баллов
        rus = user_scores.get("rus", 0)
        math = user_scores.get("math", 0)
        fiz = user_scores.get("fiz", 0)
        inf = user_scores.get("inf", 0)
        
        response = ["📚 Подходящие программы МГТУ им. Баумана:"]
        has_programs = False
        
        target_university = "МГТУ им. Баумана"
        if target_university not in UNIVERSITIES:
            await message.answer("Данные по МГТУ им. Баумана не найдены")
            return
            
        for direction, programs in UNIVERSITIES[target_university].items():
            direction_programs = []
            
            for program in programs:
                meets_requirements = True
                
                # Определение способа расчета баллов
                if program["optional"]:
                    # Случай с выборочными предметами
                    total_score = rus + math + max(fiz, inf)
                elif program["fiz"] is None or program["inf"] is None:
                    # Случай с прочерком в одном из предметов
                    total_score = rus + math + (fiz if program["inf"] is None else inf)
                else:
                    # Общий случай (4 предмета)
                    total_score = rus + math + fiz + inf
                
                score_diff = program["total_score"] - total_score
                
                # Проверка минимальных баллов по предметам
                required_checks = [
                    ("math", program["math"]),
                    ("rus", program["rus"]),
                    ("fiz", program["fiz"]),
                    ("inf", program["inf"])
                ]
                
                for subject, min_score in required_checks:
                    if min_score is not None and user_scores.get(subject, 0) < min_score:
                        meets_requirements = False
                        break
                
                # Проверка выборочных предметов
                if program["optional"]:
                    elective_passed = any(
                        user_scores.get(subj, 0) >= program.get(subj, 0)
                        for subj in program["optional"]
                    )
                    if not elective_passed:
                        meets_requirements = False

                # Проверка проходного балла
                if meets_requirements and total_score + 10 < program["total_score"]:
                    meets_requirements = False
                
                # Формирование информации о программе
                if meets_requirements:
                    min_scores = [
                        f"{name}: {program[subj]}" 
                        for subj, name in [
                            ("math", "Математика"), 
                            ("rus", "Русский"),
                            ("fiz", "Физика"),
                            ("inf", "Информатика")
                        ] 
                        if program[subj] is not None
                    ]
                    
                    program_info = [
                        f"🎓 Программа: {program['description']}",
                        f"├ Минимум: {', '.join(min_scores)}",
                        f"├ Твой суммарный балл: {total_score}",
                    ]

                    if total_score >= program["total_score"]:
                        program_info.extend([
                            f"├ Примерный проходной балл: {program['total_score']}",
                            "├ ✅ Вероятность пройти очень высокая!",
                            f"└ ДВИ: {'✅' if program['dvi_required'] == 'да' else 'Не требуется'}"
                        ])
                    else:
                        program_info.extend([
                            f"⚠️ Не хватает ~{score_diff} баллов",
                            "├ Проверь индивидуальные достижения",
                            f"└ ДВИ: {'✅' if program['dvi_required'] == 'да' else 'Не требуется'}"
                        ])
                    
                    direction_programs.append("\n".join(program_info))
                    has_programs = True
            
            if direction_programs:
                response.append(f"\n🔹 {direction}:")
                response.extend(direction_programs)
                
        await message.answer("\n".join(response) if has_programs else "😔 Нет подходящих программ")
        
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")
        print(f"Ошибка: {e}")



@router.message(Command("mephi"))
async def show_hse_programs(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        user_scores = data.get("scores", {})
        
        # Расчет базовых баллов
        rus = user_scores.get("rus", 0)
        math = user_scores.get("math", 0)
        fiz = user_scores.get("fiz", 0)
        inf = user_scores.get("inf", 0)
        
        response = ["📚 Подходящие программы НИЯУ МИФИ:"]
        has_programs = False
        
        target_university = "НИЯУ МИФИ"
        if target_university not in UNIVERSITIES:
            await message.answer("Данные по НИЯУ МИФИ не найдены")
            return
            
        for direction, programs in UNIVERSITIES[target_university].items():
            direction_programs = []
            
            for program in programs:
                meets_requirements = True
                
                # Определение способа расчета баллов
                if program["optional"]:
                    # Случай с выборочными предметами
                    total_score = rus + math + max(fiz, inf)
                elif program["fiz"] is None or program["inf"] is None:
                    # Случай с прочерком в одном из предметов
                    total_score = rus + math + (fiz if program["inf"] is None else inf)
                else:
                    # Общий случай (4 предмета)
                    total_score = rus + math + fiz + inf
                
                score_diff = program["total_score"] - total_score
                
                # Проверка минимальных баллов по предметам
                required_checks = [
                    ("math", program["math"]),
                    ("rus", program["rus"]),
                    ("fiz", program["fiz"]),
                    ("inf", program["inf"])
                ]
                
                for subject, min_score in required_checks:
                    if min_score is not None and user_scores.get(subject, 0) < min_score:
                        meets_requirements = False
                        break
                
                # Проверка выборочных предметов
                if program["optional"]:
                    elective_passed = any(
                        user_scores.get(subj, 0) >= program.get(subj, 0)
                        for subj in program["optional"]
                    )
                    if not elective_passed:
                        meets_requirements = False

                # Проверка проходного балла
                if meets_requirements and total_score + 10 < program["total_score"]:
                    meets_requirements = False
                
                # Формирование информации о программе
                if meets_requirements:
                    min_scores = [
                        f"{name}: {program[subj]}" 
                        for subj, name in [
                            ("math", "Математика"), 
                            ("rus", "Русский"),
                            ("fiz", "Физика"),
                            ("inf", "Информатика")
                        ] 
                        if program[subj] is not None
                    ]
                    
                    program_info = [
                        f"🎓 Программа: {program['description']}",
                        f"├ Минимум: {', '.join(min_scores)}",
                        f"├ Твой суммарный балл: {total_score}",
                    ]

                    if total_score >= program["total_score"]:
                        program_info.extend([
                            f"├ Примерный проходной балл: {program['total_score']}",
                            "├ ✅ Вероятность пройти очень высокая!",
                            f"└ ДВИ: {'✅' if program['dvi_required'] == 'да' else 'Не требуется'}"
                        ])
                    else:
                        program_info.extend([
                            f"⚠️ Не хватает ~{score_diff} баллов",
                            "├ Проверь индивидуальные достижения",
                            f"└ ДВИ: {'✅' if program['dvi_required'] == 'да' else 'Не требуется'}"
                        ])
                    
                    direction_programs.append("\n".join(program_info))
                    has_programs = True
            
            if direction_programs:
                response.append(f"\n🔹 {direction}:")
                response.extend(direction_programs)
                
        await message.answer("\n".join(response) if has_programs else "😔 Нет подходящих программ")
        
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")
        print(f"Ошибка: {e}")

