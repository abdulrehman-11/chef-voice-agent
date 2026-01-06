"""
LiveKit Access Token Generator
Generates temporary access tokens for testing
"""
import os
from livekit import api
from dotenv import load_dotenv

load_dotenv()

def generate_token(room_name: str, participant_identity: str) -> str:
    """Generate a LiveKit access token"""
    
    api_key = os.getenv('LIVEKIT_API_KEY')
    api_secret = os.getenv('LIVEKIT_API_SECRET')
    
    if not api_key or not api_secret:
        raise ValueError("LIVEKIT_API_KEY and LIVEKIT_API_SECRET must be set")
    
    token = api.AccessToken(api_key, api_secret) \
        .with_identity(participant_identity) \
        .with_name(participant_identity) \
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
        ))
    
    return token.to_jwt()

if __name__ == '__main__':
    import sys
    
    room = sys.argv[1] if len(sys.argv) > 1 else 'chef-session'
    identity = sys.argv[2] if len(sys.argv) > 2 else 'chef-test-user'
    
    token = generate_token(room, identity)
    print(f"\n✅ Token generated for '{identity}' in room '{room}':")
    print(f"\n{token}\n")
