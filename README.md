# GPT in Review

![Preview](preview.gif)

Generates `data.json` and `tarot_card.png` for the GPT in Review website from your OpenAI data export.

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- OpenAI API key (for topic clustering/embeddings)
- Google API key (for tarot card image generation via Gemini)

## Getting Your ChatGPT Export

1. Go to [chat.openai.com](https://chat.openai.com)
2. Click your profile icon → **Settings**
3. **Data controls** → **Export data** → **Confirm export**
4. Wait for the email (can take a few minutes to hours depending on data size)
5. Download and extract the zip file
6. Find `conversations.json` in the extracted folder (usually inside of `OpenAI-export/User Online Activity/Conversations__user-xxxxxx_conversations_1_export.zip` archive)

## Setup

```bash
# Create virtual environment (recommended)
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

# Configure API keys
cp .env.example .env
```

Edit `.env` with your actual API keys:
```
OPENAI_API_KEY=sk-proj-your-key-here
GOOGLE_API_KEY=AIza-your-key-here
```

## Usage

```bash
python main.py /path/to/conversations.json
```

## Output

- `website/data.json` - All analytics data for the website
- `website/tarot_card.png` - Generated tarot card image

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | For embeddings and topic labeling |
| `GOOGLE_API_KEY` | Yes | For tarot card image generation |

You can also use `GEMINI_API_KEY` instead of `GOOGLE_API_KEY`.

## Viewing Results

After running the pipeline, view your dashboard:

```bash
cd website
python -m http.server 8000
```

Then open http://localhost:8000 in your browser.
