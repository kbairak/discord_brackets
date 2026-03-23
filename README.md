# Discord Brackets Bot

A Discord bot that enables community members to run playoff-style bracket tournaments for fun voting.

## Features

- Collect contestants from community members
- Automatically generate tournament brackets with play-in rounds when needed
- Multi-round voting with real-time vote counts
- Visual bracket representation
- Support for power-of-2 and non-power-of-2 contestant counts

## Setup

### Prerequisites

- Python 3.13+
- Docker and Docker Compose
- A Discord account with permission to add bots to a server

### Creating a Discord Bot Application

1. **Create the Application:**
   - Go to <https://discord.com/developers/applications>
   - Click "New Application" and give it a name (e.g., "Brackets Bot")
   - Click "Create"

2. **Create the Bot:**
   - In the left sidebar, click "Bot"
   - Click "Add Bot" and confirm
   - Under the bot's username, click "Reset Token" and copy it
   - ⚠️ **Keep this token secret!** Never commit it to version control

3. **Enable Intents:**
   - Scroll down to "Privileged Gateway Intents"
   - Enable:
     - ✅ **Message Content Intent** (required for the bot to read messages)
   - Click "Save Changes"

4. **Invite the Bot to Your Server:**
   - In the left sidebar, click "OAuth2" → "URL Generator"
   - Under "Scopes", select:
     - ✅ `bot`
     - ✅ `applications.commands`
   - Under "Bot Permissions", select:
     - ✅ Send Messages
     - ✅ Attach Files
   - Copy the generated URL at the bottom
   - Open the URL in your browser and select a server to add the bot to
   - Click "Authorize"

### Installation

1. Clone the repository

2. Start the PostgreSQL database:

   ```bash
   docker-compose up -d
   ```

3. Install dependencies using uv:

   ```bash
   make install
   # or directly: uv sync
   ```

4. Set environment variables:

   ```bash
   export DISCORD_BOT_TOKEN=your_actual_token_here
   export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/discord_brackets
   ```

### Running the Bot

```bash
make run
# or directly: uv run main.py
```

The bot will connect to Discord and be ready to use in your server. You can stop it anytime with Ctrl+C.

**Note:** The bot only runs while the command is active. For 24/7 availability, you'll need to host it on a server (VPS, Railway, Render, etc.).

## Usage

1. In a Discord channel, type `/brackets [title]` to create a new tournament
2. Community members click "Submit Contestant" to add entries
3. The creator clicks "End Collection" when ready
4. Review and optionally edit contestants
5. Click "Start Bracket" to begin
6. Vote on matches by clicking the contestant buttons
7. The creator clicks "End Round" to advance when voting is complete
8. Continue until a winner is crowned!

## How It Works

### Bracket Generation

The bot automatically calculates the optimal bracket structure:

- **Power of 2 contestants** (4, 8, 16, etc.): Clean bracket with no play-ins
- **Non-power of 2 contestants**: Play-in round to reduce to next lower power of 2
- **Example**: 13 contestants → 3 play-in matches → 10 remaining + 3 winners = 13 → reduces to 8 for main bracket

### Voting

- Each user can vote once per match
- Vote counts are displayed in real-time on the buttons
- Ties are broken randomly

### Database

All bracket data is stored in a PostgreSQL database including:

- Brackets and their phases
- Contestants and elimination rounds
- Matches and results
- Individual votes

The database runs in Docker for local development and can be deployed to any PostgreSQL-compatible service (e.g., Render, Railway, Supabase) for production.

## Development

### Quick Commands (Makefile)

```bash
make help      # Show all available commands
make lint      # Run ruff and pyright type checkers
make format    # Auto-format code with ruff
make test      # Run pytest test suite
make check     # Run all checks (lint + test)
make install   # Install dependencies
make run       # Run the bot
make clean     # Remove cache files
```

### Testing

The bot includes a comprehensive test suite with 23 tests covering:

- **Database operations** (8 tests): CRUD operations, vote counting, contestant management
- **Bracket logic** (10 tests): Generation algorithms, round advancement, edge cases
- **Integration** (5 tests): Full tournament flows, multi-round scenarios

Run tests with:

```bash
# Make sure PostgreSQL is running
docker-compose up -d

# Run tests
make test
# or
pytest tests/ -v
```

Tests require `DATABASE_URL` to be set. They will clean and recreate tables for each test run.

Test coverage includes:

- Power of 2 contestant counts (2, 4, 8, 16)
- Non-power of 2 counts requiring play-ins (3, 5, 6, 13)
- Edge cases (ties, byes, single elimination)
- Vote tracking and duplicate prevention
- Full tournament flows from start to winner

### Type Checking

The project uses Pyright for type checking (officially supported by py-cord):

```bash
make lint
# or
pyright . --pythonversion 3.13
```

## Project Structure

```
discord_brackets/
├── main.py                 # Bot initialization & entry point
├── bot/
│   ├── cog.py             # Main bracket command cog
│   └── views.py           # Discord UI components
├── database/
│   ├── db.py              # Database connection
│   └── models.py          # Database operations
├── bracket/
│   ├── logic.py           # Bracket generation & progression
│   └── image.py           # Bracket visualization
├── tests/                  # Test suite (pytest)
│   ├── conftest.py        # Test fixtures
│   ├── test_database.py   # Database tests
│   ├── test_bracket_logic.py  # Bracket algorithm tests
│   └── test_integration.py    # Full flow tests
└── docker-compose.yml     # PostgreSQL database setup
```

## Deployment (DigitalOcean App Platform)

This project is ready to deploy to DigitalOcean using the included `.do/app.yaml` spec:

### Prerequisites

- DigitalOcean account
- GitHub repository with your code

### Deployment Steps

1. **Push to GitHub:**

   ```bash
   git push origin main
   ```

2. **Create App on DigitalOcean:**
   - Go to <https://cloud.digitalocean.com/apps>
   - Click **"Create App"**
   - Select **GitHub** as source
   - Choose your repository and `main` branch
   - DigitalOcean will auto-detect the `.do/app.yaml` configuration

3. **Review Configuration:**
   - **Worker:** Discord bot background process ($5/month)
   - **PostgreSQL:** Database (dev tier: $7/month, production: $15/month)
   - `DATABASE_URL` is automatically injected into the worker

4. **Set Discord Bot Token:**
   - In the app configuration, find `DISCORD_BOT_TOKEN`
   - Click **Edit** and paste your Discord bot token
   - This is kept secret and only available at runtime

5. **Deploy:**
   - Click **"Create Resources"**
   - DigitalOcean will build and deploy your app
   - Monitor the **Logs** tab to verify the bot started successfully

### Auto-Deployment

- Every push to `main` triggers automatic redeployment
- View deployment status and logs in the DigitalOcean dashboard

### Pricing

- **Development:** ~$12/month (basic-xxs worker + dev database)
- **Production:** ~$27/month (basic-xs worker + production database)

### Alternative: CLI Deployment

```bash
# Install doctl
brew install doctl  # macOS

# Authenticate
doctl auth init

# Deploy from app spec
doctl apps create --spec .do/app.yaml
```

## TODOs

- [ ] Image
- [ ] Custom order to make sure favourites have a small chance of encountering each other early
- [ ] Timer
- [ ] User-selected emoji per option
