from flask import Flask, jsonify, request, send_from_directory, render_template
from databaser import *
import os

app = Flask(__name__)
IMAGE_DIR = os.path.join(os.path.dirname(__file__), 'images')

@app.route('/menu')
def menu():
    return jsonify(Menu())

@app.route('/images/<filename>')
def getimage(filename):
    return send_from_directory(IMAGE_DIR, filename)

@app.route('/to-order', methods=['POST', 'GET'])
def toOrder():
    try:
        form = {
            "order": request.form.get("order"),
            "adress": request.form.get("adress"),
            "firstname": request.form.get("firstname"),
            "lastname": request.form.get("lastname"),
            "phonenumber": request.form.get("phonenumber")
        }

        writeTransaction(
            form["order"],
            form["adress"],
            form["firstname"],
            form["lastname"],
            form["phonenumber"]
        )

        return jsonify({
            "status": "ok",
            "message": "Ваша заказ прийнято! Очікуйте кур'єра та готовтесь до апетиту через 10-30 хв."
        })
    except Exception as ex:
        print(ex)
        return jsonify({
            "status": "error",
            "message": "Нажаль трапилась помилка при замовленні. Зверніться в підтримку та повідомте нам про проблему."
        })

@app.route('/transaction')
def transaction():
    elements = gettransaction()
    return render_template('orderhistory.html', elements=elements)

if __name__ == '__main__':
    databaseMenuInit()
    databaseTransactionInit()
    app.run(debug=True)