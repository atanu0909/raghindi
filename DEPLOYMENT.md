# 🚀 Deployment Guide

## Deploy to Streamlit Community Cloud

### Step 1: Prepare Your Repository
✅ **Already Done!** Your code is now on GitHub at: `https://github.com/atanu0909/raghindi`

### Step 2: Get Google Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Copy the key (you'll need it for deployment)

### Step 3: Deploy on Streamlit Cloud
1. **Visit:** [https://share.streamlit.io/](https://share.streamlit.io/)
2. **Sign in** with your GitHub account
3. **Click "New app"**
4. **Select repository:** `atanu0909/raghindi`
5. **Main file path:** `app.py`
6. **Click "Advanced settings"**
7. **Add secrets:**
   ```
   GOOGLE_API_KEY = "your-actual-api-key-here"
   ```
8. **Click "Deploy"**

### Step 4: Access Your App
After deployment (usually 2-3 minutes), your app will be available at:
`https://your-app-name.streamlit.app`

## Alternative: Deploy to Other Platforms

### Heroku
1. Create `Procfile`:
   ```
   web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
   ```
2. Set environment variable: `GOOGLE_API_KEY`

### Railway
1. Connect GitHub repository
2. Set environment variable: `GOOGLE_API_KEY`
3. Railway auto-detects Streamlit apps

### Render
1. Connect GitHub repository  
2. Build command: `pip install -r requirements.txt`
3. Start command: `streamlit run app.py --server.port=$PORT --server.address=0.0.0.0`
4. Set environment variable: `GOOGLE_API_KEY`

## 🔒 Important Security Notes
- Never commit API keys to GitHub
- Always use environment variables or secrets management
- The `.streamlit/secrets.toml` file is for local development only
- Use Streamlit Cloud's secrets management for production

## 🎉 Your App Features
- ✅ PDF Question Generation with AI
- ✅ Interactive Exam System  
- ✅ AI-Powered Answer Evaluation
- ✅ Pattern-Based Question Formatting
- ✅ Professional PDF Downloads
- ✅ Multi-language Support
- ✅ Customizable Question Types

## 📞 Support
If you encounter any issues during deployment, check:
1. All dependencies are in `requirements.txt`
2. API key is correctly set in secrets
3. Repository is public or properly connected
4. Main file path is set to `app.py`
