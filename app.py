from flask import Flask, request, jsonify
from datetime import datetime
import os

app = Flask(__name__)

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    trips = data.get('trips', [])
    total_days = 0

    for trip in trips:
        try:
            d1 = datetime.strptime(trip['departure'], "%Y-%m-%d")
            d2 = datetime.strptime(trip['return'], "%Y-%m-%d")
            days = (d2 - d1).days
            if days > 0:
                total_days += days
        except Exception as e:
            return jsonify({'error': f'Ошибка в данных: {e}'}), 400

    limit = 180  # лимит дней вне Польши за 5 лет
    status = "OK" if total_days <= limit else "Превышен лимит"
    return jsonify({
        'total_days': total_days,
        'limit': limit,
        'status': status
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
