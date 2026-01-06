"""
Simple token server for LiveKit access
Provides tokens for frontend to connect to LiveKit rooms
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from livekit import api
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

@app.route('/get-token', methods=['POST'])
def get_token():
    """Generate LiveKit access token"""
    try:
        data = request.get_json()
        
        room_name = data.get('room', 'chef-session')
        participant_identity = data.get('identity', f'chef-{os.urandom(4).hex()}')
        participant_name = data.get('name', participant_identity)
        
        # Get LiveKit credentials
        api_key = os.getenv('LIVEKIT_API_KEY')
        api_secret = os.getenv('LIVEKIT_API_SECRET')
        
        if not api_key or not api_secret:
            return jsonify({'error': 'LiveKit credentials not configured'}), 500
        
        # Generate token
        token = api.AccessToken(api_key, api_secret) \
            .with_identity(participant_identity) \
            .with_name(participant_name) \
            .with_grants(api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            ))
        
        jwt_token = token.to_jwt()
        
        return jsonify({
            'token': jwt_token,
            'room': room_name,
            'identity': participant_identity
        })
        
    except Exception as e:
        print(f"Error generating token: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'LiveKit Token Server'})

if __name__ == '__main__':
    print("🔑 Starting LiveKit Token Server...")
    print(f"📡 LiveKit URL: {os.getenv('LIVEKIT_URL')}")
    print("🌐 Server running on http://localhost:5000")
    print("📍 Token endpoint: POST http://localhost:5000/get-token")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
