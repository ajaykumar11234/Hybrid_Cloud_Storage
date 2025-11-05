import jwt
from functools import wraps
from flask import request, jsonify
import datetime

# JWT Configuration
JWT_SECRET_KEY = 'ajay-secret-key'
JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(hours=24)

# Mock user database (replace with real database in production)
users = []

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            # Remove 'Bearer ' prefix
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Decode the token
            data = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            current_user = next((user for user in users if user['id'] == data['user_id']), None)
            
            if not current_user:
                return jsonify({'error': 'User not found'}), 401
                
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token is invalid'}), 401
        except Exception as e:
            return jsonify({'error': 'Token verification failed'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated