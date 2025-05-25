from flask import Flask, jsonify
import json
import os

app = Flask(__name__)

# Load menu data
DATA_PATH = os.path.join(os.path.dirname(__file__), '../../shared_data/menus.json')

def load_menus():
    with open(DATA_PATH, 'r') as f:
        return json.load(f)

@app.route('/menus', methods=['GET'])
def get_all_menus():
    return jsonify(load_menus())

@app.route('/menu/<int:restaurant_id>', methods=['GET'])
def get_menu_by_id(restaurant_id):
    menus = load_menus()
    for restaurant in menus:
        if restaurant['restaurant_id'] == restaurant_id:
            return jsonify(restaurant)
    return jsonify({'error': 'Restaurant not found'}), 404

if __name__ == '__main__':
    app.run(port=5001)
