import mongoengine as me

from models import Course, Category

from settings import MONGO_URI


me.connect(host=MONGO_URI)



def update_is_free():
    for i in Course.objects:
        i.update(is_free=i.discount_percentage==100)


def check_duplicateds():
    d = {}
    for i in Course.objects:
        if i.course_id in d:
            d[i.course_id] += 1
        else:
            d[i.course_id] = 1
    for k,v in d.items():
        if v > 1:
            print(k, v)


def remove_duplicateds():
    d = set()
    for i in Course.objects:
        if i.course_id in d:
            i.delete()
            print('deleted!')
        else:
            d.add(i.course_id)


def update_search_text():
    for i in Course.objects:
        search_text = '\n'.join([i.title, i.teacher, i.description]) 
        i.update(search_text=search_text)

# update_is_free()
# check_duplicateds()
# remove_duplicateds()
update_search_text()
