from flask import Flask, render_template
import csv

app = Flask(__name__)



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




@app.get('/')
def test():
    posts = load()
    data = {
        'posts': posts[:12],
        'pages': [1, 2, 3, 4, 5],
        'current_page': 1
    }
    # data = load()
    # print(data[1])
    return render_template('3.html', data=data)



if __name__ == '__main__':
    app.run(debug=True)
