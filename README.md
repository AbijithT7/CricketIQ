# CricIQ: IPL Match Predictor

CricIQ is a full-stack machine learning application that predicts the outcome of IPL matches based on historical data, venue statistics, and team performance metrics. It provides real-time insights including win probabilities, expected first-innings scores, and key players to watch.

## 🚀 Features

- **Match Prediction**: Predicts win probability for any matchup using an XGBoost model.
- **Venue Insights**: Calculates expected first-innings scores based on historical venue averages.
- **Powerplay Estimates**: Provides projected powerplay scores.
- **Top Performers**: Identifies historically accurate top run-scorers and wicket-takers for specific matchups and venues.
- **Historical Alias Handling**: Correctly maps historical team names (e.g., Delhi Daredevils) to their modern counterparts (e.g., Delhi Capitals).

## 🛠️ Tech Stack

- **Frontend**: React (Vite), Tailwind CSS
- **Backend**: FastAPI (Python), Pandas, Scikit-learn, XGBoost
- **Data**: IPL JSON dataset processed into structured features
- **Machine Learning**: XGBoost Classifier

## 📋 Prerequisites

- Python 3.8+
- Node.js 18+
- npm or yarn

## 🔧 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/criciq.git
cd criciq
```

### 2. Backend Setup
```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the backend server
uvicorn main:app --reload
```
The API will be available at `http://127.0.0.1:8000`.

### 3. Frontend Setup
```bash
# Install npm dependencies
npm install

# Run the development server
npm run dev
```
The application will be available at `http://localhost:5173`.

## 📂 Project Structure

- `main.py`: FastAPI backend and API endpoints.
- `ml_match_features.csv`: Processed dataset used for feature lookups.
- `xgb_match_predictor.pkl`: Trained XGBoost model.
- `src/`: React frontend source code.
- `ipl_json/`: Raw match data (JSON format).
- `train_model.py`: Script to train and save the ML model.
- `extract_features_json.py`: Data processing script to generate features from JSON.

## 📈 API Endpoints

- `GET /api/features/{team1}/{team2}/{venue}`: Fetches historical features and enriched insights for a matchup.
- `POST /api/predict/match`: Takes match features and returns win probabilities.

## 📄 License

MIT License.
