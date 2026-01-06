// Production API endpoint - will be set via Vercel environment variable
const TOKEN_SERVER_URL = window.VITE_TOKEN_SERVER_URL || 'http://localhost:5000/get-token';

console.log('🔧 Token server URL:', TOKEN_SERVER_URL);
