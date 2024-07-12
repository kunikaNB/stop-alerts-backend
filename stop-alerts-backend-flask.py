from flask import Flask, request, render_template_string, redirect, url_for, jsonify
from sqlalchemy import create_engine, Column, Integer, String, MetaData, Table
from sqlalchemy.orm import declarative_base, sessionmaker
import signal

app = Flask(__name__)

DATABASE_URL = 'postgresql://username:password@localhost/vcm_db'  # Update with your actual database URL

# Set up the database engine
engine = create_engine(DATABASE_URL)
metadata = MetaData()
Base = declarative_base()

# Define the table structure
class StoppedIssue(Base):
    __tablename__ = 'stopped_issues'
    id = Column(Integer, primary_key=True)
    old_vcm_id = Column(String, nullable=False)
    new_vcm_id = Column(String, nullable=False)

Base.metadata.create_all(engine)

# Create a new session
Session = sessionmaker(bind=engine)
session = Session()

def save_stopped_issue(old_vcm_id, new_vcm_id):
    stopped_issue = StoppedIssue(old_vcm_id=old_vcm_id, new_vcm_id=new_vcm_id)
    session.add(stopped_issue)
    session.commit()

def get_stopped_issues():
    return {issue.old_vcm_id for issue in session.query(StoppedIssue).all()}

stopped_issues = get_stopped_issues()

def handle_exit(sig, frame):
    session.close()
    exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

@app.route('/stop_alerts_form/<issue_key>', methods=['GET', 'POST'])
def stop_alerts_form(issue_key):
    if request.method == 'POST':
        old_vcm_id = request.form.get('old_vcm_id')
        new_vcm_id = request.form.get('new_vcm_id')
        
        if old_vcm_id and new_vcm_id and old_vcm_id == issue_key:
            save_stopped_issue(old_vcm_id, new_vcm_id)
            stopped_issues.add(old_vcm_id)
            return redirect(url_for('stop_alerts_form', issue_key=issue_key, status='success'))
        else:
            return redirect(url_for('stop_alerts_form', issue_key=issue_key, status='error'))
    
    status = request.args.get('status')
    message = ''
    if status == 'success':
        message = 'Alerts stopped successfully!'
    elif status == 'error':
        message = 'Invalid data. Please ensure both fields are filled and old VCM ID matches the issue key.'
    
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                .card {
                    max-width: 400px;
                    margin: auto;
                    padding: 20px;
                    box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
                    transition: 0.3s;
                    border-radius: 5px;
                }
                .card input[type=text], .card input[type=submit] {
                    width: 100%;
                    padding: 10px;
                    margin: 5px 0 20px 0;
                    display: inline-block;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    box-sizing: border-box;
                }
                .card input[type=submit] {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                }
                .card input[type=submit]:hover {
                    background-color: #45a049;
                }
                .card h2 {
                    text-align: center;
                }
                .card p {
                    text-align: center;
                    color: red;
                }
            </style>
        </head>
        <body>
            <div class="card">
                <h2>Stop Alerts for VCM Jira Ticket {{ issue_key }}</h2>
                <form method="post">
                    <label for="old_vcm_id">Old VCM Jira Ticket ID:</label>
                    <input type="text" id="old_vcm_id" name="old_vcm_id" value="{{ issue_key }}" readonly><br><br>
                    <label for="new_vcm_id">New VCM Jira Ticket ID:</label>
                    <input type="text" id="new_vcm_id" name="new_vcm_id"><br><br>
                    <input type="submit" value="Submit">
                </form>
                {% if message %}
                    <p>{{ message }}</p>
                {% endif %}
            </div>
        </body>
        </html>
    ''', issue_key=issue_key, message=message)

@app.route('/check_alerts/<issue_key>', methods=['GET'])
def check_alerts(issue_key):
    if issue_key in stopped_issues:
        return {"stop_alerts": True}
    else:
        return {"stop_alerts": False}

@app.route('/stop_alerts', methods=['POST'])
def stop_alerts():
    data = request.json
    old_vcm_id = data.get('old_vcm_id')
    new_vcm_id = data.get('new_vcm_id')
    
    if old_vcm_id and new_vcm_id:
        save_stopped_issue(old_vcm_id, new_vcm_id)
        stopped_issues.add(old_vcm_id)
        return jsonify({"message": "Alerts stopped successfully"}), 200
    else:
        return jsonify({"error": "Invalid data"}), 400

if __name__ == '__main__':
    app.run(debug=True, host='::', port=5000)
