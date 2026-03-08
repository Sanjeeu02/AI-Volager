# ✈️ AI Voyager - One-Click Deployment

This project is now configured for **Zero-Configuration Mobile Access**. You no longer need to worry about IP addresses or firewall settings failing again and again.

## 🚀 How to Run (Windows)
1. **Just Double-Click `START_VOYAGER.bat`**
2. The script will:
   - Detect your current computer's IP address (e.g. `10.35.69.252`).
   - Automatically update `index.html` with this IP.
   - Start the **AI Engine** (Streamlit) on port `8501`.
   - Start the **Landing Page** on port `8000`.
   - Open the local browser for you.

## 📱 How to Access on Mobile
Once the launcher says **"✨ AI VOYAGER IS NOW LIVE! ✨"**:
1. Check the **Mobile URL** printed in the terminal (usually something like `http://10.x.x.x:8000`).
2. Open that URL on your phone browser.
3. Tap **"Launch AI Voyager"** — it will connect every single time, even if your IP changed!

## 🔐 Security
Your `.env` and `chat_history.json` are strictly excluded from the GitHub repository via `.gitignore` to protect your API keys.

## 📁 Repository Structure
- **START_VOYAGER.bat**: Your primary one-click launcher.
- **index.html**: Mobile-optimized premium landing page.
- **index.css**: Modern glassmorphism design system.
- **helloworld/travel_agent**: The powerful core AI engine.

---
🚀 *Happy travels with Voyager AI!*
