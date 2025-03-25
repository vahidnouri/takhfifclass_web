
import csv
from models import Course





def load():
    with open('data/a.csv', mode='r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        data = [row for row in reader]

        data2 = []
        for i in data:
            j = i.copy()
            for k in i:
                if k not in 'title,main_price,discounted_price,discount_percentage,img_url,category,affiliate_link':
                    j.pop(k)
            data2.append(j)
    return data2




def load2():
    with open('data/a.csv', mode='r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        data = [row for row in reader]
        #
        for i in data:
            Course(
                course_id = i.get('course_id', ''),
                title = i.get('title', ''),
                datetime = datetime.strptime(i.get('date'), '%Y-%m-%d'),
                teacher = i.get('Teacher', ''),
                main_price = int(i.get('main_price') or 0),
                discounted_price = int(i.get('discounted_price') or 0),
                discount_percentage = int(i.get('discount_percentage') or 0),
                has_discount = eval(i.get('has_discount', 'False')),
                img_url = i.get('img_url', ''),
                course_url = i.get('course_url', ''),
                duration = i.get('Duration', ''),
                category = i.get('category', ''),
                website = i.get('website', ''),
                affiliate_link = i.get('affiliate_link', ''),
                description = i.get('description', ''),
                summary = i.get('Summary', ''),
                seasons = i.get('Seasons', ''),
                shamsi_date = i.get('shamsi_date', ''),
                course_url_name = i.get('course_url_name', ''),
                rephrased_desc = '',
                is_free = False if int(i.get('main_price') or 0) else True,
            ).save()
    return 



