from flask import Flask, render_template, request, redirect, session, jsonify
import db
import requests as req

app = Flask(__name__)
app.secret_key = 'bloodbank123'

@app.template_filter('format_number')
def format_number(value):
    try:
        return "{:,}".format(int(value))
    except:
        return value

@app.route('/')
def home():
    if 'admin' not in session:
        return redirect('/login')
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admin WHERE username=%s AND password=%s", (username, password))
        admin = cursor.fetchone()
        conn.close()
        if admin:
            session['admin'] = username
            return redirect('/')
        else:
            error = 'Invalid credentials'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/login')

@app.route('/donors')
def donors():
    if 'admin' not in session:
        return redirect('/login')
    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM donors")
    donors = cursor.fetchall()
    conn.close()
    return render_template('donors.html', donors=donors)

@app.route('/add_donor', methods=['POST'])
def add_donor():
    name = request.form['name']
    age = request.form['age']
    blood_group = request.form['blood_group']
    phone = request.form['phone']
    email = request.form['email']
    location = request.form['location']
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO donors (name, age, blood_group, phone, email, location, available) VALUES (%s,%s,%s,%s,%s,%s,1)",
                   (name, age, blood_group, phone, email, location))
    conn.commit()
    conn.close()
    return redirect('/donors')

@app.route('/delete_donor/<int:id>')
def delete_donor(id):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM donors WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    return redirect('/donors')

@app.route('/stock')
def stock():
    if 'admin' not in session:
        return redirect('/login')
    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM blood_stock")
    stock = cursor.fetchall()
    conn.close()
    return render_template('stock.html', stock=stock)

@app.route('/update_stock', methods=['POST'])
def update_stock():
    blood_group = request.form['blood_group']
    units = request.form['units']
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE blood_stock SET units_available=%s, last_updated=CURDATE() WHERE blood_group=%s",
                   (units, blood_group))
    conn.commit()
    conn.close()
    return redirect('/stock')

@app.route('/requests')
def requests_page():
    if 'admin' not in session:
        return redirect('/login')
    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM blood_requests")
    reqs = cursor.fetchall()
    conn.close()
    return render_template('requests.html', requests=reqs)

@app.route('/add_request', methods=['POST'])
def add_request():
    patient = request.form['patient_name']
    blood_group = request.form['blood_group']
    units = request.form['units_needed']
    hospital = request.form['hospital']
    contact = request.form['contact']
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO blood_requests (patient_name, blood_group, units_needed, hospital, contact, request_date, status) VALUES (%s,%s,%s,%s,%s,CURDATE(),'Pending')",
                   (patient, blood_group, units, hospital, contact))
    conn.commit()
    conn.close()
    return redirect('/requests')

@app.route('/update_status/<int:id>/<status>')
def update_status(id, status):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE blood_requests SET status=%s WHERE id=%s", (status, id))
    conn.commit()
    conn.close()
    return redirect('/requests')

@app.route('/search')
def search():
    if 'admin' not in session:
        return redirect('/login')
    blood_group = request.args.get('blood_group', '')
    location = request.args.get('location', '')
    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM donors WHERE available=1"
    params = []
    if blood_group:
        query += " AND blood_group=%s"
        params.append(blood_group)
    if location:
        query += " AND location LIKE %s"
        params.append(f'%{location}%')
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    return render_template('search.html', results=results, blood_group=blood_group, location=location)

@app.route('/user', methods=['GET'])
def user_portal():
    blood_group = request.args.get('blood_group', '')
    location = request.args.get('location', '')
    search_results = None
    if blood_group or location:
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM donors WHERE available=1"
        params = []
        if blood_group:
            query += " AND blood_group=%s"
            params.append(blood_group)
        if location:
            query += " AND location LIKE %s"
            params.append(f'%{location}%')
        cursor.execute(query, params)
        search_results = cursor.fetchall()
        conn.close()
    return render_template('user.html', search_results=search_results, location=location)

@app.route('/user/request', methods=['POST'])
def user_request():
    patient = request.form['patient_name']
    blood_group = request.form['blood_group']
    units = request.form['units_needed']
    hospital = request.form['hospital']
    contact = request.form['contact']
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO blood_requests (patient_name, blood_group, units_needed, hospital, contact, request_date, status) VALUES (%s,%s,%s,%s,%s,CURDATE(),'Pending')",
                   (patient, blood_group, units, hospital, contact))
    conn.commit()
    conn.close()
    return render_template('user.html', success='Blood request submitted successfully!', search_results=None, location='')

@app.route('/user/donate', methods=['POST'])
def user_donate():
    name = request.form['name']
    age = request.form['age']
    blood_group = request.form['blood_group']
    phone = request.form['phone']
    email = request.form['email']
    location = request.form['location']
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO donors (name, age, blood_group, phone, email, location, available) VALUES (%s,%s,%s,%s,%s,%s,1)",
                   (name, age, blood_group, phone, email, location))
    conn.commit()
    conn.close()
    return render_template('user.html', success='You have been registered as a donor!', search_results=None, location='')

# ========== HEALTH STATS (REAL EXTERNAL API) ==========

@app.route('/healthstats')
def healthstats():
    if 'admin' not in session:
        return redirect('/login')
    try:
        global_data = req.get('https://disease.sh/v3/covid-19/all', timeout=5).json()
        india_data = req.get('https://disease.sh/v3/covid-19/countries/India', timeout=5).json()
        return render_template('healthstats.html', global_stats=global_data, india=india_data, error=None)
    except Exception as e:
        return render_template('healthstats.html', global_stats=None, india=None, error=str(e))

# ========== REST API ROUTES ==========

@app.route('/api/donors', methods=['GET'])
def api_donors():
    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM donors")
    donors = cursor.fetchall()
    conn.close()
    for donor in donors:
        if donor.get('last_donation'):
            donor['last_donation'] = str(donor['last_donation'])
    return jsonify(donors)

@app.route('/api/stock', methods=['GET'])
def api_stock():
    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM blood_stock")
    stock = cursor.fetchall()
    conn.close()
    for item in stock:
        if item.get('last_updated'):
            item['last_updated'] = str(item['last_updated'])
    return jsonify(stock)

@app.route('/api/requests', methods=['GET'])
def api_requests():
    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM blood_requests")
    reqs = cursor.fetchall()
    conn.close()
    for req_item in reqs:
        if req_item.get('request_date'):
            req_item['request_date'] = str(req_item['request_date'])
    return jsonify(reqs)

@app.route('/api/donors/<int:id>', methods=['GET'])
def api_donor_by_id(id):
    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM donors WHERE id=%s", (id,))
    donor = cursor.fetchone()
    conn.close()
    if donor:
        if donor.get('last_donation'):
            donor['last_donation'] = str(donor['last_donation'])
        return jsonify(donor)
    return jsonify({'error': 'Donor not found'}), 404

@app.route('/api/stock/<blood_group>', methods=['GET'])
def api_stock_by_group(blood_group):
    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM blood_stock WHERE blood_group=%s", (blood_group,))
    item = cursor.fetchone()
    conn.close()
    if item:
        if item.get('last_updated'):
            item['last_updated'] = str(item['last_updated'])
        return jsonify(item)
    return jsonify({'error': 'Blood group not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)