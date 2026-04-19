# constants, blocklists, thresholds

CORPORATE_EMPLOYERS = [
    "Google", "Meta", "Microsoft", "OpenAI", "Anthropic", "Stripe", "Apple",
    "Amazon", "Netflix", "Uber", "Lyft", "Airbnb", "Salesforce", "Oracle",
    "IBM", "Intel", "NVIDIA", "Figma", "Notion", "Vercel", "Cloudflare",
    "GitHub", "LinkedIn", "Twitter", "X", "Snap", "Pinterest", "Dropbox",
    "Atlassian", "Shopify", "Square", "Block", "Palantir", "Databricks",
    "Snowflake", "MongoDB", "HashiCorp",
]

CORPORATE_BIO_TERMS = [
    "staff",
    "official",
    "team at",
    "engineer @",
    "developer advocate",
    "devrel",
    "developer relations",
    "platform team",
]

DEPLOYMENT_FILE_INDICATORS = [
    "Dockerfile",
    "docker-compose.yml",
    "vercel.json",
    ".vercel",
    "railway.toml",
    "fly.toml",
    "fly.io",
    ".env.example",
    "render.yaml",
    "heroku.yml",
    "Procfile",
]

SOPHISTICATED_DEPENDENCIES = {
    "auth": [
        "passport", "nextauth", "clerk", "auth0", "supertokens", "lucia",
        "jose", "jsonwebtoken", "bcrypt", "firebase-admin",
    ],
    "payments": [
        "stripe", "paddle", "lemonsqueezy", "braintree",
    ],
    "database": [
        "prisma", "drizzle", "sequelize", "typeorm", "mongoose", "sqlalchemy",
        "tortoise-orm", "supabase", "planetscale",
    ],
    "api_wrappers": [
        "openai", "anthropic", "twilio", "sendgrid", "resend", "plaid",
        "pinecone", "weaviate",
    ],
}

ACCOUNT_MIN_AGE_DAYS = 60

FOLLOWER_CEILING = 5000
