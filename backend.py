from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import hashlib
import psycopg2
from datetime import datetime, timedelta, timezone
import jwt
import toml
import sys

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
JWT_SECRET = "6B2E87418BF62D278DA58788629EC647B441FE900F5F108DB212B82C7237033F"

CONFIG = toml.load(".env")
DATABASE_USER = CONFIG["DATABASE_USER"]
DB_PASSWORD = CONFIG["DB_PASSWORD"]
DB_IP_PORT = CONFIG["DB_IP_PORT"]
DB_NAME = CONFIG["DB_NAME"]
SERVER_PORT = CONFIG["SERVER_PORT"]

@app.route('/registration', methods=['POST'])
@cross_origin()
def register():
    try:
        cursor = conn.cursor()
        content = request.json
        username = content['username']
        password = content['password']
        role = content['role']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        sql_query = "SELECT * FROM users WHERE username='%s'"
        cursor.execute(sql_query % username)
        data = cursor.fetchone()
        
        if data != None:
            return jsonify({"result": "This user already registered"}), 409

        else:
            
            sql_query = "INSERT INTO users (username, password, role, banned) VALUES ('%s', '%s', '%s', '%s')"
            cursor.execute(sql_query % (username, hashed_password, role, False))
            
            sql_query = "SELECT * FROM users WHERE username='%s'"
            cursor.execute(sql_query % username)
            sqldata = cursor.fetchone()
            
            payload = {"username": username, "id": sqldata[0], "role": sqldata[3]}
            payload["exp"] = datetime.now(tz=timezone.utc) + timedelta(minutes=5)
            tokenJWT = jwt.encode(payload=payload, key=JWT_SECRET, algorithm='HS256')
            payload["exp"] = datetime.now(tz=timezone.utc) + timedelta(days=30)
            RToken = jwt.encode(payload=payload, key=JWT_SECRET, algorithm='HS256')
            
            sql_query = "UPDATE users SET RToken = '%s' WHERE username = '%s'"
            cursor.execute(sql_query % (RToken, username))
            
            
            return jsonify({"error": False, "result": True}), 200
        
        cursor.close()

    except Exception as e:
        return jsonify({"error": True, "result": e}), 500
    
@app.route('/login', methods=['POST'])
@cross_origin()
def login():
    try:
        content = request.json
        username = content['username']
        password = content['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
        cursor = conn.cursor()
        sql_query = "SELECT * FROM users WHERE username='%s'"
        cursor.execute(sql_query % username)
        data = cursor.fetchone()
    
        if data == None:
            return jsonify({"error": True, "result": "User does not exist"}), 401
    
        if data[1] == username and data[2] == hashed_password:
            payload = {"username": username, "id": data[0], "role": data[3]}
            payload["exp"] = datetime.now(tz=timezone.utc) + timedelta(minutes=5)
            tokenJWT = jwt.encode(payload=payload, key=JWT_SECRET, algorithm='HS256')
            payload["exp"] = datetime.now(tz=timezone.utc) + timedelta(days=30)
            RToken = jwt.encode(payload=payload, key=JWT_SECRET, algorithm='HS256')
        
            sql_query = "UPDATE users SET RToken = '%s' WHERE username = '%s'"
            cursor.execute(sql_query % (RToken, username))

            return jsonify({"error": False, "tokenJWT": tokenJWT, "tokenRT": RToken}), 200
        
        else:
            return jsonify({"error": True, "result": "Incorrect Password"}), 401
        
        cursor.close()
        
    except Exception as e:
        return jsonify({"error": True, "result": e}), 500

@app.route('/refreshToken', methods=['POST'])
@cross_origin()
def RefreshToken():
    try:
        cursor = conn.cursor()
        content = request.json
        RToken = content['tokenRT']
        sql_query = "SELECT rtoken FROM users WHERE rtoken='%s'"
        cursor.execute(sql_query % RToken)
        data = cursor.fetchone()

        if data == None:
            return jsonify({"error": True, "result": "Incorrect RToken"}), 401
    
        if data[0] == RToken:
            payload = jwt.decode(RToken, key=JWT_SECRET, algorithms=["HS256"])
            payload["exp"] = datetime.now(tz=timezone.utc) + timedelta(minutes=5)
            tokenJWT = jwt.encode(payload=payload, key=JWT_SECRET, algorithm='HS256')
            payload["exp"] = datetime.now(tz=timezone.utc) + timedelta(days=30)
            RToken = jwt.encode(payload=payload, key=JWT_SECRET, algorithm='HS256')
            
            sql_query = "UPDATE users SET RToken = '%s' WHERE username = '%s'"
            cursor.execute(sql_query % (RToken, payload["username"]))
            
            return jsonify({"error": False, "tokenJWT": tokenJWT, "tokenRT": RToken}), 200
            
        else:
            return jsonify({"error": True, "result": "Incorrect RToken"}), 401
            
        cursor.close()
    
    except Exception as e:
        return jsonify({"error": True, "result": e}), 500

class DatabaseException(Exception):
    pass


if __name__ == '__main__':
    try:
        conn = psycopg2.connect(f'postgresql://{DATABASE_USER}:{DB_PASSWORD}@{DB_IP_PORT}/{DB_NAME}')
        conn.autocommit = True
        print("Successfully connected to database")
    except Exception as e:
        print('Can`t establish connection to database')
        raise DatabaseException("Panic error, exit")
        sys.exit()
    app.run(host='0.0.0.0', port=SERVER_PORT)