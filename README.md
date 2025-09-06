# PDF Question Generator

A Streamlit web application that generates innovative questions from PDF documents using Google's Gemini AI.

## Features

- 📚 Upload PDF documents
- 🤖 AI-powered question generation using Google Gemini
- ⚙️ Customizable difficulty levels and question count
- 🌍 Multi-language support
- 💾 Download generated questions as text files

## How to Deploy to Streamlit Cloud

### Prerequisites
1. A Google Gemini API key (get it from [Google AI Studio](https://makersuite.google.com/app/apikey))
2. A GitHub account
3. A Streamlit Cloud account (free at [share.streamlit.io](https://share.streamlit.io))

### Step-by-Step Deployment

1. **Push code to GitHub:**
   - Create a new repository on GitHub
   - Push this code to your repository

2. **Deploy on Streamlit Cloud:**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Connect your GitHub repository
   - Set main file path to: `app.py`

3. **Configure Secrets:**
   - In your Streamlit Cloud app settings, go to "Secrets"
   - Add your Gemini API key:
   ```toml
   GEMINI_API_KEY = "your_api_key_here"
   ```

4. **Deploy:**
   - Click "Deploy" and wait for the app to build
   - Your app will be live at: `https://[your-app-name].streamlit.app`

## Local Development

To run locally:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Configuration

The app supports the following configurations:
- **Difficulty Level**: Easy, Medium, Hard, or Mixed
- **Number of Questions**: 5-50 questions
- **Language Instructions**: Customize how the AI handles language

## API Key Setup

Make sure to add your Gemini API key to Streamlit secrets:
1. Go to your app dashboard on Streamlit Cloud
2. Click on "Settings" → "Secrets"
3. Add: `GEMINI_API_KEY = "your_actual_api_key"`

## Security Note

Never commit your API key to version control. Always use Streamlit secrets or environment variables for sensitive information.
