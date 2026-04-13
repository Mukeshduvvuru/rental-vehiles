# Copy this file to .env and fill in your values
# NEVER commit the real .env file to version control

# PostgreSQL connection string
# Format: postgresql://user:password@host:port/database_name
DATABASE_URL=postgresql://postgres:0000@localhost:5432/rental_db

# JWT Secret Key - generate a strong random string for production
# Python command to generate: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your-super-secret-key-change-this-in-production

# JWT Algorithm (HS256 = HMAC with SHA-256, widely supported)
ALGORITHM=HS256

# Token expiry in minutes (30 = token expires in 30 mins after login)
ACCESS_TOKEN_EXPIRE_MINUTES=30
