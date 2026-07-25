from flask import Flask, jsonify, request, render_template_string
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URI', 'sqlite:///employees.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(80), nullable=False)

with app.app_context():
    db.create_all()

# Single-Page Frontend Dashboard
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Employee Management Portal</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background-color: #f4f6f9; }
        .card { max-width: 600px; margin: auto; background: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        h2 { color: #2c3e50; margin-top: 0; }
        .status { padding: 6px 12px; background-color: #e8f8f5; color: #27ae60; border-radius: 20px; font-weight: bold; font-size: 0.9em; display: inline-block; margin-bottom: 15px; }
        input { width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box; }
        button { width: 100%; background-color: #2980b9; color: white; padding: 12px; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; margin-top: 10px; }
        button:hover { background-color: #3498db; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; color: #333; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Employee Management Portal</h2>
        <div class="status">● System Status: Healthy (DevSecOps Deployed)</div>
        
        <h3>Add New Employee</h3>
        <input type="text" id="name" placeholder="Full Name">
        <input type="text" id="role" placeholder="Role (e.g. DevOps Engineer)">
        <button onclick="addEmployee()">Add Employee</button>

        <h3>Employee Directory</h3>
        <table>
            <thead>
                <tr><th>ID</th><th>Name</th><th>Role</th></tr>
            </thead>
            <tbody id="empTable"></tbody>
        </table>
    </div>

    <script>
        async function fetchEmployees() {
            const res = await fetch('/api/employees');
            const data = await res.json();
            const table = document.getElementById('empTable');
            table.innerHTML = data.map(e => `<tr><td>${e.id}</td><td>${e.name}</td><td>${e.role}</td></tr>`).join('');
        }

        async function addEmployee() {
            const name = document.getElementById('name').value;
            const role = document.getElementById('role').value;
            if(!name || !role) return alert('Please enter both name and role');

            await fetch('/api/employees', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ name, role })
            });
            document.getElementById('name').value = '';
            document.getElementById('role').value = '';
            fetchEmployees();
        }

        fetchEmployees();
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/api/employees', methods=['GET', 'POST'])
def manage_employees():
    if request.method == 'POST':
        data = request.get_json()
        new_emp = Employee(name=data['name'], role=data['role'])
        db.session.add(new_emp)
        db.session.commit()
        return jsonify({"message": "Employee added!"}), 201
    
    employees = Employee.query.all()
    return jsonify([{"id": e.id, "name": e.name, "role": e.role} for e in employees]), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
