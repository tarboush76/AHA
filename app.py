import pandas as pd
from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def index():
    """عرض صفحة البحث الرئيسية."""
    return render_template('index.html')

@app.route('/results', methods=['GET'])
def get_results():
    """استقبال رقم الجلوس وقراءة الملف المناسب لعرض النتيجة."""
    seat_number = request.args.get('seat_number', type=str)
    
    if not seat_number:
        return render_template('not_found.html')

    first_digit = seat_number[0]
    
    file_map = {
        '5': 'results_2025.xlsx',
        '8': 'results_2024.xlsx',
        '3': 'results_2023.xlsx',
        '2': 'results_2022.xlsx',
        '4': 'results_2021.xlsx'
    }
    
    file_name = file_map.get(first_digit)
    
    if not file_name:
        return render_template('not_found.html', seat_number=seat_number)

    try:
        df = pd.read_excel(file_name)
    except FileNotFoundError:
        return f"<h1>خطأ: ملف النتائج '{file_name}' غير موجود.</h1>"

    year_end = file_name.split('_')[1].split('.')[0]
    year_start = str(int(year_end) - 1)
    academic_year = f"{year_start}/{year_end}"
    
    student_row = df[df['Number'].astype(str) == seat_number]
    
    if student_row.empty:
        return render_template('not_found.html', seat_number=seat_number)
    
    student_data = student_row.iloc[0].to_dict()
    print("Column names found in student data:", student_data.keys())
    # == الأسطر الجديدة هنا ==
    # تنسيق تاريخ الميلاد
    if 'تاريخ الميلاد' in student_data and pd.notna(student_data['تاريخ الميلاد']):
        # التحقق من أن القيمة هي كائن تاريخ قبل التنسيق
        if hasattr(student_data['تاريخ الميلاد'], 'strftime'):
            student_data['تاريخ الميلاد'] = student_data['تاريخ الميلاد'].strftime("%Y/%m/%d")
    # == نهاية الأسطر الجديدة ==

    grades_rows_html = ""
    subjects_count = 0
    subject_translation = {
        "القران": "Holy Quran", "الاسلامية": "Islamic Education", "العربي": "Arabic Language",
        "الانجليزي": "English Language", "الرياضيات": "Mathematics", "العلوم": "Science", "الاحتماعيات": "Social Studies",
    }
    
    for col, val in student_data.items():
        col_name = str(col).strip()
        if col_name in subject_translation:
            if pd.notna(val):
                subjects_count += 1
                english_name = subject_translation.get(col_name, "")
                grade_value = int(val) if isinstance(val, (int, float)) else str(val)
                
                grades_rows_html += f'''
<tr class="odd">
    <td align="center"><b><span style="font-size: 12px;">{col_name}</span></b></td>
    <td align="center">100</td>
    <td class="small-col" align="center">50</td>
    <td align="center" class=" nowrap"><h4><b>{grade_value}</b></h4></td>
    <td align="center"><b><span style="font-size: 12px;">{english_name}</span></b></td>
</tr>'''

    max_total = subjects_count * 100 if subjects_count > 0 else 0

    return render_template(
        'results.html',
        student=student_data,
        grades_rows=grades_rows_html,
        max_total=max_total,
        academic_year=academic_year
    )

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=5001, debug=True)
 