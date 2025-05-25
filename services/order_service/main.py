from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

DATA_PATH = os.path.join(os.path.dirname(__file__), '../../shared_data/orders.json')

def load_orders():
    if not os.path.exists(DATA_PATH):
        return []
    with open(DATA_PATH, 'r') as f:
        return json.load(f)

def save_orders(orders):
    with open(DATA_PATH, 'w') as f:
        json.dump(orders, f, indent=2)

@app.route('/orders', methods=['GET'])
def get_all_orders():
    return jsonify(load_orders())

@app.route('/order', methods=['POST'])
def place_order():
    orders = load_orders()
    new_order = request.get_json()

    if not new_order:
        return jsonify({'error': 'Invalid request data'}), 400

    new_order['order_id'] = len(orders) + 1
    orders.append(new_order)
    save_orders(orders)
    return jsonify({'message': 'Order placed successfully', 'order_id': new_order['order_id']}), 201

if __name__ == '__main__':
    app.run(port=5002)
