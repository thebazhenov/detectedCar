// Simple server-side API to verify Supabase-authenticated users (ES module)
import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import { createClient } from '@supabase/supabase-js';

const app = express();
const PORT = process.env.PORT || 4000;

app.use(cors({ origin: 'http://localhost:8080' }));
app.use(express.json());

const SUPABASE_URL = process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL;
const SERVICE_ROLE_KEY = process.env.SERVICE_ROLE_KEY;

if (!SUPABASE_URL || !SERVICE_ROLE_KEY) {
  console.error('Missing SUPABASE_URL or SERVICE_ROLE_KEY in environment. See .env.example');
}

const supabase = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);

// POST /api/verify-user
// Accepts Authorization: Bearer <access_token> or { token } in body
// Returns the Supabase user object if token is valid
app.post('/api/verify-user', async (req, res) => {
  try {
    const authHeader = req.headers.authorization || '';
    const tokenFromHeader = authHeader.startsWith('Bearer ') ? authHeader.split(' ')[1] : null;
    const token = tokenFromHeader || req.body?.token;

    if (!token) {
      return res.status(400).json({ error: 'No token provided. Send Authorization: Bearer <token> or { token } in JSON body.' });
    }

    // Use Supabase auth to get the user for this access token
    const { data, error } = await supabase.auth.getUser(token);

    if (error) {
      return res.status(401).json({ error: error.message });
    }

    return res.json({ user: data?.user ?? null });
  } catch (err) {
    console.error('verify-user error', err);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

app.listen(PORT, () => {
  console.log(`Server listening on http://localhost:${PORT}`);
});
